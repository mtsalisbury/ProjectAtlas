# Mac Rule Router — Setup

Routes your Mac's traffic through four possible exits, decided per-destination,
all at once — not one exit node for the whole device like stock Tailscale.

| Group | Source file | Exits via |
|---|---|---|
| MFA / security-sensitive | `rules/mfa-home.txt` | Home (always, takes priority over everything else) |
| USA domains + apps | `rules/usa-domains.txt`, `rules/usa-apps.txt` | NY |
| Canada domains + apps | `rules/canada-domains.txt`, `rules/canada-apps.txt` | Toronto |
| Everything else (MISC) | *(no file — the default)* | Direct — whatever network you're actually on |

Uses [sing-box](https://github.com/SagerNet/sing-box) in TUN mode to see all
Mac traffic, plus a mesh-only SOCKS5 proxy running on each exit node (NY,
Toronto, home) as the actual backend each group dials out through.

## Prerequisites

- NY and Toronto each have `atlas-mesh-socks.service` running
  (`../add-socks-proxy.sh`).
- The home Pi is registered and has `atlas-home-socks.service` running
  (`../setup-home-node.sh`) — **this step happens once you're at the house,
  can't run remotely.**
- Your Mac can already reach the mesh (it's been enrolled since Part 0.1).

## Install

```bash
brew install sing-box
```

## Edit the rule lists

**The dashboard (`dashboard.rpnwireless.com`, admin panel) is the source of
truth for the rule lists now, not the local `.txt` files directly.** Every
device sharing this profile edits the same lists there — the "HOME EGRESS
RULES" panel — so nothing drifts between devices. Pull the current lists
down before generating config:

```bash
cd ops/home-egress/mac-client
ATLAS_TOKEN=<your admin token> python3 sync-rules.py
```

This overwrites the local `rules/*.txt` files with whatever's on the
dashboard. Editing the local files directly still works for a quick local
test, but anything you type there is overwritten on the next sync — treat
the dashboard as the real copy.

## Generate the config

Get each node's mesh IP:port from the output of `add-socks-proxy.sh` /
`setup-home-node.sh` (or `ssh <node> tailscale ip -4` plus whatever
`SOCKS_PORT` you used, default 1080), then:

```bash
NY_SOCKS=100.64.0.X:1080 \
TORONTO_SOCKS=100.64.0.6:1080 \
HOME_SOCKS=100.64.0.Y:1080 \
python3 generate-config.py
```

This writes `config.json` from whatever's currently in `rules/*.txt` —
run `sync-rules.py` first if you want the latest from the dashboard.

## Run

TUN mode needs root (it's creating a virtual network interface):

```bash
sudo sing-box run -c config.json
```

Leave this running in a terminal (or set it up as a LaunchDaemon once you've
confirmed it works — not done yet, deliberately, until this has been proven
on real traffic first).

## Verify

While it's running, in another terminal:

```bash
# Should show NY's IP
curl -4 https://icanhazip.com --resolve walmart.com:443:1.1.1.1 2>/dev/null || true
# Simplest real check: open walmart.com and hulu.com in a browser, confirm
# egress via a "what's my IP" style check on each; then walmart.ca; then
# something unmatched (should show your real, local IP).
```

Simplest honest test: visit an IP-echo site through each app/domain path by
hand and confirm the IP shown matches the exit you expect. Nothing here has
been run against live traffic yet — this is the same "configured, not yet
proven" state every other piece of Atlas started in.

## Editing rules later

Just edit the `.txt` files in `rules/` — one domain per line, `#` for
comments — then re-run `generate-config.py` with the same env vars and
restart `sing-box`. No code changes, ever, for adding/removing a domain.

## Known limits, stated plainly

- **Matches by domain, not literal process.** Two different apps talking to
  the same domain can't be split — this is the tradeoff we chose over
  needing OS-level per-app entitlements, see the chat that scoped this.
- **Not yet tested against live traffic.** Configured only.
- **DNS-over-HTTPS in some apps/browsers can bypass sniffing** if the app
  resolves names through an encrypted resolver sing-box can't see into.
  Chrome/Firefox with DoH enabled are the most likely to do this — worth
  testing specifically once this is running.
- **MFA push notifications routed through Apple's own push
  infrastructure** (shared by every app) aren't isolable this way — only
  each app's own direct traffic is. Noted in `rules/mfa-home.txt` too.
