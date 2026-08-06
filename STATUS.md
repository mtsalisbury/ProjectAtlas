# Project Atlas — Status

**This is the one file to update.** Everything about where the project stands lives here now — not spread across separate documents. If something changes, it changes here, in the relevant section below, nowhere else.

**Last updated:** August 5, 2026

---

## Part 0.1 — August 5 Session: The Client Tail — Enrollment, Lens, Real Questionnaire

**The two gaps named at the end of Part 3.8 are now closed in code.** Part 3.8 ended with two explicit admissions: the questionnaire frontend "still uses fake local JavaScript state," and "nothing yet tells their actual device to select and use that exit node." Both are now built, and tested against a stubbed Headscale with 59 assertions passing.

**New: `enrollment.py`** — the Headscale wrapper that ties a client device to the mesh. Same `docker exec headscale ...` pattern as `headscale.py`/`presence_provision.py`, no new dependencies.
- `create_preauth_key()` — single-use and 1-hour by default. A reusable key is a standing invitation to join someone's Presence; that has to be a deliberate choice, never a default.
- `register_node()` + `normalize_node_key()` — mobile path. Accepts the full registration URL, a bare key, a `nodekey:`-prefixed key, or any of those with stray whitespace/uppercase. Refusing to parse a pasted URL is a self-inflicted support ticket.
- `build_enrollment_instructions()` — generates the real per-platform command **server-side**, so the coordination-server URL and exit-node name can't drift out of sync with what the mesh actually has. This directly guards against the failure recorded in the Aug 4 H5 run, where the stock Tailscale app defaulting to Tailscale's own servers surfaced as a confusing 401.

**New: `presence_enroll_api.py`** — an `APIRouter` adding five client routes: `POST /api/presence/enroll`, `POST /api/presence/enroll/mobile`, `GET /api/presence/enroll/keys`, `POST /api/presence/enroll/revoke`, `GET /api/presence/lens`. All authenticate with `X-Presence-Token`, never the admin `ATLAS_TOKEN`.

**`main.py` — two lines only.** An import, and `app.include_router(...)` placed **above** `app.mount("/", StaticFiles(...))`. The catch-all static mount silently swallows any route registered after it; the deploy script verifies this ordering before it will push, and verifies `/api/presence/lens` returns 401 (not 404) afterwards.

**`static/presence.html` — the fake state is gone.** The prototype's `state` object and `populateLens()` local-render are replaced with real calls: "Build my Presence" now POSTs to `/api/presence/provision`, and the Lens renders from `GET /api/presence/lens`. Two new screens (auth, enrollment) were appended to the existing `screens` array rather than prepended, so the existing `welcome=0 / q1=1 … q5=5` indices the inline `onclick` handlers depend on stay valid. Original CSS and question wording untouched.

**The Lens now reports honestly rather than optimistically.** It shows the matched exit node *and* whether that node is actually online *and* whether its `0.0.0.0/0` route was ever approved. Naming a matched exit node without those two checks would be a false green light — precisely the class of error that cost a full day of debugging on Aug 3 before the missing `autogroup:internet:*` ACL rule was found.

**Verified by test, not by assertion (59/59 passing).** Notable cases, run against a stub emulating the real Headscale CLI surface:
- Enrollment *before* provisioning returns a clean 409 with a human message, not a 500.
- The Lens returns 200 and renders even when the mesh is unreachable — matching Part 3.5's principle that visibility must not require connectivity.
- `q3` (home address) correctly drives exit-node matching: "London, United Kingdom" → `EGR-Lon1`, "Toronto, Ontario" → `EGR-Tor1`.
- The ACL rewrite preserves pre-existing group members *and* the `autogroup:internet:*` rule.
- **Isolation holds between two real Presences**: each sees only its own device, no overlap, and a client token gets 401 from `/api/topology`.
- Full pre-auth keys are never returned by the list endpoint — only an 8-character prefix.

**Honest limits — what this does NOT do:**
- **Mobile is still not zero-touch, and the code says so out loud** (`zero_touch: False`). Part 2's finding stands and was not re-litigated. What changed is that the *administrator* is out of the loop: previously someone had to reach Mike so he could run `headscale nodes register` by hand; now they paste the link their own app already shows them. One-paste and self-service, not zero-touch.
- **Nothing here verifies the device actually selected the exit node.** The desktop command includes `--exit-node=`, and the Lens reports whether the egress is healthy — but confirming real traffic is leaving via that egress still needs the existing exit-node test panel. The client tail issues the instruction; it does not yet prove compliance.
- **Not deployed as of this writing.** `deploy-enrollment.sh` is written, syntax-checked, and does backup → copy → rebuild → health-check → automatic rollback, but has not been run.

**Flagged, not fixed — `db.py` password hashing is weak.** `hash_password()` is a single round of unsalted-construction SHA-256 (`sha256(salt + password)`). It is fast by design, which is exactly wrong for password storage — a commodity GPU tries billions of these per second. For a solo demo with test accounts this is not urgent; before any real person creates an account it should move to `bcrypt`, `scrypt`, or `argon2id`. Logged here rather than changed, since it touches existing working auth and wasn't in scope tonight.

---

## Part 0.2 — August 5 Session, Second Build: Route Path Selection

**Declared origin is now a control, not an assignment.** Before this, `match_exit_node()` did a one-time keyword match against the home address at signup, and that egress was permanent. A traveler — the entire use case — could not re-declare where they appeared from. That's now fixed: a person changes their declared origin from the Lens, at will.

**New: `routing.py`**
- `list_exit_nodes()` discovers egress **live from Headscale**, filtering to nodes with an approved `0.0.0.0/0` route. Deliberately not read from the hardcoded `EXIT_NODE_MAP` keyword table — adding a droplet in a new region should make it selectable without a code change, and a stale list would either hide real capacity or offer egress that no longer exists.
- `resolve_path()` **rejects an offline egress with a readable message**, rather than accepting it. Letting someone select a dead exit node would reproduce exactly the symptom that cost a full day on Aug 3: a connection that looks established but passes no traffic.
- `build_switch_command()` emits `tailscale set` rather than `tailscale up` — changes one setting on a live connection instead of re-running the login flow, so it won't prompt for re-auth. It includes `--exit-node-allow-lan-access` by default, because Part 3.5 names that setting specifically as "buried, non-obvious, and meaningless to someone who isn't a network engineer." Without it, choosing an exit node silently kills printers and NAS access and the person has no idea why.
- **"Where I actually am" is a first-class option**, not the absence of one. Presenting honestly is a legitimate choice, and a null exit node is now visibly distinct from an unset one.

