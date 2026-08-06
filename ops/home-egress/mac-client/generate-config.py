#!/usr/bin/env python3
"""
Atlas — generate the Mac's sing-box config from the plain-text rule files.

The rule files (rules/*.txt) are the source of truth, meant to be hand-edited
directly — one domain per line, no code changes needed. This script just
turns them into the JSON sing-box actually wants, plus wires up the three
mesh SOCKS5 backends (NY, Toronto, home) as outbounds.

Usage:
    NY_SOCKS=100.64.0.X:1080 \\
    TORONTO_SOCKS=100.64.0.6:1080 \\
    HOME_SOCKS=100.64.0.Y:1080 \\
    python3 generate-config.py

Each *_SOCKS value is the mesh IP:port printed at the end of
add-socks-proxy.sh (for NY/Toronto) or setup-home-node.sh (for home).

Priority, if a domain appears in more than one list: mfa-home.txt wins over
everything else, then usa-*, then canada-*. Anything matching nothing falls
through to DIRECT — untouched, out whatever network the Mac is actually on.
"""

import json
import os
import sys
from pathlib import Path

RULES_DIR = Path(__file__).parent / "rules"
OUT_PATH = Path(__file__).parent / "config.json"


def load_domains(filename: str) -> list[str]:
    path = RULES_DIR / filename
    if not path.exists():
        return []
    domains = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domains.append(line)
    return domains


def require_env(name: str) -> tuple[str, str]:
    val = os.environ.get(name)
    if not val or ":" not in val:
        print(f"ERROR: set {name}=<mesh-ip>:<port>, e.g. {name}=100.64.0.6:1080", file=sys.stderr)
        sys.exit(1)
    host, port = val.rsplit(":", 1)
    return host, port


def socks_outbound(tag: str, host: str, port: str) -> dict:
    return {
        "type": "socks",
        "tag": tag,
        "server": host,
        "server_port": int(port),
        "version": "5",
    }


def main():
    ny_host, ny_port = require_env("NY_SOCKS")
    tor_host, tor_port = require_env("TORONTO_SOCKS")
    home_host, home_port = require_env("HOME_SOCKS")

    mfa_domains = load_domains("mfa-home.txt")
    usa_domains = load_domains("usa-domains.txt") + load_domains("usa-apps.txt")
    canada_domains = load_domains("canada-domains.txt") + load_domains("canada-apps.txt")

    if not mfa_domains:
        print(
            "WARNING: rules/mfa-home.txt is empty — nothing will be forced "
            "through home yet except whatever the phone does at the OS level. "
            "Add your bank/authenticator domains there, then regenerate.",
            file=sys.stderr,
        )

    # Sniffing moved from an inbound-level field to an explicit route rule in
    # sing-box 1.11+ ("Migrate legacy inbound fields to rule actions"). It has
    # to run before the domain_suffix rules below, since those depend on the
    # sniffed SNI/HTTP host to know each connection's domain at all.
    rules = [{"action": "sniff"}]
    if mfa_domains:
        rules.append({"domain_suffix": mfa_domains, "outbound": "home"})
    if usa_domains:
        rules.append({"domain_suffix": usa_domains, "outbound": "ny"})
    if canada_domains:
        rules.append({"domain_suffix": canada_domains, "outbound": "toronto"})

    config = {
        "log": {"level": "info", "timestamp": True},
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "utun-atlas",
                "address": ["172.19.0.1/30"],
                "mtu": 1500,
                "auto_route": True,
                "strict_route": True,
                "stack": "system",
            }
        ],
        "outbounds": [
            socks_outbound("ny", ny_host, ny_port),
            socks_outbound("toronto", tor_host, tor_port),
            socks_outbound("home", home_host, home_port),
            {"type": "direct", "tag": "direct"},
        ],
        "route": {
            "rules": rules,
            "final": "direct",
            "auto_detect_interface": True,
        },
    }

    OUT_PATH.write_text(json.dumps(config, indent=2))
    print(f"Wrote {OUT_PATH}")
    print(f"  MFA-home domains:   {len(mfa_domains)}")
    print(f"  USA (-> NY):        {len(usa_domains)}")
    print(f"  Canada (-> Toronto):{len(canada_domains)}")
    print("  Everything else:    DIRECT (local, untouched)")


if __name__ == "__main__":
    main()
