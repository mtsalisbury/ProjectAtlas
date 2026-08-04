# Project Atlas — Status

**This is the one file to update.** Everything about where the project stands lives here now — not spread across separate documents. If something changes, it changes here, in the relevant section below, nowhere else.

**Last updated:** July 30, 2026

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

## Part 4 — Suggested Order, Next Time

1. **Solve independent relying-party trust** — how a real, outside service could trust an Atlas Presence without a hand-configured shared secret. This is now the single most important open question in the whole project.
2. OIDC provider decisions — cheap to decide, unlocks admin-free onboarding.
3. The desktop zero-touch script — real, achievable quickly.
4. Outreach — you now have two rounds of real, tested proof, not just documents.
