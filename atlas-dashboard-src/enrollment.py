"""
Atlas — Device Enrollment
=========================

Closes the gap named in STATUS.md Part 3.8:

    "the backend can now correctly grant permission for a user to route through
     their matched exit node, but nothing yet tells their actual device to
     select and use that exit node."

This module is the tail that ties a client device to the mesh. It wraps the
Headscale CLI (via `docker exec headscale ...`, the same pattern already used
by headscale.py and presence_provision.py) and exposes three real capabilities:

  1. Pre-auth key issuance      -> desktop/laptop zero-touch enrollment
  2. Node-key registration      -> mobile enrollment (Tailscale iOS/Android)
  3. Exit-node assignment       -> tells the device *which* egress to present from

Design notes
------------
* No new dependencies. Same subprocess-to-docker pattern as the rest of the app.
* Every function raises RuntimeError with the raw stderr on failure, so the
  caller can surface a real message instead of a generic 500.
* Pre-auth keys are single-use and short-lived by default. A reusable key is a
  standing invitation to join someone's Presence; that should be a deliberate,
  explicit choice, never the default.
"""

import json
import re
import subprocess
from datetime import datetime, timezone

HEADSCALE_CONTAINER = "headscale"

# The coordination server a client must be pointed at. STATUS.md (Aug 4, H5 run)
# records a real failure caused by this: the stock Tailscale app defaults to
# Tailscale's own servers, not Headscale, which surfaced as an unrelated 401.
# Every enrollment instruction this module emits states it explicitly.
LOGIN_SERVER = "https://mesh.rpnwireless.com"

DEFAULT_KEY_EXPIRY = "1h"


def _headscale(args, timeout=15):
    """Run a headscale CLI command inside the container. Returns stdout."""
    cmd = ["docker", "exec", HEADSCALE_CONTAINER, "headscale"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            "headscale command failed ({}): {}".format(
                " ".join(args), result.stderr.strip() or result.stdout.strip()
            )
        )
    return result.stdout


