#!/usr/bin/env bash
#
# Atlas — turn the home Pi into a real exit-node provider, plus a mesh-only
# SOCKS5 proxy for the Mac's rule router
# ================================================================
# Same pattern as ops/setup-exit-node.sh (used for the Toronto rebuild,
# Aug 5), adapted for a box that lives on your home network instead of a
# public droplet:
#
#   - No public IP is needed. Tailscale/Headscale NAT-traverses fine — this
#     node just needs ordinary outbound internet, the same as any phone.
#   - First run has to happen over your LAN (wired connection, or whatever
#     you already use to reach your home network) because the Pi has no
#     Tailscale identity yet to reach it any other way. That's the "has to
#     happen tomorrow" step — nothing here can run from the Cowork sandbox,
#     which has no path into your home network at all.
#   - Registers as a FULL exit-node provider (--advertise-exit-node
#     --advertise-routes=0.0.0.0/0,::/0), same as NY/Toronto/London, so your
#     phone's stock Tailscale app can select "home" directly as its exit
#     node — this is what makes the MFA-always-comes-from-home rule work on
#     iOS without needing a custom app.
#   - ALSO installs microsocks bound only to the Tailscale interface, so the
#     Mac's sing-box rule-router has a mesh-only SOCKS5 backend to send its
#     "home" traffic group through. Nothing here is exposed to your home
#     LAN or the public internet — only reachable over the mesh.
#
# Usage, run from the Pi itself (simplest for a first-time box with no
# Tailscale identity yet), or via SSH from your Mac if the Pi already has
# SSH enabled and you're on the same LAN or plugged in directly:
#
#   sudo NODE_NAME=EGR-Home1 ./setup-home-node.sh
#
# Required env vars:
#   (none — NODE_NAME defaults to EGR-Home1)
#
# Optional env vars (defaults match the current mesh):
#   NODE_NAME       Friendly exit-node name (default EGR-Home1)
#   CONTROL_HOST    Headscale control-plane public IP (default 192.241.147.167)
#   LOGIN_SERVER    Coordination server URL (default https://mesh.rpnwireless.com)
#   HS_USER         Numeric Headscale user ID to register under (default 1 = personal)
#   SOCKS_PORT      Port for the mesh-only SOCKS5 proxy (default 1080)
#   CONTROL_USER    SSH user for the control host (default root)
#
# This script is meant to run locally ON the Pi (as root/sudo), not remotely
# from your Mac like setup-exit-node.sh does for droplets — it still needs
# to SSH OUT to the control host to approve routes and rename the node,
# which means the Pi itself needs SSH access configured to reach
# CONTROL_HOST. If that's not set up yet, run the Headscale-side commands
# (approve-routes / rename, printed at the end) by hand from your Mac
# instead.
#
# What this does NOT do:
#   - Prove live third-party traffic actually flows. Same caveat as
#     setup-exit-node.sh — a live peer test risks self-locking whichever
#     peer is used, see STATUS.md Part 0.3.
#   - Configure port forwarding or dynamic DNS. Not needed — Tailscale's
#     NAT traversal handles a home connection with a normal consumer
#     router/ISP fine, the same way your phone already works on the mesh.

set -euo pipefail

NODE_NAME="${NODE_NAME:-EGR-Home1}"
CONTROL_HOST="${CONTROL_HOST:-192.241.147.167}"
LOGIN_SERVER="${LOGIN_SERVER:-https://mesh.rpnwireless.com}"
HS_USER="${HS_USER:-1}"
SOCKS_PORT="${SOCKS_PORT:-1080}"
CONTROL_USER="${CONTROL_USER:-root}"

CSSH="ssh -o ConnectTimeout=10 ${CONTROL_USER}@${CONTROL_HOST}"

say() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

[[ "$EUID" -eq 0 ]] || die "Run this with sudo — it edits sysctl and installs a systemd unit."

# --- preflight -----------------------------------------------------------
say "Preflight"
command -v curl >/dev/null || die "curl not found — install it first (apt-get install -y curl)."
$CSSH "echo ok" >/dev/null || die "Cannot reach control host $CONTROL_HOST over SSH from this Pi. Either set up SSH access from the Pi to the control host, or run the approve-routes/rename steps by hand from your Mac using the node ID this script prints."
echo "  reached control host at $CONTROL_HOST"

