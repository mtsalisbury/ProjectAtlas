# Scope: Presence Ownership — Recovery, Portability, and What Atlas Can See

**Status:** Scoping only, for next session | **This one is foundational — worth doing alongside or before Phase 1 of the identity service, not after**

## What's already true, structurally

The private key behind a passkey never leaves the user's device — generated in secure hardware, never seen by Atlas, never seen by any relying party. That's not a policy Atlas follows; it's a cryptographic fact true regardless of intent. Combined with last night's per-destination, opt-in design, Atlas already can't act on someone's traffic without an explicit rule they set. That's real ownership of *access*. It is not yet ownership of *recovery* or *visibility* — those are the two real gaps below.

## Gap 1: Recovery currently depends on Apple or Google

Today, losing a device and getting a passkey back relies on iCloud Keychain or Google Password Manager — real, secure systems, but ones Atlas doesn't control. "Ours" is compromised if recovering it always routes through someone else's infrastructure.

**The fix already has a head start, from work already tested.** The device-recovery test from night one — revoke one device, confirm the other keeps working undisturbed — is half of the real answer. The missing half: **let an already-enrolled device vouch for a new one**, so recovery doesn't need platform keychain sync at all. Someone with two enrolled devices loses one, uses the second to authorize a replacement, done — no dependency on Apple or Google in that path. Keychain sync becomes a convenience some people use, not the only way back in.

**What this needs, concretely:** a real "authorize a new device from an existing one" flow in the identity service — not yet built, not yet tested, genuinely new work, but it extends something already proven rather than inventing from nothing.

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