**New routes:** `GET /api/presence/paths` (live options, current marked, offline shown-but-disabled rather than hidden), `POST /api/presence/path` (change origin, returns a plain-language summary and the command to apply), and `GET /api/presence/enroll/mobile-steps`.

**`db.py`:** new `path_history` table plus `set_persona_exit_node()`, `record_path_change()`, `get_path_history()`. Persona rows are **updated in place** rather than duplicated — the questionnaire answers didn't change, only the presentation; the audit trail belongs in `path_history`. `get_latest_persona()` now orders by `id` rather than `built_at`, since two rows written in the same second were previously ambiguous and "latest" has to be exact.

**Bug caught and fixed during this build:** clicking the mobile tab was minting a fresh pre-auth key every time — a credential the mobile flow can't even redeem. Split out to a GET endpoint that renders instructions without issuing anything.

**Tested: 53 new assertions, plus the 59 enrollment assertions re-run green (112 total).** Notable cases: switching London→Toronto→direct→London persists correctly and the Lens reflects each change; an unknown egress and an offline egress both return 400 with a human-readable reason; **rejected attempts write no history**, because a change that was refused is not a change and polluting the audit trail would make it useless as a record; two Presences keep entirely separate paths and histories; questionnaire answers survive path changes untouched.

**Migration verified against a simulated live database**, not just a fresh one: an old-schema DB seeded with a real user and persona was run through the new `init_db()` — user survived, persona survived, `path_history` added, original answers untouched. `CREATE TABLE IF NOT EXISTS` means the deploy is safe against the existing `atlas.db`, and the script's `cp -a` backup captures the database alongside the code.

**Honest limit, unchanged and worth restating:** Headscale **cannot push** an exit-node selection to a client — that is a client-side Tailscale setting; the coordination server grants permission to route, it does not dictate the route. So this API is authoritative about *intent* and returns the command that applies it; the device still performs the switch. The endpoint is deliberately shaped for the future native client agent (Part 3.5) to consume, so that agent won't need a different contract when it arrives — it will simply apply the change itself with nothing to paste.

**Caught before deploy — Headscale v0.29.3 requires numeric user IDs.** A pre-flight check against the live server (rather than trusting the stub) surfaced a real incompatibility:

```
docker exec headscale headscale preauthkeys create --user presence-user-1 --expiration 1h
Error: invalid argument "presence-user-1" for "-u, --user" flag:
strconv.ParseUint: parsing "presence-user-1": invalid syntax
```

Every `--user` flag on this version wants the numeric ID, not the name — while `headscale users create <name>` still takes a name, which is why provisioning worked on Aug 4 and enrollment would have failed. Four call sites were affected: `preauthkeys create`, `preauthkeys list`, `preauthkeys expire`, `nodes register`.

Fixed with `resolve_user_id()` (name → ID via `users list --output json`, cached) plus `_headscale_for_user()`, which tries the ID form first and falls back to the name form. Older Headscale wanted names, so this survives a downgrade without a code change. **The test stub was then corrected to reproduce the real v0.29.3 error**, and both suites re-run green against it — plus a third run against a simulated name-only server to prove the fallback. Had the stub not been corrected, the tests would have kept passing against behaviour the real server doesn't have.

Live user IDs for reference: `personal`=1, `employment`=2, `pseudonymous`=3, `employment-other-person-test`=4, `presence-user-1`=6.

**Also fixed pre-deploy: exit nodes are now selected by mesh IP, not name.** `--exit-node=EGR-Tor1` depends on MagicDNS being enabled, which is optional on Headscale and often off, and names get normalised (`EGR-Tor1` → `egr-tor1`). The `100.64.x.x` address is unambiguous. The friendly name still appears in the explanation text, since an IP means nothing to a person reading it.

**Still not deployed.** Both builds are staged in `atlas-dashboard-src/`, awaiting `./deploy-enrollment.sh`. Test count: **114 assertions** (60 enrollment + 54 path).

---

**Environment note for future sessions:** SSH from the Cowork sandbox to the droplets is not possible — that environment has no network interface and reaches the world through a domain-allowlisted proxy, which returns `Forbidden` for `192.241.147.167:22` and `mesh.rpnwireless.com:22` while allowing `github.com:22`. Source has to be copied into the connected folder (`scp -r root@... ./atlas-dashboard-src`) for editing, then deployed from the Mac. Claude Code running in a terminal on the Mac itself would not have this limitation.

---

## Part 0.3 — August 5 Session, Evening: Go-Live Runbook, Lens Honesty Fix, PWA, Toronto Rebuild

**Ran the Client Tail Go-Live runbook (`ops/Runbook-Client-Tail-GoLive.md`) against the real, live server.** Step 1 (deploy) turned out to have already happened in an untracked prior moment — the enroll/paths routes answered live with real data before any deploy was run tonight. Step 2 (API smoke test) passed cleanly: signup, provision (real Headscale user `presence-user-2`, real ACL restart), paths, and enroll-key generation all returned exactly what the runbook expected.

**A genuinely new, better-isolated finding: the Mac itself cannot consume *any* exit node — this was very likely never actually true before either, despite reading as solved.** Re-tested declared-origin switching directly on the Mac (Step 3), and it failed the same way for both London and NY, even after a full `tailscale down`/`up` cycle to rule out a stale WireGuard session. Diagnosis, in order:
- ACL confirmed still correct (`group:personal` → `autogroup:internet:*`, the Aug 3 fix is intact, not a regression).
- London's NAT, forwarding, UFW, and rp_filter all checked out correct — and London was *simultaneously* forwarding Toronto's real traffic to `8.8.8.8` and back throughout the test.
- `tailscale ping` from the Mac to London succeeded directly (87ms) — the peer-to-peer tunnel itself is healthy.
- Packet capture on London during a live attempt showed WireGuard handshake traffic arriving from the Mac's public IP, but **zero decapsulated packets from the Mac's tunnel address (100.64.0.4) ever appeared** — the data plane specifically for the Mac's own traffic never comes through, even though the control-plane handshake does.
- On the Mac's own side: `route get`, interface counters, and the local routing table all confirm outbound traffic *is* correctly entering the tunnel interface (`utun12`) — hundreds of packets sent during a test window, almost none returned.
- Swapping the exit node from London to NY (`atlas-mesh`, the control-plane server, otherwise flawless) reproduced the identical failure — ruling out any specific droplet and pointing at the Mac (or its current network) as the common factor.
- `tailscale netcheck` was clean this time — no `FetchRIB` error — so this isn't necessarily the same signature as the previously-tracked `tailscale/tailscale#3299`, though it may be related.

