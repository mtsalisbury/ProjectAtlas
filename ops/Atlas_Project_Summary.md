# Project Atlas — Summary

## The core idea

The internet recognizes accounts, devices, and IP addresses. It doesn't recognize *people*. Project Atlas is research into whether there should be a native concept of a **Personal Internet Presence** — a portable, person-controlled identity that travels with you, independent of any single network, application, or company.

The founding example: a traveler lands somewhere unfamiliar, tries to check their bank account, and gets blocked or challenged — not because anything is actually wrong, just because the network looks unfamiliar. Atlas asks whether that's a solvable problem at the identity layer, not just something to route around.

## What's actually been built and proven — not theory, tested

**A real, self-hosted mesh network** (Headscale, on your own infrastructure) with three isolated identity contexts — `personal`, `employment`, `pseudonymous` — each cryptographically separated from the others.

**Two research hypotheses tested and confirmed:**
- **H6 (persistence across networks):** a device kept its identity switching from home Wi-Fi to a mobile hotspot, verified server-side.
- **H5 (device recovery):** revoking one lost device doesn't disturb any other device tied to the same Presence.

**A real security gap found, then fixed:** cross-context isolation initially *failed* by default — two different people's devices could see each other. An explicit access policy was built, tested, and confirmed to close that gap.

**A working passkey-based demo** ("Atlas Demo Bank") proving the actual traveler-story claim: a real device passkey, recognized by a relying party, with no IP or location check — beating a simulated "unrecognized network" block that a conventional login would have failed.

**Cross-relying-party trust proven** — a second demo service ("Atlas Demo Airline") recognized the same Presence using a signed token, with no separate passkey enrollment. This is the one thing a bare, site-locked passkey cannot do on its own — the actual evidence that a Presence adds something beyond ordinary passkey login.

**A real browser extension**, correctly detecting which sites support Presence and switching itself on and off accordingly — tested live against both a supporting site and unrelated real websites.

**The public research site rebuilt clean** — every page verified against real content, one consistent design system, old broken files retired, secrets kept out of the public repo.

## The declared-origin proof — the hardest, most contested result

After two full days of methodical debugging — real infrastructure lockouts, a known upstream Tailscale bug ruled out, eleven separate technical causes checked and eliminated one by one — the actual root cause turned out to be a single missing line in an access policy written days earlier for a different purpose.

Once fixed: **a device's traffic was confirmed, three independent ways, to egress from a different location than its real one** — and then tested against a real bank's live fraud-detection system. TD explicitly identified the login as coming from London and asked for human approval — a real, working demonstration of the exact scenario the whole project started with.

## What this proved, and what it didn't

It proved the mechanism works, end to end, against real infrastructure most people would call production-grade. It also surfaced an honest, important finding: banks like TD already have decent fraud detection of their own. The real value of Atlas isn't "beat one bank's security team" — it's giving a person **one Presence they hold and control**, usable the same way across many services, instead of every service running its own separate, disconnected trust-guessing game. "Presence shared, data never" — not a slogan, a tested architectural choice.

## Key decisions locked in, not to be re-litigated

- This is a controlled package, not an attempt to become an open internet standard.
- Recovery of a lost Presence depends on a self-held phrase, protected by a second factor — no company, including Atlas itself, can hand it back if lost. That's the actual price of it being genuinely *yours*.
- Destination-level content filtering (blocking dangerous sites, catching fraud) is explicitly out of scope — that's the ISP's job, not an identity platform's.
- Token signing uses ES256; visibility into which relying party a token is used at stays intentionally limited.

## What's still genuinely open

- A real identity service (separating Presence issuance from any single demo site) — scoped in detail, not yet built.
- Route-path selection as its own clean, user-facing capability — today it's manual CLI flags; a real product would need a portal or simple client control.
- Atlas Paper 003, Article 002, and the broader research track — untouched for several sessions in favor of infrastructure work.
- Outreach — real proof now exists that didn't exist before; the people originally identified to show this to still haven't seen it.

## The honest bottom line

Two intense days turned a concept into working, tested infrastructure — including a result that held up against a real bank's real security system. What's unproven isn't the mechanism anymore. It's whether anyone besides the person who built it wants it, and that question hasn't been asked yet.
