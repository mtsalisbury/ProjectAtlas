import sqlite3
import hashlib
import secrets
import bcrypt
from pathlib import Path

DB_PATH = Path("/opt/atlas-dashboard/atlas.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            headscale_username TEXT,
            token TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            q1 TEXT, q2 TEXT, q3 TEXT, q4 TEXT, q5 TEXT,
            exit_node TEXT,
            built_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Route Path Selection: every change of declared origin is recorded.
    # A person changing where the internet sees them from is exactly the kind
    # of event that should be auditable by that person after the fact — and it
    # gives the research side a real dataset on how presentation actually gets
    # used, rather than assumptions about it.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS path_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            from_exit_node TEXT,
            to_exit_node TEXT,
            reason TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Home-egress rule lists (MFA/USA/Canada domains) — the shared profile
    # every device pulls from. Lives here, not flat files, since atlas.db is
    # the one path docker-compose.yml actually persists across rebuilds;
    # a first attempt using files under /opt/atlas-dashboard/home-egress-rules
    # discovered that path isn't bind-mounted at all and never reaches the
    # running container.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS home_egress_rules (
            key TEXT PRIMARY KEY,
            content TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """
    bcrypt, not the legacy sha256(salt + password) scheme this replaces.
    A single round of unsalted-construction SHA-256 is fast by design, which
    is exactly wrong for password storage — a commodity GPU tries billions of
    these per second. bcrypt's per-hash salt and deliberate slowness are the
    point. Flagged in STATUS.md since Aug 5; fixed here before any real
    person signs up.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _is_legacy_hash(password_hash: str) -> bool:
    # Legacy hashes are exactly 64 hex chars (a raw SHA-256 digest). Every
    # bcrypt hash starts with "$2" — the two formats can't collide.
    return len(password_hash) == 64 and not password_hash.startswith("$")

def _legacy_sha256(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()

def create_user(email: str, password: str):
    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise ValueError("Email already registered")
    password_hash = hash_password(password)
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO users (email, password_hash, salt, token) VALUES (?, ?, ?, ?)",
        (email, password_hash, "", token)
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(user)

def verify_login(email: str, password: str):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        conn.close()
        return None
    stored = user["password_hash"]
    if _is_legacy_hash(stored):
        if _legacy_sha256(password, user["salt"]) != stored:
            conn.close()
            return None
        # Correct password on an old-scheme account — upgrade it now, while
        # the plaintext is in hand. Lazy migration: every account still on
        # the weak scheme gets moved the next time its owner actually logs
        # in, with no forced reset and no downtime.
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = '' WHERE id = ?",
            (hash_password(password), user["id"])
        )
        conn.commit()
    else:
        if not bcrypt.checkpw(password.encode(), stored.encode()):
            conn.close()
            return None
    conn.close()
    return dict(user)

def get_user_by_token(token: str):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    conn.close()
    return dict(user) if user else None

def set_headscale_username(user_id: int, headscale_username: str):
    conn = get_conn()
    conn.execute("UPDATE users SET headscale_username = ? WHERE id = ?", (headscale_username, user_id))
    conn.commit()
    conn.close()

def save_persona(user_id: int, q1, q2, q3, q4, q5, exit_node):
    conn = get_conn()
    conn.execute(
        "INSERT INTO personas (user_id, q1, q2, q3, q4, q5, exit_node) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, q1, q2, q3, q4, q5, exit_node)
    )
    conn.commit()
    conn.close()

def get_latest_persona(user_id: int):
    conn = get_conn()
    # Ordered by id, not built_at: two rows written in the same second are
    # otherwise ambiguous, and "latest" has to be exact.
    persona = conn.execute(
        "SELECT * FROM personas WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(persona) if persona else None


# --- Route Path Selection ---------------------------------------------------

def set_persona_exit_node(user_id: int, exit_node: str):
    """
    Change the declared origin on this Presence's current persona.

    Updates in place rather than inserting a new persona row: the questionnaire
    answers haven't changed, only the presentation. The audit trail lives in
    path_history, which is the right place for it.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM personas WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return False
    conn.execute("UPDATE personas SET exit_node = ? WHERE id = ?", (exit_node, row["id"]))
    conn.commit()
    conn.close()
    return True


def record_path_change(user_id: int, from_exit_node, to_exit_node, reason: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO path_history (user_id, from_exit_node, to_exit_node, reason) "
        "VALUES (?, ?, ?, ?)",
        (user_id, from_exit_node, to_exit_node, reason)
    )
    conn.commit()
    conn.close()


def get_path_history(user_id: int, limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT from_exit_node, to_exit_node, reason, changed_at FROM path_history "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Home-egress rule lists --------------------------------------------------

def get_home_egress_rules():
    conn = get_conn()
    rows = conn.execute("SELECT key, content FROM home_egress_rules").fetchall()
    conn.close()
    return {r["key"]: r["content"] for r in rows}


def get_home_egress_rule(key: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT content FROM home_egress_rules WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row["content"] if row else None


def set_home_egress_rule(key: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO home_egress_rules (key, content) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET content = excluded.content",
        (key, content)
    )
    conn.commit()
    conn.close()
