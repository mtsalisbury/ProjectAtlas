#!/usr/bin/env bash
#
# Atlas — deploy the client enrollment + Lens layer to atlas-mesh
# ===============================================================
# Run this FROM YOUR MAC, from inside the atlas-dashboard-src directory.
#
#   chmod +x deploy-enrollment.sh
#   ./deploy-enrollment.sh
#
# What it does:
#   1. Backs up the current /opt/atlas-dashboard on the droplet (timestamped)
#   2. Copies the four changed/new files
#   3. Rebuilds and restarts the container
#   4. Health-checks; rolls back automatically if the app doesn't come up
#
# STATUS.md (Aug 4) records the rule: prefer mesh addresses over public ones for
# admin work. Defaulting to the public IP here anyway, because the Mac's
# Tailscale was stopped as of Aug 5 — a mesh address you can't reach is worse
# than a public one you can. Switch back once the Mac is re-enrolled:
#   ATLAS_HOST=100.64.0.8 ./deploy-enrollment.sh

set -euo pipefail

ATLAS_HOST="${ATLAS_HOST:-192.241.147.167}"
ATLAS_USER="${ATLAS_USER:-root}"
APP_DIR="/opt/atlas-dashboard"

# The application code lives in /opt/atlas-dashboard, but the compose file that
# builds it lives with the rest of the stack (headscale, caddy, bank-demo) in
# /root/atlas-mesh. Confirmed Aug 5 from the running image name,
# `atlas-mesh-atlas-dashboard`: compose project `atlas-mesh`, service
# `atlas-dashboard`. Running `docker compose` from APP_DIR fails with
# "no configuration file provided: not found".
COMPOSE_DIR="${COMPOSE_DIR:-/root/atlas-mesh}"
SERVICE="${SERVICE:-atlas-dashboard}"
PUBLIC_URL="${PUBLIC_URL:-https://dashboard.rpnwireless.com}"

SSH="ssh ${ATLAS_USER}@${ATLAS_HOST}"
STAMP="$(date +%Y%m%d-%H%M%S)"

# Compose v2 is the default; fall back to v1 automatically.
COMPOSE="docker compose"

# PY_FILES: Python source, syntax-checked before anything is copied.
# FILES: everything actually shipped to the server (PY_FILES plus non-Python
# files like requirements.txt, which py_compile would wrongly try to parse
# as Python and reject — learned the hard way shipping the bcrypt fix).
PY_FILES=(enrollment.py presence_enroll_api.py routing.py headscale.py db.py main.py home_egress_api.py)
FILES=("${PY_FILES[@]}" requirements.txt)