**The correction this forces on the record: the "SOLVED, same day" proof earlier in this document was run with Toronto as the traveling client, never the Mac.** That proof stands — Toronto-as-client through London is real, confirmed, and reconfirmed again tonight. But "the Mac can select an exit node and get real routed traffic" has apparently never actually been demonstrated in this project. This is now a real, open, reproducible bug, isolated far more precisely than before — not a re-run of old ground.

**Found and fixed a real honesty gap in the Lens itself.** While diagnosing the above, `headscale nodes list-routes` showed Toronto's exit route as `Approved` but with `Available`/`Serving` both blank — its own `tailscaled` wasn't currently advertising the route it was approved for. `/api/presence/paths` and `/api/presence/lens` were reporting Toronto as a healthy option anyway, because `headscale.py` only ever read Headscale's `approved_routes` field and never looked at `subnet_routes` (what's actually being served right now). Fixed:
- `headscale.py` now also captures `subnet_routes` as `serving_routes`.
- `routing.py` gained `_is_serving_exit_route()`; `list_exit_nodes()` and `resolve_path()` now require a route to be both online *and* actually serving before calling it available, with a distinct error message when a node is online-but-not-serving versus genuinely offline.
- `enrollment.py`'s `get_exit_node_info()` and the `/api/presence/lens` response both gained an `exit_route_serving` field alongside the existing `exit_route_approved`.
- `static/presence.html` now shows a third pill ("route serving" / "route not serving") in the Lens header, and the path picker distinguishes "offline" from "approved but not currently serving" in its unavailable-reason text.
- Deployed and verified live: Toronto correctly shows `serving_route: false, available: false` post-fix; London and NY both show `true`.

**Built and deployed real PWA support for `presence.html` — installable on a phone home screen with no app store, no review.** Generated a proper icon set (`icon-192.png`, `icon-512.png`, `apple-touch-icon.png`, `favicon-32.png`) from the existing canonical double-ring brand mark already inline in the page, using `qlmanage` to rasterize an SVG source (no image tooling was otherwise available) plus `sips` for resizing. Added `manifest.json` and the standard Apple meta tags (`apple-mobile-web-app-capable`, etc.). Confirmed live on a real iPhone: installed via Safari's Add to Home Screen, launches full-screen with no browser chrome. The hard platform limit stays explicit in the code comment: a web page, however installed, cannot establish or control a VPN connection — that needs `NetworkExtension`/`VpnService`, native capabilities no PWA can reach. The stock Tailscale app remains the thing that actually carries the tunnel; this is, and can only be, the visibility/control layer around it.

**Found and fixed a real routing bug: `presence.rpnwireless.com` was serving a stale, disconnected prototype, not the real app.** The domain the person-facing app is actually supposed to live at was pointed by Caddy at a separate static directory (`/root/atlas-mesh/presence-site`) containing a 667-line snapshot of `presence.html` from before Part 0.1's backend wiring — the old fake-local-JavaScript-state version, with no backend behind it at all. Fixed by changing that Caddy block to `rewrite / /presence.html` + `reverse_proxy atlas-dashboard:8000`, matching how `dashboard.rpnwireless.com` is served. Verified live: `presence.rpnwireless.com/api/presence/lens` now returns a real `401` (proving it hits the actual FastAPI backend) instead of static-file behavior. The old `presence-site` directory was left in place but is now unreferenced — not deleted.

**Toronto (`EGR-Tor1`) was found completely wedged, then rebuilt from scratch.** SSH was unreachable on every path tried (public IP, mesh IP, repeated) even after a graceful reboot; the DigitalOcean web console also failed to connect. Packet capture incidentally caught the likely cause: a leftover `ping` process from an earlier test session, running once a second, apparently never cleaned up, on a 512MB droplet with little headroom. A hypervisor-level Power Cycle didn't bring SSH back either, so the droplet was rebuilt from a clean Ubuntu 24.04 base image via DigitalOcean's Rebuild action (same IP and droplet ID retained, no DNS or mesh config needed to change).

Reconfigured from scratch and confirmed matching London's known-working setup:
- Old dead node entry (ID 10) deleted from Headscale before re-registering, so there's no stale duplicate.
- Tailscale installed, registered against `mesh.rpnwireless.com` with `--advertise-exit-node --advertise-routes=0.0.0.0/0,::/0`.
- `net.ipv4.ip_forward=1` persisted via `/etc/sysctl.d/99-tailscale.conf` (not just set for the current boot — this was almost certainly missing before and is a real candidate for why Toronto never actually served its route even when it *was* up).
- UFW confirmed inactive, matching London.
- Routes now show `Approved` + `Available` + `Serving` all populated in `headscale nodes list-routes` — renamed to `EGR-Tor1` (node ID 13, `100.64.0.6`).
- Confirmed no leftover background processes on the fresh box.

**Update, same night: live traffic verification was completed after all — Toronto's exit-node forwarding is now proven with real traffic, not just config.** London and NY can't double as test clients while still advertising as exit nodes themselves — Tailscale refuses to let a node be a provider and a consumer at the same time (`Cannot advertise an exit node and use an exit node at the same time`) — and the Mac can't be used either, for the reason above. So London was temporarily un-advertised as a provider (`tailscale set --advertise-exit-node=false`) and pointed at Toronto as its own exit node instead. Packet capture on Toronto during that test showed the real proof: London's traffic (`100.64.0.7`) fully decapsulating on Toronto's `tailscale0` — a complete TCP+TLS handshake and clean session close to a real destination (the `curl` to icanhazip.com), and three real ICMP echo requests to `1.1.1.1` with real replies. Toronto genuinely forwards third-party traffic correctly.