# --- clean up any stale node with this name -------------------------------
say "Checking for an existing node named $NODE_NAME"
EXISTING_JSON=$($CSSH "docker exec headscale headscale nodes list --output json")
EXISTING=$(python3 -c "
import json
nodes = json.loads('''$EXISTING_JSON''')
for n in nodes:
    if n.get('given_name') == '$NODE_NAME':
        print(n['id'], n.get('online', False))
        break
")
if [[ -n "$EXISTING" ]]; then
  EID=$(awk '{print $1}' <<<"$EXISTING")
  EONLINE=$(awk '{print $2}' <<<"$EXISTING")
  if [[ "$EONLINE" == "True" ]]; then
    die "A node named $NODE_NAME (ID $EID) is already registered AND ONLINE. Refusing to delete a live node — investigate manually before re-running."
  fi
  echo "  found a dead entry for $NODE_NAME (ID $EID) — deleting before re-registering"
  $CSSH "docker exec headscale headscale nodes delete -i $EID --force"
else
  echo "  no existing node named $NODE_NAME — clean"
fi

# --- install tailscale -----------------------------------------------------
say "Installing Tailscale on this Pi"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
  echo "  installed"
else
  echo "  already installed"
fi

# --- generate a fresh preauth key and register ------------------------------
say "Registering with the mesh as an exit-node provider"
KEY=$($CSSH "docker exec headscale headscale preauthkeys create --user $HS_USER --reusable=false --expiration 1h")
[[ -n "$KEY" ]] || die "Failed to generate a preauth key from $CONTROL_HOST."
tailscale up --login-server="${LOGIN_SERVER}" --authkey="${KEY}" --advertise-exit-node --advertise-routes=0.0.0.0/0,::/0 --accept-dns=false
echo "  registered"

# --- persist IP forwarding ---------------------------------------------------
say "Persisting IP forwarding (the same setting that wedged Toronto until it was made persistent, Aug 5)"
echo 'net.ipv4.ip_forward=1' | tee /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding=1' | tee -a /etc/sysctl.d/99-tailscale.conf
sysctl -p /etc/sysctl.d/99-tailscale.conf
systemctl restart tailscaled
sleep 3
echo "  ip_forward persisted, tailscaled restarted"

# --- check for a firewall, don't touch it ------------------------------------
say "Checking for an active firewall (not modifying it)"
if command -v ufw >/dev/null; then
  UFW_STATUS=$(ufw status 2>&1 || echo "not installed")
  echo "  $UFW_STATUS"
  if grep -qi "^Status: active" <<<"$UFW_STATUS"; then
    die "UFW is active on this Pi. Decide the right rules manually (at minimum allow the SOCKS_PORT and Tailscale's own ports from the tailscale0 interface) before continuing."
  fi
else
  echo "  ufw not installed — nothing to check"
fi

# --- get this node's mesh IP -------------------------------------------------
say "Reading this node's mesh IP"
sleep 2
MESH_IP=$(tailscale ip -4)
[[ -n "$MESH_IP" ]] || die "Could not read a mesh IP from 'tailscale ip -4'."
echo "  mesh IP: $MESH_IP"

# --- install microsocks, bound only to the mesh interface --------------------
say "Installing a mesh-only SOCKS5 proxy (microsocks) on port $SOCKS_PORT"
if ! command -v microsocks >/dev/null; then
  if apt-get install -y microsocks 2>/dev/null; then
    echo "  installed via apt"
  else
    echo "  not in apt — building from source"
    apt-get update -y
    apt-get install -y git build-essential
    TMPDIR=$(mktemp -d)
    git clone --depth 1 https://github.com/rofl0r/microsocks "$TMPDIR/microsocks"
    make -C "$TMPDIR/microsocks"
    install -m 0755 "$TMPDIR/microsocks/microsocks" /usr/local/bin/microsocks
    rm -rf "$TMPDIR"
    echo "  built and installed to /usr/local/bin/microsocks"
  fi
else
  echo "  already installed"
fi

cat > /etc/systemd/system/atlas-home-socks.service <<UNIT
[Unit]
Description=Atlas mesh-only SOCKS5 proxy (home egress for the Mac rule router)
After=tailscaled.service
Requires=tailscaled.service

[Service]
ExecStart=$(command -v microsocks) -i ${MESH_IP} -p ${SOCKS_PORT}
Restart=on-failure
RestartSec=5
User=nobody
Group=nogroup
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now atlas-home-socks.service
sleep 1
systemctl is-active --quiet atlas-home-socks.service || die "atlas-home-socks.service did not start — check 'systemctl status atlas-home-socks'."
echo "  microsocks bound to ${MESH_IP}:${SOCKS_PORT}, started, enabled on boot"

# --- approve routes and rename -----------------------------------------------
say "Approving routes and renaming to $NODE_NAME"
NEW_ID=$(python3 -c "
import json, subprocess
out = subprocess.run(['ssh', '${CONTROL_USER}@${CONTROL_HOST}', 'docker exec headscale headscale nodes list --output json'], capture_output=True, text=True).stdout
nodes = json.loads(out)
candidates = [n for n in nodes if n.get('ip_addresses') and n.get('online')]
candidates.sort(key=lambda n: n.get('created_at', {}).get('seconds', 0), reverse=True)
print(candidates[0]['id'] if candidates else '')
")
[[ -n "$NEW_ID" ]] || die "Could not find the newly registered node's ID. Check manually with: headscale nodes list"
echo "  new node ID: $NEW_ID"

$CSSH "docker exec headscale headscale nodes approve-routes -i $NEW_ID --routes 0.0.0.0/0,::/0"
$CSSH "docker exec headscale headscale nodes rename -i $NEW_ID $NODE_NAME"
echo "  approved and renamed"

# --- verify --------------------------------------------------------------
say "Verifying"
ROUTES=$($CSSH "docker exec headscale headscale nodes list-routes")
echo "$ROUTES"
if ! grep -A2 "^$NEW_ID " <<<"$ROUTES" | grep -q "0.0.0.0/0.*0.0.0.0/0.*0.0.0.0/0"; then
  echo "  WARNING: could not confirm Approved+Available+Serving all populated for ID $NEW_ID — check the table above by eye."
else
  echo "  Approved + Available + Serving all confirmed for $NODE_NAME (ID $NEW_ID)"
fi

say "Done"
cat <<EOF

  $NODE_NAME is registered, forwarding, and its routes are approved.
  Mesh-only SOCKS5 proxy is live at ${MESH_IP}:${SOCKS_PORT}.

  Two things to do next:
    1. On your phone: stock Tailscale app -> select $NODE_NAME as the exit
       node. That's the whole MFA-from-home rule on iOS for now — every
       app's traffic goes through home until a real per-app iOS client
       exists.
    2. On your Mac: use ${MESH_IP}:${SOCKS_PORT} as the HOME_SOCKS value
       when running generate-config.py (see ops/home-egress/mac-client/).

  This proves CONFIGURATION, not live traffic. As with every other exit
  node in this project, the actual traffic-flows proof needs a live peer
  test — see STATUS.md Part 0.3 for the exact (manual, not automated)
  procedure and why it isn't automated.

EOF
