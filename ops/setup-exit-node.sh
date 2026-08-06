#!/usr/bin/env bash
#
# Atlas — turn a fresh droplet into a working exit-node provider
# ================================================================
# Run this FROM YOUR MAC, after rebuilding/creating a droplet from a clean
# Ubuntu base image. Automates everything done by hand for the Toronto
# rebuild on Aug 5: install Tailscale, register, advertise as an exit node,
# persist IP forwarding, approve the routes, rename to the mesh's naming
# convention, and verify.
#
#   DROPLET_IP=1.2.3.4 NODE_NAME=EGR-XYZ1 ./setup-exit-node.sh
#
# Required env vars:
#   DROPLET_IP   Public IP of the freshly built droplet
#   NODE_NAME    Friendly exit-node name to end up with, e.g. EGR-Tor1
#
# Optional env vars (defaults match the current mesh):
#   CONTROL_HOST  Control-plane server running Headscale (default 192.241.147.167)
#   LOGIN_SERVER  Coordination server URL (default https://mesh.rpnwireless.com)
#   HS_USER       Numeric Headscale user ID to register under (default 1 = personal)
#                 Headscale v0.29.3+ requires the numeric ID, not the name —
#                 see STATUS.md Part 0.2 for why.
#
# What this does NOT do:
#   - Prove live third-party traffic actually flows. That needs a live peer to
#     temporarily un-advertise itself and consume this node as a test client —
#     see STATUS.md Part 0.3 for why that can't be automated safely (it risks
#     self-locking whichever peer is used to test).
#   - Touch UFW. If UFW is active on the fresh image, this script reports it
#     and stops rather than guessing what rules you want.

set -euo pipefail

: "${DROPLET_IP:?Set DROPLET_IP to the fresh droplet public IP}"
: "${NODE_NAME:?Set NODE_NAME to the exit-node name this box should end up with, e.g. EGR-Tor1}"

CONTROL_HOST="${CONTROL_HOST:-192.241.147.167}"
LOGIN_SERVER="${LOGIN_SERVER:-https://mesh.rpnwireless.com}"
HS_USER="${HS_USER:-1}"
DROPLET_USER="${DROPLET_USER:-root}"
CONTROL_USER="${CONTROL_USER:-root}"

DSSH="ssh -o ConnectTimeout=10 ${DROPLET_USER}@${DROPLET_IP}"
CSSH="ssh -o ConnectTimeout=10 ${CONTROL_USER}@${CONTROL_HOST}"

say() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

# --- preflight ---------------------------------------------------------------
say "Preflight"
$DSSH "echo ok" >/dev/null || die "Cannot reach $DROPLET_IP over SSH. Is it rebuilt and booted?"
echo "  reached droplet at $DROPLET_IP"
$CSSH "echo ok" >/dev/null || die "Cannot reach control host $CONTROL_HOST over SSH."
echo "  reached control host at $CONTROL_HOST"

# --- clean up any stale node with this name -----------------------------------
say "Checking for an existing node named $NODE_NAME"
EXISTING_JSON=$($CSSH "docker exec headscale headscale nodes list --output json")
EXISTING=$(python3 -c "
import json, sys
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

# --- install tailscale ---------------------------------------------------------
say "Installing Tailscale on $DROPLET_IP"
$DSSH "curl -fsSL https://tailscale.com/install.sh | sh" >/dev/null
echo "  installed"

# --- generate a fresh preauth key and register ---------------------------------
say "Registering with the mesh as an exit-node provider"
KEY=$($CSSH "docker exec headscale headscale preauthkeys create --user $HS_USER --reusable=false --expiration 1h")
[[ -n "$KEY" ]] || die "Failed to generate a preauth key from $CONTROL_HOST."
$DSSH "tailscale up --login-server=${LOGIN_SERVER} --authkey=${KEY} --advertise-exit-node --advertise-routes=0.0.0.0/0,::/0 --accept-dns=false"
echo "  registered"

# --- persist IP forwarding -----------------------------------------------------
say "Persisting IP forwarding (this was almost certainly the real Toronto bug — set for the boot, not saved across one)"
$DSSH "
echo 'net.ipv4.ip_forward=1' | tee /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding=1' | tee -a /etc/sysctl.d/99-tailscale.conf
sysctl -p /etc/sysctl.d/99-tailscale.conf
systemctl restart tailscaled
sleep 3
"
echo "  ip_forward persisted, tailscaled restarted to clear any stale health warning"

# --- check UFW, don't touch it -------------------------------------------------
say "Checking UFW (not modifying it)"
UFW_STATUS=$($DSSH "ufw status" 2>&1 || echo "not installed")
echo "  $UFW_STATUS"
if grep -qi "^Status: active" <<<"$UFW_STATUS"; then
  die "UFW is active on this box. London/Toronto both run with UFW inactive — decide the right rules for this one manually before continuing, then re-run with UFW already configured."
fi

# --- approve routes and rename --------------------------------------------------
say "Approving routes and renaming to $NODE_NAME"
sleep 2
NEW_ID=$(python3 -c "
import json, subprocess
out = subprocess.run(['ssh', '${CONTROL_USER}@${CONTROL_HOST}', 'docker exec headscale headscale nodes list --output json'], capture_output=True, text=True).stdout
nodes = json.loads(out)
candidates = [n for n in nodes if n.get('ip_addresses') and n.get('online')]
# The just-registered node is whichever online node does NOT already have a
# given_name matching an existing exit-node convention — pick the most
# recently created one to be safe.
candidates.sort(key=lambda n: n.get('created_at', {}).get('seconds', 0), reverse=True)
print(candidates[0]['id'] if candidates else '')
")
[[ -n "$NEW_ID" ]] || die "Could not find the newly registered node's ID. Check manually with: headscale nodes list"
echo "  new node ID: $NEW_ID"

$CSSH "docker exec headscale headscale nodes approve-routes -i $NEW_ID --routes 0.0.0.0/0,::/0"
$CSSH "docker exec headscale headscale nodes rename -i $NEW_ID $NODE_NAME"
echo "  approved and renamed"

# --- verify ----------------------------------------------------------------
say "Verifying"
ROUTES=$($CSSH "docker exec headscale headscale nodes list-routes")
echo "$ROUTES"
if ! grep -A2 "^$NEW_ID " <<<"$ROUTES" | grep -q "0.0.0.0/0.*0.0.0.0/0.*0.0.0.0/0"; then
  echo "  WARNING: could not confirm Approved+Available+Serving all populated for ID $NEW_ID — check the table above by eye."
else
  echo "  Approved + Available + Serving all confirmed for $NODE_NAME (ID $NEW_ID)"
fi

LEFTOVER=$($DSSH "ps aux | grep -E 'tcpdump|ping ' | grep -v grep" || true)
if [[ -n "$LEFTOVER" ]]; then
  echo "  WARNING: leftover process found on the fresh box — this is what likely wedged the old Toronto:"
  echo "$LEFTOVER"
fi

say "Done"
cat <<EOF

  $NODE_NAME is registered, forwarding, and its routes are approved.

  This proves CONFIGURATION, not live traffic. To actually prove traffic
  flows (as done for Toronto on Aug 5), a live peer needs to temporarily
  give up its own exit-node-provider role and consume this one instead —
  that step is NOT automated here because it risks self-locking whichever
  peer is used to test, and recovering from that needs a human at the
  DigitalOcean console. See STATUS.md Part 0.3 for the exact procedure.

EOF
