#!/usr/bin/env python3
"""
Atlas — pull the shared home-egress rule lists down from the dashboard.

The dashboard (dashboard.rpnwireless.com) is the single source of truth
for these lists now — edit them there, from any device, and every device
sharing this profile picks up the same rules by running this before
generate-config.py. Local rules/*.txt become a synced mirror, not the
source of truth.

Usage:
    ATLAS_TOKEN=... python3 sync-rules.py
    python3 generate-config.py   # as before, now reading the synced files
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DASHBOARD = os.environ.get("ATLAS_DASHBOARD_URL", "https://dashboard.rpnwireless.com")
RULES_DIR = Path(__file__).parent / "rules"

RULE_FILES = {
    "mfa-home": "mfa-home.txt",
    "usa-domains": "usa-domains.txt",
    "usa-apps": "usa-apps.txt",
    "canada-domains": "canada-domains.txt",
    "canada-apps": "canada-apps.txt",
}


def main():
    token = os.environ.get("ATLAS_TOKEN")
    if not token:
        print("ERROR: set ATLAS_TOKEN to your admin token", file=sys.stderr)
        sys.exit(1)

    req = urllib.request.Request(
        f"{DASHBOARD}/api/home-egress/rules",
        headers={"X-Atlas-Token": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rules = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: {e.code} {e.reason} — check ATLAS_TOKEN is correct", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: could not reach {DASHBOARD}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    print(f"Synced from {DASHBOARD}:")
    for key, filename in RULE_FILES.items():
        content = rules.get(key, "")
        (RULES_DIR / filename).write_text(content)
        count = len([
            line for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ])
        print(f"  {filename}: {count} entr{'y' if count == 1 else 'ies'}")

    print("Run generate-config.py next to rebuild config.json from these.")


if __name__ == "__main__":
    main()