def _headscale_json(args, timeout=15):
    raw = _headscale(args + ["--output", "json"], timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("headscale returned non-JSON output: " + raw[:300])


# ---------------------------------------------------------------------------
# User ID resolution
# ---------------------------------------------------------------------------
# Headscale 0.23+ (confirmed on v0.29.3) requires a NUMERIC user ID for the
# --user flag. Passing a username fails with:
#     invalid argument "presence-user-1" for "-u, --user" flag:
#     strconv.ParseUint: parsing "presence-user-1": invalid syntax
#
# The rest of Atlas identifies a Presence by name (`presence-user-N`), and
# `headscale users create <name>` still takes a name, so the mismatch is only on
# the flags. This resolves name -> id once and caches it.
#
# Older Headscale wanted the name here, so both are attempted: ID first, name as
# a fallback. That keeps this working if the server is ever rolled back.

_USER_ID_CACHE = {}


def resolve_user_id(username, refresh=False):
    """Map a Headscale username to its numeric ID."""
    username = str(username)
    if not refresh and username in _USER_ID_CACHE:
        return _USER_ID_CACHE[username]

    data = _headscale_json(["users", "list"])
    # Shape differs by version: a bare list, or {"users": [...]}.
    users = data.get("users", []) if isinstance(data, dict) else (data or [])

    for u in users:
        name = u.get("name") or u.get("username") or u.get("Name") or u.get("Username")
        if name == username:
            uid = u.get("id", u.get("ID"))
            if uid is None:
                break
            _USER_ID_CACHE[username] = str(uid)
            return str(uid)

    raise RuntimeError(
        "No Headscale user named '{}'. Known users: {}".format(
            username,
            ", ".join(str(u.get("name") or u.get("username")) for u in users) or "(none)",
        )
    )


def _headscale_for_user(username, build_args, timeout=15, as_json=False):
    """
    Run a headscale command whose --user flag needs an ID on this version and a
    name on older ones.

    build_args(user_ref) -> list of CLI args.

    Tries the numeric ID first. If that fails in a way that looks like the
    server wanted a name instead, retries with the name — so this survives a
    Headscale downgrade without a code change. A genuine error (user really
    doesn't exist, key already used) still surfaces, because the retry fails too
    and the original error is what gets raised.
    """
    runner = _headscale_json if as_json else _headscale

    try:
        uid = resolve_user_id(username)
    except RuntimeError:
        # Can't resolve — fall straight through to the name form.
        return runner(build_args(username), timeout=timeout)

    try:
        return runner(build_args(uid), timeout=timeout)
    except RuntimeError as id_error:
        try:
            return runner(build_args(username), timeout=timeout)
        except RuntimeError:
            # Report the ID-form failure: that's the supported path on current
            # Headscale, so it's the more useful error to see.
            raise id_error


# ---------------------------------------------------------------------------
# 1. Pre-auth keys — desktop / laptop enrollment
# ---------------------------------------------------------------------------

def create_preauth_key(headscale_username, expiration=DEFAULT_KEY_EXPIRY,
                       reusable=False, ephemeral=False):
    """
    Issue a pre-auth key for a Presence.

    reusable=False is deliberate. A single-use key enrolls exactly one device
    and then dies. That matches "this key is for the laptop in front of me,"
    not "anyone holding this string can join my Presence forever."
    """
    def build(user_ref):
        args = ["preauthkeys", "create", "--user", str(user_ref),
                "--expiration", expiration]
        if reusable:
            args.append("--reusable")
        if ephemeral:
            args.append("--ephemeral")
        return args

    data = _headscale_for_user(headscale_username, build, as_json=True)

    # Headscale versions differ: some return the key object, some a bare string.
    if isinstance(data, dict):
        key = data.get("key") or data.get("Key")
    else:
        key = str(data).strip()

    if not key:
        raise RuntimeError("headscale did not return a pre-auth key: " + str(data)[:300])

    return {
        "key": key,
        "login_server": LOGIN_SERVER,
        "expiration": expiration,
        "reusable": reusable,
        "ephemeral": ephemeral,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }


def list_preauth_keys(headscale_username):
    """All pre-auth keys for a Presence, so a person can see and revoke them."""
    data = _headscale_for_user(
        headscale_username,
        lambda ref: ["preauthkeys", "list", "--user", str(ref)],
        as_json=True,
    )
    keys = []
    for k in data or []:
        keys.append({
            "id": k.get("id"),
            # Never return the full key on a list view — only enough to identify it.
            "key_prefix": (k.get("key") or "")[:8],
            "reusable": k.get("reusable", False),
            "ephemeral": k.get("ephemeral", False),
            "used": k.get("used", False),
            "expiration": k.get("expiration"),
            "created_at": k.get("created_at"),
        })
    return keys


def expire_preauth_key(headscale_username, key):
    """Revoke an outstanding key before it is used."""
    _headscale_for_user(
        headscale_username,
        lambda ref: ["preauthkeys", "expire", "--user", str(ref), key],
    )
    return True


# ---------------------------------------------------------------------------
# 2. Node-key registration — mobile enrollment
# ---------------------------------------------------------------------------

# STATUS.md Part 2 records this as a confirmed limitation:
#   "Mobile can't be fully zero-touch with current tooling — Tailscale's mobile
#    apps have no way to accept a pre-auth key."
#
# That remains true and is not being re-litigated here. What this does is remove
# the *admin* from the loop, which was the actual bottleneck. Previously the
# person had to reach you so you could run `headscale nodes register` by hand.
# Now they paste the node key their own app already shows them, and the server
# registers it against their own Presence. Not zero-touch; one-paste, self-service.

NODEKEY_RE = re.compile(r"(?:nodekey:)?([0-9a-fA-F]{64})")


def normalize_node_key(raw):
    """
    Accept whatever the person actually has in their clipboard.

    The Tailscale app shows a full registration URL. People paste the URL, or
    the key, or the key with the `nodekey:` prefix, or with stray whitespace.
    All four should work — refusing to parse a URL is a self-inflicted support
    ticket.
    """
    if not raw:
        raise ValueError("No node key provided.")
    match = NODEKEY_RE.search(raw.strip())
    if not match:
        raise ValueError(
            "That doesn't look like a node key. Paste either the full "
            "registration link from your Tailscale app, or the key itself."
        )
    return "nodekey:" + match.group(1).lower()


def register_node(headscale_username, raw_node_key):
    """Register a waiting device against a Presence."""
    node_key = normalize_node_key(raw_node_key)
    output = _headscale_for_user(
        headscale_username,
        lambda ref: ["nodes", "register", "--user", str(ref), "--key", node_key],
    )
    return {
        "registered": True,
        "node_key": node_key[:16] + "...",
        "headscale_username": headscale_username,
        "detail": output.strip(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 3. Exit-node assignment — which egress this Presence presents from
# ---------------------------------------------------------------------------

def get_exit_node_info(exit_node_name):
    """
    Resolve a named exit node (EGR-Tor1 / EGR-Lon1) to its live mesh state.

    The client needs the mesh IP to actually select it, and needs to know
    whether it's online before telling someone to route through it.
    """
    import headscale  # local import: avoids a circular import at module load

    for node in headscale.get_nodes():
        if node.get("name") == exit_node_name:
            return {
                "name": node["name"],
                "online": node.get("online", False),
                "ip_addresses": node.get("ip_addresses", []),
                "routes": node.get("routes", []),
                # A node only functions as an exit node if the 0.0.0.0/0 and
                # ::/0 routes are actually approved. Reporting "assigned" when
                # the route was never approved would be a false green light.
                "exit_route_approved": any(
                    r in ("0.0.0.0/0", "::/0") for r in node.get("routes", [])
                ),
                # Approval and live service are different things — Headscale can
                # approve a route while the node's own tailscaled isn't currently
                # advertising it (found live on EGR-Tor1, Aug 5: approved but its
                # `subnet_routes` was empty, meaning nothing was actually being
                # served). Reporting "approved" alone as if it meant "working" is
                # the same false-green-light failure this field exists to avoid.
                "exit_route_serving": any(
                    r in ("0.0.0.0/0", "::/0") for r in node.get("serving_routes", [])
                ),
            }
    return None


def nodes_for_user(headscale_username):
    """Every device currently enrolled in this Presence."""
    import headscale

    return [n for n in headscale.get_nodes()
            if n.get("context") == headscale_username]


# ---------------------------------------------------------------------------
# 4. Human-facing enrollment instructions
# ---------------------------------------------------------------------------

def build_enrollment_instructions(preauth_key, exit_node_name=None,
                                  exit_node_selector=None):
    """
    Turn a key into something a person can actually act on, per platform.

    This is deliberately generated server-side rather than hardcoded in the
    frontend, so the login server and exit-node name can never drift out of
    sync with what the mesh actually has.

    exit_node_selector, when supplied, is what goes after `--exit-node=` — the
    node's mesh IP rather than its name. Tailscale accepts either, but the name
    only resolves if MagicDNS is on, and Headscale's is optional. Falls back to
    the name when no selector is available.
    """
    key = preauth_key["key"]
    up = "tailscale up --login-server={} --authkey={}".format(LOGIN_SERVER, key)
    selector = exit_node_selector or exit_node_name
    if selector:
        up += " --exit-node={}".format(selector)
        if exit_node_name:
            up += " --exit-node-allow-lan-access"

    return {
        "macos": {
            "label": "Mac",
            "zero_touch": True,
            "command": up,
            "note": ("Paste into Terminal. Requires the Tailscale CLI "
                     "(brew install tailscale, or the App Store app's CLI helper)."),
        },
        "linux": {
            "label": "Linux",
            "zero_touch": True,
            "command": "sudo " + up,
            "note": "Paste into a shell on the device you're enrolling.",
        },
        "windows": {
            "label": "Windows",
            "zero_touch": True,
            "command": up.replace("tailscale up", "tailscale.exe up"),
            "note": "Run in an Administrator Command Prompt.",
        },
        "mobile": {
            "label": "iPhone / iPad / Android",
            "zero_touch": False,
            "steps": [
                "Install the Tailscale app from the App Store or Play Store.",
                ("In the app, before signing in, open the overflow menu and choose "
                 "'Use custom coordination server'. Enter: " + LOGIN_SERVER),
                "Tap Sign in. The app will show a registration link.",
                "Copy that link and paste it into the box on this page.",
            ],
            "note": ("The mobile apps can't accept a pre-auth key — that's a "
                     "Tailscale limitation, not an Atlas one. Pasting the link "
                     "here does the same job without needing an administrator."),
        },
    }
