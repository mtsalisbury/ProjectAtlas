# Project Atlas — Status

**This is the one file to update.** Everything about where the project stands lives here now — not spread across separate documents. If something changes, it changes here, in the relevant section below, nowhere else.

**Last updated:** July 30, 2026

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

## Part 2 — Decisions Already Made — Don't Re-litigate

- The public site stays pure research. Book 01 and the consumer-facing pieces stay separate, sent directly to specific people.
- Mobile can't be fully zero-touch with current tooling — confirmed, Tailscale's mobile apps have no way to accept a pre-auth key.
- Desktop/Mac *can* be genuinely zero-touch today, via a wrapped `--authkey` script — designed, not yet built.
- No portal device, no proximity requirement — phones just need ordinary internet access to reach the server.
- **This is a controlled package, not an open internet standard.** Atlas decides which relying parties participate, indefinitely — not a stepping stone toward eventually opening to anyone. Public-key verification (over a shared secret) is still the right technical approach even inside this closed model — that's an engineering choice, separate from who's allowed to be a relying party at all.

## Part 3 — Presence: What's Actually Offered, By Evidence Tier

*Updated tonight. This section moves items between tiers only when something is actually tested — never because it would be convenient to believe it's ready.*

### Tier 1 — Tested and proven

- **An identity that survives switching networks.** Proven (H6).
- **Clean device recovery** without disturbing other devices. Proven (H5).
- **Enforced separation between different people's Presences.** Proven — found broken first, then fixed, then re-verified.
- **A real relying party recognizing a person instead of a network.** *New as of tonight.* A working demo bank page, using a real passkey tied to a Presence, correctly ignored a simulated "new network" block that stopped the old-fashioned login path cold. Server-tested and confirmed by an actual passkey ceremony on a real device — not simulated.
- **A second relying party recognizing the same Presence without a new passkey.** This directly answers last night's open question — a bare, site-locked passkey cannot do this by design; Atlas can, and it's now proven, not just argued.
- **A visible signal for whether a site supports Presence**, confirmed switching correctly between an active demo site and unrelated real sites.

### Tier 2 — Built, working, not yet proven at real scale

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
