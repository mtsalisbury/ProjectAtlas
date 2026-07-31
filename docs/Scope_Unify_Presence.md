# Scope: Real Public-Key Trust for Presence (No Shared Secrets)

**Status:** Scoping only — nothing built yet | **Answers both open items in STATUS.md at once**

## The problem, stated precisely

Tonight's bank-to-airline trust works because I configured both services with the same secret myself. That's not real federation — it's two demos I control pretending to be independent. A genuine outside relying party, one we've never spoken to, has no way to get that secret, and shouldn't need to.

Separately: the mesh (Track A) gives every device a real cryptographic identity when it joins Headscale. The passkey demo (Track B) gives a browser session a *different* identity, unrelated to the first. "Presence" currently means two different things depending which system you're looking at.

## The finding worth stating plainly before scoping the fix

My first instinct — sign Presence tokens with the device's actual WireGuard key — doesn't work, and it's worth understanding why rather than glossing past it. That key exists to encrypt tunnel traffic between mesh devices. A bank's server was never part of the mesh and never will be; it has no path to that key, and shouldn't need one. Good that this got caught at the scoping stage instead of half-built.

## What actually solves this — a pattern that already exists, not something new

The real fix looks like **the same trust model behind "Sign in with Google," not a shared secret.** Concretely:

1. **A single Atlas identity service** — not each relying party running its own separate passkey system, as the bank demo does tonight. One service, one place, holds the mapping between a Presence and its passkey credential.
2. **That service signs tokens with its own real keypair** (asymmetric — public/private, not a shared HMAC secret like tonight's demo).
3. **It publishes its public key at a predictable, standard address** — the same pattern OIDC providers already use (a JWKS endpoint, a well-known JSON file listing current signing keys).
4. **Any relying party — the bank, the airline, or one we've never met — fetches that public key independently and verifies tokens themselves.** No handshake with us required in advance. No secret to distribute. This is the actual mechanism that makes "we've never spoken to this relying party" possible.

## Where Track A actually connects, honestly

Not by sharing the WireGuard key directly. The real connection: **the same context names — `personal`, `employment`, `pseudonymous` — become the source of truth in both places.** Right now Headscale defines them for mesh purposes, and the bank demo has its own separate, hardcoded copy. Unifying means one service owns "what Presences exist" and both the mesh and the relying-party flow read from it, instead of each maintaining its own private copy of the same idea.

## Decisions needed before building anything

1. **Where does this identity service live?** A new subdomain (`id.rpnwireless.com`, matching the pattern of `mesh.` and `admin.`), or folded into an existing container? Leaning toward new and separate — this is a distinct responsibility from either Headscale or the demo bank.
2. **What signs the tokens?** A standard, well-supported algorithm (RS256 or ES256), not something hand-rolled. This is a place to use a mature library, not custom cryptography.
3. **Registration stays closed, deliberately, for now.** Worth separating two things that sound similar but aren't: the *public key* is always meant to be publicly fetchable — that's not a loss of control, it's the same as anyone being able to see a website's TLS certificate without being able to pretend to be that website. What stays closed is *who's allowed to stand up as a relying party at all* — for now, that requires explicit registration and approval, the same as how "Sign in with Google" requires an app ID before a site can use it. Nothing about this architecture forces registration open; it can stay closed indefinitely, and should, until there's a real reason to widen it.
4. **How does key rotation work?** If the signing key ever needs to change, every relying party needs a way to notice — this is a real operational question, not an edge case to skip.

## Phased build, once decisions are made

**Phase 1 — Stand up the identity service itself.** Move the passkey registration/login logic out of the bank demo and into its own service. Same WebAuthn code, different home. Prove it still works exactly as tonight's demo did, just relocated.

**Phase 2 — Switch from shared secret to real signing.** Replace the HMAC token from tonight with a properly signed one, and publish the public key at a well-known address. Update the bank and airline demos to verify against that published key instead of a secret baked into their own config.

**Phase 3 — The actual test that proves this worked:** stand up a *third* demo relying party — registered and approved by you, same as the first two, but built without ever being told a secret in advance, only pointed at the public key endpoint — and confirm it can verify a real Presence token entirely on its own. That's the moment "no shared secret" stops being a claim and becomes a tested result. This deliberately does not test open, unapproved registration — that stays closed, per the decision above, until there's a real reason to revisit it.

## What this does not attempt to solve yet

This scope does not touch Track A's own open items (testing H1/H4 with real employment/pseudonymous devices) — those stay exactly as queued. This is specifically about making Presence one real, verifiable thing instead of two demos sharing a name.