**The cost of that test: London self-locked, the same known failure mode from earlier in this project, but with a new wrinkle worth recording.** The moment London switched to consuming an exit node, it lost its own SSH session over its public IP, exactly as documented. A reboot did **not** recover it this time — unlike Toronto's wedge (a resource-exhaustion problem a reboot clears), London's problem was a *persisted setting*: Tailscale saves the exit-node selection to `/var/lib/tailscale/tailscaled.state`, so on every reboot `tailscaled` started back up and immediately reapplied "route everything through Toronto," recreating the same lockout before SSH ever became reachable. Recovered via the DigitalOcean web Console (works over a virtual serial connection, independent of the box's own broken networking) — logged in with a DO-reset root password, ran `tailscale set --exit-node=` directly at the console, and SSH came back immediately. Restored London's provider role afterward (`--advertise-exit-node --advertise-routes=0.0.0.0/0,::/0`); Headscale's route approval for it survived untouched (same node ID, same prior approval). **Worth remembering distinctly from the Toronto recovery: a wedged box needs a reboot/power-cycle; a self-locked box needs its persisted Tailscale state cleared at the console — a reboot alone won't fix the second kind, and may look identical from the outside.**

Final state, confirmed clean: all three exit nodes (`EGR-Lon1`, `atlas-mesh`, `EGR-Tor1`) show `Approved` + `Available` + `Serving` populated in `headscale nodes list-routes`. Toronto moved from config-only to fully live-traffic-verified in the same session as its rebuild.

**New: `ops/setup-exit-node.sh`** — automates everything tonight's Toronto rebuild did by hand: install Tailscale, clean up any stale node entry with the same name, register with `--advertise-exit-node --advertise-routes=0.0.0.0/0,::/0`, persist `ip_forward` (the near-certain reason Toronto's route was approved but never actually served, even before it got wedged), check UFW without touching it, approve the routes, and rename to the mesh's naming convention. Run as `DROPLET_IP=... NODE_NAME=EGR-XYZ1 ./setup-exit-node.sh` against a freshly rebuilt droplet. Deliberately does **not** automate the live-traffic verification step — that requires a live peer to temporarily give up its own provider role and risk self-locking, which needs a human at the DigitalOcean console to recover from, not something to run unattended.

**One real bug hit while writing it, worth remembering for any future script:** bash fails to parse an apostrophe inside a `${VAR:?message}` or `${VAR:-message}` parameter expansion, even when the whole thing is inside double quotes — a contraction like "droplet's" in the error message broke the entire script with a confusing, far-away "unexpected EOF" error. Fixed by avoiding apostrophes in those specific messages.

**`deploy-enrollment.sh`'s `FILES` array was missing `headscale.py`**, which the Lens fix above depends on — fixed, so future deploys of this area won't silently skip it.

---

## Part 0 — August 4 Session: Live Admin Dashboard, Access Lock, H5 Proven on Real Hardware

**A working, token-gated admin dashboard now exists and is live at `http://100.64.0.8:8000` (mesh-only, not public yet).** Built as a FastAPI backend (`main.py`, `headscale.py`, `h6_test.py`, `exit_test.py`, `h5_test.py`) serving a single-page frontend styled to Project Atlas branding (dark navy/gold, Space Grotesk + IBM Plex Mono). This turns the hypothesis tests from one-off SSH/manual proofs into repeatable, one-click, logged tests.

**What the dashboard does, confirmed live today:**
- **Live mesh topology view** — every node, context, online/offline status, IP addresses, routes, last-seen, pulled straight from `headscale nodes list --output json`.
- **H6 panel** — two-button snapshot/compare flow with a detail modal, wired to the same server-side logic already proven in Paper 002. Now has a real UI, not just a server-side proof.
- **Exit-node check panel** — select an exit node, run a live check against known egress IPs (London `144.126.200.88`, Toronto `134.122.41.187`), pass/fail with full detail view.
- **Access lock, built and verified end-to-end today:**
  - Backend token check via `X-Atlas-Token` header on every `/api/*` route (401 without it, 200 with it) — confirmed.
  - systemd bound to the mesh IP (`100.64.0.8:8000`) instead of `127.0.0.1` — no more SSH tunnel required, reachable directly over the mesh.
  - Frontend login overlay ("ATLAS ADMIN — LOCKED") gating all API calls through an `authFetch` wrapper — confirmed working in-browser.
- **H5 (device recovery) — proven today on a real device, not a test node.** Added `expire_node()` to the Headscale wrapper (`headscale nodes expire -i <id>`) and a new `h5_test.py` that snapshots the full mesh before/after expiring a target node, asserting every *other* node's online status, IPs, and context are unchanged. Ran it against a real iPhone in the `personal` context: **passed** — other devices unaffected, iPhone cleanly expired. Confirmed the *full* recovery loop too: the iPhone needed its Tailscale client re-pointed at the correct custom coordination server (`https://mesh.rpnwireless.com` — stock Tailscale app defaults to Tailscale's own servers, not Headscale, which produced an unrelated 401 at first), then `headscale auth register --auth-id <id> --user personal` from the server side, then reconnected successfully. This is a genuinely stronger H5 result than the earlier version — it proves the full real-world recovery path, not just the isolation guarantee.

**Architectural refinement — ACL isolation model clarified (see Part 2 for the permanent principle):** Isolation between contexts is **default-isolated, user-controlled**, not absolute. The mesh should prevent *involuntary* crossing between contexts (inference, leakage, third-party visibility) — it isn't meant to lock the identity owner out of their own resources, since all contexts belong to the same person choosing to present differently, not to adversaries. This reframes the planned ACL isolation test: it should validate "nothing crosses without deliberate user action," not "nothing can ever cross." Building a formal test for this is deferred, pending a clearer definition of what deliberate cross-context bridging should look like.

