"""
Atlas — home-egress rule list storage.

The dashboard is the single source of truth for the personal multi-group
egress rules (MFA/USA/Canada domain lists) — every device sharing this
profile pulls from here rather than each keeping its own local copy that
quietly drifts. Admin-token gated by main.py's existing middleware, same
as every other /api/* route except /api/presence/*.

Stored in atlas.db (via db.py), not flat files on disk — a first attempt
used /opt/atlas-dashboard/home-egress-rules directly, which turned out to
be invisible inside the container: docker-compose.yml only bind-mounts
specific paths (logs/, mesh config/, and atlas.db as a single file), so
anything else written to that host path never reaches the running
container and wouldn't survive a rebuild either. atlas.db is already the
correctly-wired persistence mechanism this project uses for everything
else — reusing it here instead of adding a new volume mount to a
docker-compose.yml that headscale, caddy, and bank-demo also depend on.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import db

router = APIRouter(prefix="/api/home-egress", tags=["home-egress"])

RULE_KEYS = {"mfa-home", "usa-domains", "usa-apps", "canada-domains", "canada-apps"}

# Seed values — only ever applied the first time a key has never been set,
# so an admin edit is never silently overwritten by a redeploy. These are
# the actual contents validated live the night of Aug 5–6, not placeholders.
DEFAULTS = {
        "mfa-home": "# MFA / security-sensitive -> ALWAYS exit via home, regardless of what\n# group they'd otherwise fall into. This list takes priority over the\n# USA/Canada lists below it in generate-config.py \u2014 if a domain appears\n# here AND in usa-domains.txt, home wins.\n#\n# THIS LIST IS EMPTY ON PURPOSE. This is the one list I can't fill in for\n# you \u2014 it needs your actual bank(s), authenticator app(s), and anything\n# else that does push-based or step-up MFA. Add one domain per line, e.g.:\n#\n# yourbank.com\n# authy.com\n# okta.com\n#\n# Some MFA push notifications ride over Apple's own push infrastructure\n# (shared by every app, not just MFA ones) rather than the bank/app's own\n# domain \u2014 that traffic can't be isolated this way, only the app's direct\n# API/sync calls can. Worth testing each entry once added, rather than\n# assuming it's fully covered.\n\n# TD \u2014 both TD Bank (US) and TD Canada Trust. Both banks' online banking\n# now live under td.com (TD Canada Trust's old tdcanadatrust.com domain\n# consolidated here); tdbank.com is the separate US retail banking domain.\n# Not personally verified against a live login yet \u2014 confirm these are\n# actually what your browser shows in the address bar during a real\n# login, then remove this note.\ntd.com\ntdbank.com\n",
        "usa-domains": "# USA domains -> exit via NY\n# One domain per line. Matches this domain and all its subdomains.\n# Lines starting with # are ignored. Edit freely, no code changes needed \u2014\n# just regenerate config.json afterward (see ../README.md).\n\nwalmart.com\nhulu.com\nnytimes.com\n",
        "usa-apps": "# USA apps -> exit via NY\n# \"App\" rules are still matched by the domains that app's traffic talks to \u2014\n# there's no way to see which literal process opened a connection on macOS\n# without a much heavier kernel-level tool, so this list is really \"known\n# domains used by this app,\" same mechanism as usa-domains.txt, just kept\n# separate so it's easy to see what's an app vs. a plain website.\n#\n# TikTok, seeded from tonight's example. This list is not exhaustive \u2014\n# TikTok uses many CDN domains and some may be missing. Add more here as\n# you notice traffic that should have matched but didn't.\n\ntiktok.com\ntiktokv.com\ntiktokcdn.com\nttlivecdn.com\nmusical.ly\n",
        "canada-domains": "# Canada domains -> exit via Toronto\n# One domain per line. Matches this domain and all its subdomains.\n\nwalmart.ca\ncbc.ca\n",
        "canada-apps": "# Canada apps -> exit via Toronto\n# Same note as usa-apps.txt \u2014 matched by domain, not literal process.\n# Empty for now. Add domains for any Canadian banking/service apps here.\n"
    }


def _ensure_seeded():
    existing = db.get_home_egress_rules()
    for key, default in DEFAULTS.items():
        if key not in existing:
            db.set_home_egress_rule(key, default)


_ensure_seeded()


class RuleUpdate(BaseModel):
    content: str


@router.get("/rules")
def get_rules():
    """Every list at once — what the Mac client's sync script pulls."""
    rules = db.get_home_egress_rules()
    return {k: rules.get(k, "") for k in RULE_KEYS}


@router.get("/rules/{key}")
def get_rule(key: str):
    if key not in RULE_KEYS:
        raise HTTPException(status_code=404, detail=f"unknown rule list '{key}'")
    return {"key": key, "content": db.get_home_egress_rule(key) or ""}


@router.post("/rules/{key}")
def set_rule(key: str, req: RuleUpdate):
    if key not in RULE_KEYS:
        raise HTTPException(status_code=404, detail=f"unknown rule list '{key}'")
    db.set_home_egress_rule(key, req.content)
    return {"saved": key}
