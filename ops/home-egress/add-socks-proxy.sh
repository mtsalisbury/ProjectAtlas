#!/usr/bin/env bash
#
# Atlas — add a mesh-only SOCKS5 proxy to an EXISTING exit node (NY or
# Toronto today; London or any future one the same way)
# ================================================================
# Run this FROM YOUR MAC. It does not touch Headscale routes or ACLs at
# all — NY and Toronto are already registered, approved, and serving as
# exit nodes. All this adds is a small SOCKS5 proxy, bound only to the
# node's own tailscale0 interface, so the Mac's sing-box rule router has
# something to send "USA traffic" / "Canada traffic" through without
# fighting over Tailscale's one-exit-node-at-a-time limit.
#
# Nothing here is reachable from the public internet or even the rest of
# the mesh beyond whatever Headscale ACLs already allow — it's bound to
# the node's 100.64.x.x address only.
#
#   NODE_HOST=100.64.0.6 ./add-socks-proxy.sh        # Toronto, by mesh IP
#   NODE_HOST=192.241.147.167 ./add-socks-proxy.sh   # NY / atlas-mesh, by public IP
#
# Required env vars:
#   NODE_HOST   How to SSH into the node. Prefer its mesh IP (100.64.x.x) —
#               per STATUS.md, selecting an exit node over its PUBLIC IP
#               risks it locking its own SSH session out. This script
#               doesn't select an exit node, so the risk is much lower, but
#               the mesh address is still the safer habit.
#
# Optional env vars:
#   NODE_USER   SSH user (default root)
#   SOCKS_PORT  Port for the proxy (default 1080)

set -euo pipefail

: "${NODE_HOST:?Set NODE_HOST to the node mesh IP (preferred) or public IP}"
NODE_USER="${NODE_USER:-root}"
SOCKS_PORT="${SOCKS_PORT:-1080}"

NSSH="ssh -o ConnectTimeout=10 ${NODE_USER}@${NODE_HOST}"

say() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

say "Preflight"
$NSSH "echo ok" >/dev/null || die "Cannot reach $NODE_HOST over SSH."
echo "  reached $NODE_HOST"

say "Reading this node's mesh IP (proxy binds here, nowhere else)"
MESH_IP=$($NSSH "tailscale ip -4")
[[ -n "$MESH_IP" ]] || die "Could not read a mesh IP from this node — is tailscaled running?"
echo "  mesh IP: $MESH_IP"

say "Installing microsocks if needed"
$NSSH "
set -e
if command -v microsocks >/dev/null; then
  echo '  already installed'
else
  if apt-get install -y microsocks 2>/dev/null; then
    echo '  installed via apt'
  else
    echo '  not in apt — building from source'
    apt-get update -y
    apt-get install -y git build-essential
    rm -rf /tmp/microsocks-build
    git clone --depth 1 https://github.com/rofl0r/microsocks /tmp/microsocks-build
    make -C /tmp/microsocks-build
    install -m 0755 /tmp/microsocks-build/microsocks /usr/local/bin/microsocks
    rm -rf /tmp/microsocks-build
    echo '  built and installed'
  fi
fi
"

say "Installing systemd unit, bound to ${MESH_IP}:${SOCKS_PORT} only"
$NSSH "cat > /etc/systemd/system/atlas-mesh-socks.service <<UNIT
[Unit]
Description=Atlas mesh-only SOCKS5 proxy (used by the Mac rule router)
After=tailscaled.service
Requires=tailscaled.service

[Service]
ExecStart=\$(command -v microsocks) -i ${MESH_IP} -p ${SOCKS_PORT}
Restart=on-failure
RestartSec=5
User=nobody
Group=nogroup
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now atlas-mesh-socks.service
sleep 1
systemctl is-active --quiet atlas-mesh-socks.service"

if [[ $? -eq 0 ]]; then
  echo "  atlas-mesh-socks.service running"
else
  die "Service did not start — check 'ssh ${NODE_USER}@${NODE_HOST} systemctl status atlas-mesh-socks'."
fi

say "Done"
cat <<EOF

  SOCKS5 proxy live at ${MESH_IP}:${SOCKS_PORT}, mesh-only.

  Use this as the corresponding *_SOCKS value when running
  ops/home-egress/mac-client/generate-config.py — e.g. if this was
  Toronto, that's TORONTO_SOCKS=${MESH_IP}:${SOCKS_PORT}.

EOF