**Updated roadmap status:**
1. ✅ Scaffold API, Headscale wrapper, topology endpoint
2. ✅ H6 test — dashboard panel, live
3. ✅ Exit-node test — dashboard panel, live
4. ✅ Frontend styled to Atlas branding
5. ✅ Access lock — token-gated backend + login screen, verified live
6. ✅ H5 test — device recovery, verified live on real hardware, full reconnect loop confirmed
7. 🔄 ACL isolation — reframed as "no involuntary crossing," formal test deferred pending design of user-controlled bridging
8. ✅ Deployment — dashboard containerized and live at `https://dashboard.rpnwireless.com` with a valid Let's Encrypt cert, matching the existing `headscale`/`caddy`/`bank-demo` pattern (same `docker-compose.yml`, same Caddy auto-TLS). Old systemd instance (bound to `100.64.0.8:8000`) retired and disabled — the containerized version is now the only live instance.

**Deployment notes for future reference:**
- Dashboard container needs the Docker socket mounted (`/var/run/docker.sock`) and the Docker CLI installed in its image, since it shells out to `docker exec headscale ...` to read mesh state. This is a deliberate, accepted tradeoff for a single-admin, token-gated internal tool — not something to casually replicate for anything more exposed.
- Log directory (`/opt/atlas-dashboard/logs`) is bind-mounted from the host into the container so H6/exit-node/H5 run logs persist across container rebuilds and match the host's existing log history.
- After any Caddyfile edit, Caddy does not auto-reload — run `docker exec caddy caddy reload --config /etc/caddy/Caddyfile` explicitly.

---

---

## Part 1 — What's Actually Built and Working

**Infrastructure (real, live, tested):**
- Self-hosted Headscale mesh server on DigitalOcean, behind Caddy with automatic TLS, at `mesh.rpnwireless.com`.
- Three isolated contexts (`personal`, `employment`, `pseudonymous`).
- ACL policy enforcing contexts can't reach each other — built, tested, confirmed.
- A working demo relying party at `bank-demo.rpnwireless.com` — see Part 3, this is new as of tonight.
- **Cross-relying-party recognition, without a new passkey enrollment.** A second demo service ("Atlas Demo Airline") correctly recognized the same Presence using a token issued by the first, with no separate WebAuthn registration — tested with a full set of pass/fail cases (no token, garbage token, valid token, expired token) before ever touching a browser.
- **A visible browser signal for Presence support.** A real Chrome extension, tested in both directions on a live site: active (blue) on the demo bank, inactive (gray) everywhere else, driven by a genuine `.well-known` file check, not a hardcoded list.

**Research results, independently verified and published (Atlas Paper 002, Sections 21–22):**
- **H6 (persistence across transport changes):** confirmed.
- **H5 (device recovery):** confirmed, with a real finding — client-side status can lag behind actual server-side state.
- **Cross-context isolation:** failed by default, fixed with an explicit ACL policy, re-tested and confirmed.

**The public site** (`mtsalisbury.github.io/ProjectAtlas`): fully rebuilt, every file verified, one stylesheet, old broken pages retired, repo cleaned of clutter and secrets.

**Operational documentation (in `ops/`):** `KB-Device-Onboarding-Flow.md`, `Runbook-OIDC-Setup.md` — these stay as separate reference playbooks, not status; they don't change often and aren't part of the "one thing to update."

**Declared-origin routing test (Toronto/London exit-node experiment):** SOLVED and confirmed live. Root cause was a missing ACL permission (the policy never granted internet access through an exit node), not any infrastructure problem — full detail below.

*First attempt:* London was the traveler (consuming an exit node), not the provider. It locked itself out of both the Web Console and direct SSH the moment the exit-node route was applied — destroyed and rebuilt as a result.

*Second attempt, redesigned correctly:* both Toronto and London set up as egress-only providers (never consuming an exit node themselves), with the Mac — physically present, zero lockout risk — as the one selecting an exit node. This design was right and should be the standard going forward. Toronto and London both registered and route-approved cleanly. But live testing surfaced a specific, well-diagnosed failure: **selecting London as an exit node from the Mac drops all traffic completely — the VPN interface stays connected, but nothing passes in either direction.** Methodically ruled out, in order: UFW (inactive), the NAT/MASQUERADE rule (present), kernel IP forwarding (confirmed on, `net.ipv4.ip_forward = 1`). Every individual piece checks out correct; the whole doesn't work regardless. This points to something in how this specific droplet's network interface or DigitalOcean's networking layer interacts with Tailscale's exit-node routing — a real, specific, bounded problem, not "it doesn't work."

**Next session should start here, not from scratch:** try a different cloud provider or droplet configuration for the exit-node role, or search specifically for known DigitalOcean + Tailscale exit-node compatibility issues before further manual debugging. Toronto was never actually tested as the exit node with live traffic (only approved) — worth trying Toronto before assuming the same failure applies there too.

**Third attempt, same day — the real breakthrough: this is very likely a client-side problem, not a server-side one.** A fourth exit-node provider was set up (NY itself, the control-plane server, which has run flawlessly for two straight days) specifically to test whether the failure was tied to any particular droplet. It failed identically. That ruled out Toronto, London, and NY all being individually broken — three unrelated servers don't share the same specific bug. What they do share is being tested from the same Mac, repeatedly, over many hours. Running `tailscale netcheck` on the Mac surfaced a real, repeatable local error: `routerIP/FetchRIB: sysctl: cannot allocate memory`.

**Confirmed: this is a known, documented upstream bug in Tailscale's own macOS client** — found a matching, exact-text report in Tailscale's official GitHub issue tracker (`tailscale/tailscale#3299`), describing the identical error and the identical symptom (connections that should work drop to broken/relay-only). This is not anything specific to our build — not Headscale, not the mesh design, not any of the four servers, all of which are correctly configured and approved as of tonight and need no further changes.

**Final result for today, corrected after a same-day follow-up test:** a full Mac restart was tried and did not resolve the Mac-specific `FetchRIB` error — that remains a real, separately-tracked upstream Tailscale macOS bug (`tailscale/tailscale#3299`), worth filing a comment on with today's findings, but it turned out **not to be the actual blocker for the core test.**

**The real, generalizable finding: any remote box that selects an exit node for its own traffic risks locking itself out — the "own traffic" it reroutes includes the SSH session managing it.** Confirmed directly: Toronto, a Linux droplet with no prior issues, selected London as its exit node and immediately lost its own SSH connection — the identical pattern as London's crash the first time this morning, on a completely different operating system. This rules out "macOS bug" as the root cause of the exit-node lockouts specifically; that bug is real but separate. **The Mac never showed this failure only because of physical presence, not its OS** — a remote-access loss on a laptop you're sitting in front of is a non-event; the same thing on a headless cloud box requires a hypervisor-level recovery.

