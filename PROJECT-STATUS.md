# Project Atlas — Status Overview

**Last updated:** July 29–30, 2026 | **Purpose:** One place to see what's built, what's verified, what's decided, and what's genuinely still open — so nothing gets lost or has to be reconstructed from memory.

## What's Actually Built and Working

**Infrastructure (real, live, tested):**
- A self-hosted Headscale mesh server, deployed on DigitalOcean, running behind Caddy with automatic TLS at `mesh.rpnwireless.com`.
- Three isolated user contexts created (`personal`, `employment`, `pseudonymous`), composing existing standards per Paper 002's own design principle rather than custom infrastructure.
- An ACL policy enforcing that contexts cannot reach each other by default — built, tested, and confirmed working.

**Research results, independently verified and published:**
- **H6 (persistence across transport changes):** confirmed. A device kept its identity and connection switching from home Wi-Fi to a mobile hotspot, verified by server-side timestamps, not just client display.
- **H5 (device recovery):** confirmed, with a genuinely useful finding — server-side revocation is immediate, but a revoked device's *own* status display can lag behind that reality. Documented as a real caution for anyone relying on client self-reports.
- **Cross-context isolation:** tested honestly — the mesh **failed** this by default (two different simulated users could reach each other's devices). An explicit ACL policy fixed it, and the fix was re-tested and confirmed. This is real evidence bearing on Hypothesis H2.
- Both results are written up and live in **Atlas Paper 002**, Sections 21 and 22.

**The public site (`mtsalisbury.github.io/ProjectAtlas`):**
- Fully rebuilt from scratch after the original had duplicated files, two competing stylesheets, and several genuinely broken pages.
- Every file verified against real content — nothing guessed, nothing carried forward from the broken version without checking it first.
- Standardized on one stylesheet (`style.css`); the older, stale one (`atlas.css`) retired.
- Old files removed from the repo, `.gitignore` in place to stop `.DS_Store` clutter and prevent secrets from ever being committed.

**Operational documentation (in `ops/`, committed and pushed):**
- `KB-Device-Onboarding-Flow.md` — the real device-join flow, step by step, with what success and failure look like at each stage.
- `Runbook-OIDC-Setup.md` — planning document for eliminating manual key registration, not yet executed.

## Decisions Already Made — Don't Re-litigate These

- **The public site stays pure research.** Book 01, Architecture Foundation, Build Roadmap, and the consumer-facing pieces (Traveler Story, What Atlas Is) stay separate from the GitHub Pages site — sent directly to specific people, not published where a stranger could stumble on the mismatch in tone.
- **Mobile can't be fully zero-touch with current tooling.** Confirmed via Tailscale's own open GitHub issue — mobile apps have no way to accept a pre-auth key, only the browser login flow. OIDC can remove the *admin's* manual step, but not the user's one login screen.
- **Desktop/Mac *can* be genuinely zero-touch today**, using `tailscale up --authkey` wrapped in a double-clickable script. This is real and buildable now, unlike the mobile path.

## What's Genuinely Still Open

**Naming:** Praesa, Continuo, and Iniba all came back clean on a lightweight search-based check. None taken to an actual registrar or USPTO search yet. Not decided.

**Research track:**
- Atlas Paper 003 ("Trust in a Person-Centric Internet") — still listed as "Planned," not started.
- Article 002 (Traveler Story, adapted into the site's research voice) — not written.
- The packet-level/metadata diagrams Section 15 calls for — not produced.
- Testing H1/H4 with real devices in `employment`/`pseudonymous` contexts (beyond the synthetic cross-user test) — not done.

**Product/onboarding:**
- OIDC setup — planned in detail, not executed. Needs three decisions first (which identity provider, who's allowed to register, how context gets assigned) before any technical step starts.
- The desktop zero-touch script (`.command`/`.bat` wrapping a pre-auth key) — designed in conversation, not yet built or tested.
- The two-part welcome email — drafted as copy, not wired to anything real (nothing currently triggers it automatically).

**Strategic:**
- Outreach to the 3–5 trusted people originally discussed — never actually sent, despite now having real proof (not just documents) to back it up.
- Desktop-first vs. mobile-first priority — flagged as worth deciding explicitly, not yet decided.

## Suggested Order, Next Time

1. Decide the OIDC provider questions — cheap to decide, unlocks everything else in that runbook.
2. Build and test the desktop zero-touch script — real, achievable quickly, and would give something concrete to show alongside the research results.
3. Send the outreach — you now have working infrastructure and two honest research results to back it up, which is a materially stronger position than documents alone.
4. Everything else on the research track (Paper 003, Article 002, remaining diagrams) can follow at whatever pace makes sense — none of it is blocking the other tracks.