say() { printf '\n\033[1;35m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

# --- preflight ---------------------------------------------------------------
say "Preflight"
for f in "${FILES[@]}"; do
  [[ -f "$f" ]] || die "Missing $f — run this from atlas-dashboard-src/"
done
[[ -f static/presence.html ]] || die "Missing static/presence.html"

python3 -m py_compile "${PY_FILES[@]}" || die "Python syntax error — not deploying."
echo "  local syntax OK"

$SSH "test -d $APP_DIR" || die "Cannot reach $APP_DIR on $ATLAS_HOST"
echo "  reached $ATLAS_HOST"

# Verify the compose file and service exist BEFORE copying anything. Discovering
# this after the copy (as happened on the first run) leaves new code on disk
# with the old container still serving it — a confusing half-deployed state.
$SSH "test -f ${COMPOSE_DIR}/docker-compose.yml" \
  || die "No docker-compose.yml in ${COMPOSE_DIR}. Find it with:
    ssh ${ATLAS_USER}@${ATLAS_HOST} 'find /root /opt -maxdepth 3 -name docker-compose*.y*ml'
  then re-run with:  COMPOSE_DIR=/path/to/dir ./deploy-enrollment.sh"

if ! $SSH "cd ${COMPOSE_DIR} && docker compose config --services 2>/dev/null | grep -qx '${SERVICE}'"; then
  if $SSH "cd ${COMPOSE_DIR} && docker-compose config --services 2>/dev/null | grep -qx '${SERVICE}'"; then
    COMPOSE="docker-compose"
    echo "  using Compose v1"
  else
    die "Service '${SERVICE}' not found in ${COMPOSE_DIR}. Available:
$($SSH "cd ${COMPOSE_DIR} && docker compose config --services 2>/dev/null" || true)"
  fi
fi
echo "  compose OK: ${COMPOSE_DIR} / service ${SERVICE}"

# main.py must wire the router in ABOVE the static mount, or the catch-all
# swallows every new route. Verified locally rather than discovered in prod.
grep -q "include_router(presence_enroll_api.router)" main.py \
  || die "main.py is missing the include_router line."
if [[ $(grep -n 'app.mount("/"' main.py | cut -d: -f1) -lt \
       $(grep -n 'include_router(presence_enroll_api' main.py | cut -d: -f1) ]]; then
  die "include_router must appear BEFORE app.mount(\"/\") in main.py."
fi
echo "  router ordering OK"

# db.py gains two tables and three functions this round. init_db() uses
# CREATE TABLE IF NOT EXISTS, so it is safe to re-run against the live database
# and will not touch existing users or personas.
say "Checking database safety"
$SSH "test -f ${APP_DIR}/atlas.db" \
  && echo "  existing atlas.db found — path_history will be added, users/personas untouched" \
  || echo "  no atlas.db yet — will be created on first start"

# --- backup ------------------------------------------------------------------
# NOTE: if a previous run copied files but failed before rebuilding, this
# backup captures THAT state, not the last-known-good one. Keep the earliest
# .bak-* directory around until a deploy fully succeeds — that's the real
# rollback point. (Learned the hard way on Aug 5.)
say "Backing up to ${APP_DIR}.bak-${STAMP}"
$SSH "cp -a $APP_DIR ${APP_DIR}.bak-${STAMP} && ls -d ${APP_DIR}.bak-${STAMP}"
# The database is inside APP_DIR, so the -a copy above already captures it.
$SSH "test -f ${APP_DIR}.bak-${STAMP}/atlas.db && echo '  database included in backup' || true"

# --- copy --------------------------------------------------------------------
say "Copying files"
scp "${FILES[@]}" "${ATLAS_USER}@${ATLAS_HOST}:${APP_DIR}/"
scp static/presence.html static/index.html static/manifest.json static/icon-192.png static/icon-512.png \
    static/apple-touch-icon.png static/favicon-32.png \
    "${ATLAS_USER}@${ATLAS_HOST}:${APP_DIR}/static/"

# --- rebuild -----------------------------------------------------------------
say "Rebuilding container"
# Only this service — headscale, caddy and bank-demo share the compose file and
# must not be restarted. Restarting headscale mid-deploy would drop the mesh.
$SSH "cd ${COMPOSE_DIR} && ${COMPOSE} build ${SERVICE} && ${COMPOSE} up -d ${SERVICE}"

# --- health ------------------------------------------------------------------
# The container publishes NO ports to the host (confirmed Aug 5: its Ports
# column in `docker ps` is empty) — Caddy reaches it over the Docker network.
# So `curl http://localhost:8000/health` ON THE HOST always fails, healthy app
# or not. An earlier version of this script did exactly that and triggered a
# spurious rollback on a perfectly good deploy.
#
# Check from inside the container first (the image ships curl), then fall back
# to the public URL through Caddy.
say "Health check"
sleep 6
OK=0
for i in 1 2 3 4 5 6 7 8 9 10; do
  if $SSH "docker exec ${SERVICE} curl -fsS -m 5 http://localhost:8000/health" >/dev/null 2>&1; then
    OK=1; echo "  healthy (from inside container)"; break
  fi
  if $SSH "curl -fsS -m 5 ${PUBLIC_URL}/health" >/dev/null 2>&1; then
    OK=1; echo "  healthy (via Caddy)"; break
  fi
  echo "  waiting for app to come up ($i/10)…"
  sleep 3
done

if [[ $OK -ne 1 ]]; then
  say "App did not come up — ROLLING BACK"
  $SSH "rm -rf $APP_DIR && mv ${APP_DIR}.bak-${STAMP} $APP_DIR && cd ${COMPOSE_DIR} && ${COMPOSE} up -d --build ${SERVICE}"
  die "Rolled back to the previous version. Check: docker logs atlas-dashboard"
fi
echo "  /health OK"

# The new routes must actually be registered. 401 is the correct answer to an
# unauthenticated call — it proves the route exists and is guarded. A 404 would
# mean the static mount ate it.
say "Verifying new routes are registered"
CODE=$($SSH "curl -s -o /dev/null -w '%{http_code}' -m 5 ${PUBLIC_URL}/api/presence/lens")
if [[ "$CODE" == "401" ]]; then
  echo "  /api/presence/lens -> 401 (registered and correctly guarded)"
elif [[ "$CODE" == "404" ]]; then
  die "/api/presence/lens returned 404 — the static mount is shadowing the router."
else
  echo "  /api/presence/lens -> $CODE (unexpected, but the route exists)"
fi

say "Deployed"
cat <<EOF

  Client app:  https://dashboard.rpnwireless.com/presence.html
  Backup kept: ${APP_DIR}.bak-${STAMP}

  Smoke test from the Mac:

    curl -s -X POST https://dashboard.rpnwireless.com/api/presence/signup \\
      -H 'Content-Type: application/json' \\
      -d '{"email":"demo@rpnwireless.com","password":"demo1234"}'

    # then, with the token it returns:
    TOKEN=...
    curl -s -X POST https://dashboard.rpnwireless.com/api/presence/provision \\
      -H "X-Presence-Token: \$TOKEN" -H 'Content-Type: application/json' \\
      -d '{"q1":"consistent","q2":"all","q3":"London, United Kingdom","q4":"place","q5":"simple"}'

    curl -s -X POST https://dashboard.rpnwireless.com/api/presence/enroll \\
      -H "X-Presence-Token: \$TOKEN" -H 'Content-Type: application/json' \\
      -d '{"platform":"macos"}'

  Rollback if needed:
    ssh ${ATLAS_USER}@${ATLAS_HOST} "rm -rf ${APP_DIR} && mv ${APP_DIR}.bak-${STAMP} ${APP_DIR} && cd ${COMPOSE_DIR} && ${COMPOSE} up -d --build ${SERVICE}"

EOF