**The actual safe operating principle going forward: recovery via the cloud provider's dashboard (Power Cycle/Reboot) works independent of the guest OS's own networking, since it's a hypervisor-level action, not something routed through the box's own network stack.** Any test where a remote node consumes an exit node should be planned expecting to need a power cycle afterward — not as a failure, as a normal part of the test. The mesh SSH address (a node's `100.64.x.x` IP, not its public IP) was also confirmed today as a genuinely protected management path — Toronto's SSH session survived selecting London as an exit node when reached this way, unlike every earlier attempt over public IPs. **Always SSH to mesh addresses going forward, not public ones.**

**Same-day follow-up: the exit-node traffic failure was diagnosed to a precise, specific point using live packet capture — real evidence, not more guessing.** Methodically ruled out on London (the provider): UFW (inactive), DigitalOcean Cloud Firewalls (none exist on the account at all), the NAT/MASQUERADE rule (present and correctly configured), kernel IP forwarding (confirmed on), rp_filter (already in loose mode, not strict), policy routing (nothing unusual). Every individual piece on London checks out correct.

**The actual finding, via direct packet capture on both ends:** Toronto's own `tailscale0` interface shows real outbound ICMP echo requests leaving toward 8.8.8.8 — confirmed, Toronto is correctly handing traffic to Tailscale. London's `tailscale0` interface, captured simultaneously, shows **zero packets ever arriving** — not blocked, not dropped after arrival, never received at all. Yet `tailscale ping` between the two nodes directly succeeds cleanly (86ms, direct connection, no relay) — the underlying peer-to-peer tunnel itself is healthy. Restarting Toronto's `tailscaled` and re-establishing the exit-node selection did not change the result.

**This is a real, precise paradox worth stating plainly: the tunnel works for direct peer communication, but not for the specific job of routing third-party traffic through that peer.** That distinction — point-to-point health vs. exit-node routing function — is the exact, narrow question next session should start with, not a re-run of today's broader checks.

**Confirmed a third, independent way, same day: traceroute (both UDP and ICMP variants) shows total silence at every hop, including hop 1 — not even London's own local gateway responds.** This matches packet capture and direct ping exactly, and narrows the failure point further: whatever's wrong happens extremely early, likely at or immediately around London itself, not somewhere further out in the path to the real internet. Three independent diagnostic techniques now agree precisely — this is a solid, confirmed finding, not something that needs a fourth method to verify further.

**Concrete next steps, in order of promise:** (1) capture on London's `eth0` simultaneously with `tailscale0` during a live Toronto ping, to see whether packets ever cross from the tunnel interface to the physical one, narrowing the gap further than today's tests did; (2) search specifically for known Tailscale exit-node issues with DigitalOcean's networking stack, now that the symptom is precise enough to search for accurately; (3) consider testing exit-node routing between two droplets on the *same* provider region, removing cross-datacenter networking as a variable entirely.

**What's confirmed solid and needs no further rework:** all four nodes (Mac, Toronto, London, NY) are correctly configured — registered, forwarding enabled, routes approved. Today's session ruled out eleven distinct possible causes with direct evidence each time, not assumption.

## SOLVED, same day — the declared-origin proof is real, tested, and confirmed

**The root cause: the ACL policy written two nights ago for context isolation never granted any group permission to reach the internet through an exit node.** Every check run today on NAT, forwarding, firewalls, and routing tables was correctly ruled out — none of it was ever the problem. Headscale's policy engine was simply never told this traffic was allowed at all, and quietly dropped it every time, which is exactly why packets left the consuming node's tunnel interface but never arrived anywhere.

**The fix:** one new rule added to `acl.hujson`, granting `group:personal` access to `autogroup:internet:*` — Headscale's documented mechanism for this exact permission. Backed up the original file first, validated the new one with `headscale configtest` before restarting anything, restarted Headscale, then reconnected Toronto to London as its exit node.

**The result, confirmed live:** `curl -4 https://icanhazip.com` from Toronto, routed through London, returned `144.126.200.88` — London's address, not Toronto's own. Real ping traffic to `1.1.1.1` succeeded with zero packet loss. This is the actual, complete proof the declared-origin concept works — not simulated, not partial, run and confirmed on real infrastructure.

**Worth remembering for every future context (`employment`, `pseudonymous`) that needs this same capability:** each one needs its own equivalent `autogroup:internet:*` rule added explicitly — this fix only covered `personal`, on purpose, matching what was actually being tested.

**What was tried today, in order, none of which fully resolved it:** quitting and reopening the Tailscale app (no change — traffic only flows once the exit node is disconnected entirely); a full system restart was recommended as the next step, matching the fix that worked in the GitHub report for another user, but the symptom then shifted to the connection dropping immediately rather than staying up without passing traffic — worth treating as a related but distinct data point, not assumed to be the same failure.

**For next session:** this now has a real, upstream-tracked identity, not a mystery — worth adding a comment to `tailscale/tailscale#3299` with these specifics (macOS, exact error, symptom of connect-then-immediately-disconnect after extended use) rather than continuing to hand-diagnose it locally. If a truly fresh session (new day, fully rested Mac, first attempt of the day rather than the umpteenth) still reproduces it, that's meaningfully stronger signal for an upstream bug report than anything gathered today. All server-side infrastructure is done and correct — this is now purely a client-side investigation.

## Part 2 — Decisions Already Made — Don't Re-litigate

- The public site stays pure research. Book 01 and the consumer-facing pieces stay separate, sent directly to specific people.
- Mobile can't be fully zero-touch with current tooling — confirmed, Tailscale's mobile apps have no way to accept a pre-auth key.
- Desktop/Mac *can* be genuinely zero-touch today, via a wrapped `--authkey` script — designed, not yet built.
- No portal device, no proximity requirement — phones just need ordinary internet access to reach the server.
- **This is a controlled package, not an open internet standard.** Atlas decides which relying parties participate, indefinitely — not a stepping stone toward eventually opening to anyone. Public-key verification (over a shared secret) is still the right technical approach even inside this closed model — that's an engineering choice, separate from who's allowed to be a relying party at all.
- **Presence gets shared. Data doesn't.** A relying party attests that a Presence is valid; another relying party trusts that attestation. The underlying credential — the actual passkey — never crosses between them, the same way a government checking your bank's "yes, this is a real person" never sees your account details.

- **ACL isolation is default-isolated, user-controlled — not absolute.** Contexts (personal / employment / pseudonymous) don't reach each other over the mesh by default. This exists to prevent *involuntary* crossing — inference by a third party, leakage through shared infrastructure, an employer or relying party gaining visibility into another Presence without consent. It is not meant to lock the identity owner out of their own resources: the person controls when and how their own contexts bridge, since they're the same underlying identity choosing to present differently, not adversaries to one another. Any future isolation test should validate "nothing crosses without deliberate user action," not "nothing can ever cross."

## Part 3 — Presence: What's Actually Offered, By Evidence Tier

*Updated tonight. This section moves items between tiers only when something is actually tested — never because it would be convenient to believe it's ready.*

### Tier 1 — Tested and proven

- **An identity that survives switching networks.** Proven (H6).
- **Clean device recovery** without disturbing other devices. Proven (H5) — and as of August 4, proven on real hardware (a live iPhone) through the full expire-and-reauthenticate cycle, not just a test node.
- **Enforced separation between different people's Presences.** Proven — found broken first, then fixed, then re-verified.
- **A real relying party recognizing a person instead of a network.** *New as of tonight.* A working demo bank page, using a real passkey tied to a Presence, correctly ignored a simulated "new network" block that stopped the old-fashioned login path cold. Server-tested and confirmed by an actual passkey ceremony on a real device — not simulated.
- **A second relying party recognizing the same Presence without a new passkey.** This directly answers last night's open question — a bare, site-locked passkey cannot do this by design; Atlas can, and it's now proven, not just argued.
- **A visible signal for whether a site supports Presence**, confirmed switching correctly between an active demo site and unrelated real sites.

### Tier 2 — Built, working, not yet proven at real scale

- **A live, token-gated admin dashboard** for running these tests on demand, with full audit logging (JSONL) of every run.

- Separate contexts for different parts of a life, existing as real namespaces.
- The mesh network itself, self-hosted, under your own control.

### Tier 3 — Designed, not yet built

- **The real open question now: trust between relying parties doesn't scale yet.** Tonight's bank-to-airline token trust works because both services share one secret I configured myself. That's fine for a two-site demo, not for a real third party who's never talked to us. The next honest thing to test: what would it take for an *independent* relying party — one we don't control — to trust an Atlas Presence without us hand-configuring a shared secret with them directly?
- Hiding the underlying Tailscale/Headscale machinery inside a real branded app — technically achievable, real ongoing engineering work.
- Onboarding without manual admin approval (OIDC) — fully scoped in the runbook, not yet executed.

## Part 3.5 — New Scoped Item: Atlas Client Agent

**The gap:** Atlas currently has an admin-facing surface (the dashboard) but no end-user-facing surface. The person actually living inside a Presence today has to use the stock Tailscale app, whose settings (like allowing local network access while an exit node is active) are buried, non-obvious, and meaningless to someone who isn't a network engineer. Someone using Atlas day-to-day can't currently even see what's "on" for them, let alone control it in a way that matches how Atlas thinks about identity and context.

**The real fix, not a workaround:** a native Atlas client agent — not the stock Tailscale/Headscale client — that surfaces Presence identity, current context, and rule state (including things like bridge profiles, once built) in a UI a non-technical person can actually understand and control. This is the natural client-side counterpart to the admin dashboard, and closes the loop on "presence, not just a VPN" as a real, lived experience rather than an admin-only concept.

**Scope note:** this is a real, substantial build — not a quick toggle. It means writing and maintaining client software (likely wrapping or replacing the Tailscale client relationship entirely over time), not just a policy file. Deliberately logged here as a future roadmap item, not something to start today.

**Core principles, worked out August 4 — worth preserving exactly:**

- **Presence is singular, not per-device.** It's the same Presence whether you're on a MacBook, iPhone, iPad, or anything else in the toolbox — the device is just the current vessel, not a separate identity.
- **A client agent's job on any device is twofold:** (1) establish the VPN/mesh connection itself, and (2) apply the rules that represent *you* in that moment — current context, path/exit-node selection, active bridge profiles. The agent doesn't hold its own separate copy of truth; it represents the one real Presence.
- **The admin portal is the sole source of authority** — direct read/write access to everything (contexts, rules, bridge profiles). No ambiguity about where truth lives.
- **Client agents are viewers first, with control layered on top** — they let a person see what's actually configured for them right now. Critically, this should be reviewable **offline** — a person can check their own Presence status without requiring a live connection — then reconcile/sync once connectivity returns, rather than treating connectivity as a precondition for visibility.
- **Mobile-first, not desktop-first.** Many real people only have a phone or tablet, never a computer. Full Presence visibility and control cannot require a computer — that would make Atlas a tool for engineers only, contradicting the actual point of a *personal* internet presence for *people*, not just technical users.
- **Sequencing note:** the backend/VPN groundwork (mesh, ACLs, access lock, H5/H6, exit-node routing) was correctly built first — you need real, provable infrastructure before designing a client experience around it. But the client-agent/Presence-visibility layer is not a "nice to have" bolted onto that — it's arguably closer to the actual thesis of Personal Internet Presence than the admin tooling is. The engine came first; the client agent is the dashboard for the actual driver, not the mechanic. Both are required; this layer has been under-prioritized relative to its real importance and should move up in planning going forward.

---

## Part 3.6 — Flagged for Future Ethics/Legal Review: Remote Access to Company-Owned Devices

**Not scoped, not approved, not to be built without review.** During design discussion on August 4, a scenario came up: a company-issued laptop remains physically at the employee's home (its true, accurate location), while the employee travels with a personal device and wants to remotely access or route through that home-based company laptop. This was distinguished clearly from a rejected scenario — using Atlas to override or mask a company device's *actual* location from the company — which was explicitly ruled out as something Atlas should not build a feature around, given real legal and policy concerns (tax residency, data residency, export controls, employment/acceptable-use agreements, and the likelihood that concealment itself would violate employer policy).

The home-based-remote-access variant appears categorically different — the device's real location is never misrepresented, only accessed remotely — but the line between "legitimate remote access" and "tooling that could enable location concealment" deserves real scrutiny before anything here becomes a supported Atlas capability or product offering (including any adjacent idea like a sellable remote-KVM product). This should go through a proper ethical and legal review — not a solo engineering decision — before any related feature is scoped, designed, or built.

**Also flagged the same day, same category (needs real legal review before action, not a technical decision):** open-sourcing parts of Atlas so others can extend it. Mike wants the option to open this up, while retaining rights and explicitly not being responsible for what others build with it outside Atlas's own intentions — needs an actual license choice and liability review, not a default GitHub license picked casually.

---

## Part 3.8 - Basic Presence Backend: First Real Provisioning Pipeline (August 4)

**This is the first genuinely working, non-fake backend behind the Presence questionnaire.** Built and verified end to end via curl against the live dashboard API:

- New SQLite database (db.py) - users table (email, hashed password, per-user token, linked Headscale username) and personas table (the five questionnaire answers, matched exit node, timestamp)
- New presence_provision.py - creates a real Headscale user per signup, safely adds them to the group:personal ACL group (validate with headscale configtest before writing, same pattern as the manual Toronto-London fix), restarts Headscale, and matches their stated home location to the nearest existing exit node
- New routes on the dashboard API: POST /api/presence/signup, POST /api/presence/login, POST /api/presence/provision, GET /api/presence/status - all separated from the admin token middleware, since these need per-user auth (X-Presence-Token header), not the admin ATLAS_TOKEN
- Verified live: a real signup created a real Headscale user (presence-user-1), correctly added to group:personal in acl.hujson, Headscale restarted cleanly, exit node correctly matched to Toronto based on the Q3 answer, and the full persona was readable back via the status endpoint

**Deliberate simplification, per decision made the same day:** Q4 ("how do you want to be presented") is cosmetic for now - every real signup is provisioned into group:personal regardless of which Q4 answer they pick. The "employment" group is being treated as a reserved placeholder, not a real capability, until there is a real reason (like a company formally adopting Atlas) to build it out properly.

**Exit node matching is a simple keyword placeholder, not real geo-routing.** Only Toronto and London exist as real exit nodes today; everything that does not match a known keyword defaults to Toronto. This is a known, accepted limitation - not a bug - until more regional exit nodes exist.

**Known real gap, not yet solved:** the backend can now correctly grant permission for a user to route through their matched exit node, but nothing yet tells their actual device to select and use that exit node. That selection is currently a manual, client-side action (the stock Tailscale app). Closing this gap fully depends on the future Atlas client agent (see Part 3.6 client agent principles) - this is expected, not an oversight.

**Not yet wired to the frontend.** The presence.html questionnaire prototype still uses fake local JavaScript state for its summary and Lens screens. The next real step is connecting its "Build my Presence" action to POST /api/presence/provision, and its Lens screen to GET /api/presence/status, so the whole flow becomes real rather than a demo.

---

## Part 4 — Suggested Order, Next Time

0. **Deploy and live-test both builds** (`./deploy-enrollment.sh`, then: enroll one real Mac, enroll one real phone by paste, and switch declared origin Toronto↔London on a live device and confirm the egress IP actually changes). Everything below is more valuable once this is proven on hardware rather than against a stub.
1. **Add `autogroup:internet:*` for `employment` and `pseudonymous`.** Only `personal` got it in the Aug 3 fix. Those contexts will silently drop traffic exactly the way Toronto→London did — a known landmine, cheap to defuse.
2. **Solve independent relying-party trust** — how a real, outside service could trust an Atlas Presence without a hand-configured shared secret. This is now the single most important open question in the whole project.
3. **Make contexts real** — Q4 is still cosmetic; every signup lands in `group:personal` regardless of answer. Per-signup ACL group generation is the multi-tenancy gap.
4. OIDC provider decisions — cheap to decide, unlocks admin-free onboarding.
5. ~~The desktop zero-touch script~~ — **done, Aug 5.** `build_enrollment_instructions()` emits the wrapped `--authkey` one-liner Part 2 designed but never built. Still needs a real-hardware run.
6. ~~Route Path Selection~~ — **done, Aug 5.** See Part 0.2. Still needs a real-hardware run.
7. Password hashing upgrade in `db.py` (see Part 0.1) — before any real person signs up.
8. **Compliance verification** — the client tail issues `--exit-node=` and records intent, but nothing confirms traffic actually left that way. Wiring the existing exit-node test panel to a client-initiated check would close the loop between declared and actual.
9. Outreach — you now have three rounds of real, tested proof, not just documents.

**Vision note, Aug 5 — worth keeping in these words.** The sharpest one-line statement of the thesis so far: *a cell phone keeps one identity everywhere it roams, but on the internet the local ISP decides who you are.* A SIM travels; a DHCP lease doesn't. Your residency and your personal footprint shouldn't change because you went on vacation. That framing — Atlas as the SIM for the internet layer, supporting the remote user's ability to control and protect themselves — is now written into the client UI copy directly, and reads better than any of the earlier "person-controlled presence layer" phrasings.

## Part 3.7 - Tracked, Not Yet Done: Shared Brand Source

The problem: logo and font drift has happened more than once - the dashboard and early prototypes used a plain concentric-circles SVG mark with a navy/brass palette, while the real live public site (mtsalisbury.github.io/ProjectAtlas) uses a different, canonical treatment: indigo-violet rounded badge with white double-ring icon, light background (#fafafc), deep navy ink, Space Grotesk headers, indigo-violet accent (#5659dd).

Confirmed canonical, August 4 (verified against a live screenshot of the real site): the concentric-circles mark IS correct - it just needs the accent color fixed to indigo-violet, not brass. The Avenix logo is not actually live anywhere and should be treated as retired.

Not yet done: pull the logo SVG, font imports, and color tokens into one shared file (e.g. brand.css or similar) that every surface - public site, admin dashboard, the Presence questionnaire/Lens flow, and any future surface - references or copies from, so this drift cannot happen again. Tracked here so it is not lost; not blocking other work.

