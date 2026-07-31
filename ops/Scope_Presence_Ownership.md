# Scope: Presence Ownership — Recovery, Portability, and What Atlas Can See

**Status:** Scoping only, for next session | **This one is foundational — worth doing alongside or before Phase 1 of the identity service, not after**

## What's already true, structurally

The private key behind a passkey never leaves the user's device — generated in secure hardware, never seen by Atlas, never seen by any relying party. That's not a policy Atlas follows; it's a cryptographic fact true regardless of intent. Combined with last night's per-destination, opt-in design, Atlas already can't act on someone's traffic without an explicit rule they set. That's real ownership of *access*. It is not yet ownership of *recovery* or *visibility* — those are the two real gaps below.

## Gap 1: Recovery currently depends on Apple or Google

Today, losing a device and getting a passkey back relies on iCloud Keychain or Google Password Manager — real, secure systems, but ones Atlas doesn't control. "Ours" is compromised if recovering it always routes through someone else's infrastructure.

**Decided: a recovery portal, checking a self-held recovery secret — not a second device, not Apple, not Google, not Atlas itself.** At registration, the identity service generates a recovery phrase, shown exactly once, that the person must store themselves. Losing a device means going to the portal and providing that phrase — nothing else is checked, and nobody but the person holds a copy. This is the same model serious crypto wallets use, and it's the only one of the real options that depends on no company at all, Atlas included.

**The honest cost, stated plainly, not hidden:** if someone loses the phrase too, there is no safety net. Neither Atlas nor anyone else can recover it for them. That's not an oversight to fix later — it's the actual price of the phrase being genuinely theirs rather than something a company could hand back on request. A recoverable-by-Atlas safety net would mean Atlas has power over recovery, which defeats the point.

**What this needs, concretely:** the portal itself (a real page, separate from any single relying party), the one-time phrase generation and display flow, and the "authorize a new device using the phrase" logic in the identity service. Real, scoped work — not yet built, not yet tested.

## Gap 2: What Atlas itself can see

An identity service that logs every authentication — which relying party, when, how often — becomes a place where someone's whole pattern of activity is visible to Atlas, even if no individual relying party can see it. That undermines "ours" from a different direction than Gap 1: not "can someone else's cloud lock me out," but "can Atlas itself watch too much."

**Two honest paths, different amounts of work:**

- **Simpler, available now:** log as little as possible by default, keep retention short, and publish exactly what is and isn't recorded — transparency as the near-term answer, not a technical guarantee.
- **Stronger, real, but harder:** techniques exist (blind signatures, privacy-preserving credential schemes) that let Atlas sign a valid Presence token *without knowing which relying party it will be used at* — meaning Atlas structurally can't build the activity pattern even if it wanted to. This is real, established cryptography, not speculative — but it's meaningfully more engineering than anything scoped so far. Worth naming honestly as the stronger answer, not worth committing to building yet.

## Decisions needed

1. **Is multi-device peer-authorization the primary recovery path, or a secondary option alongside platform keychain sync?** Affects how much of Gap 1 gets solved versus mitigated.
2. **For Gap 2, start with the simple transparency answer, or invest in the stronger cryptographic one from the start?** The simple answer ships faster; the strong one is a real structural guarantee instead of a promise.

## Where this sits relative to the other two scoping documents

This isn't downstream of `Scope_Unify_Presence.md` — it shapes how that identity service should be built in the first place. Worth reading this one *before* Phase 1 begins, not after, so recovery and logging decisions aren't retrofitted onto something already built. `Scope_Declared_Origin.md` stays fully independent of this — that capability doesn't change based on how recovery or logging get solved here.
