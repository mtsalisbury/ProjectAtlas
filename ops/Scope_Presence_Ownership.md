# Scope: Presence Ownership — Recovery, Portability, and What Atlas Can See

**Status:** Scoping only, for next session | **This one is foundational — worth doing alongside or before Phase 1 of the identity service, not after**

## What's already true, structurally

The private key behind a passkey never leaves the user's device — generated in secure hardware, never seen by Atlas, never seen by any relying party. That's not a policy Atlas follows; it's a cryptographic fact true regardless of intent. Combined with last night's per-destination, opt-in design, Atlas already can't act on someone's traffic without an explicit rule they set. That's real ownership of *access*. It is not yet ownership of *recovery* or *visibility* — those are the two real gaps below.

## Gap 1: Recovery currently depends on Apple or Google

Today, losing a device and getting a passkey back relies on iCloud Keychain or Google Password Manager — real, secure systems, but ones Atlas doesn't control. "Ours" is compromised if recovering it always routes through someone else's infrastructure.

**Decided: a recovery portal, checking a self-held recovery phrase — plus a second factor at the portal itself.** At registration, the identity service generates a recovery phrase, shown exactly once, that the person must store themselves. The portal is the single highest-value target in the whole system by design — it exists specifically for when the everyday passkey isn't available, so it can't lean on that same protection. A second factor (an authenticator app set up separately from the primary device, at registration) protects the portal itself: recovering a lost Presence requires both the phrase and that second factor, not the phrase alone.

**The honest cost, stated plainly, not hidden:** if someone loses the phrase too, there is no safety net. Neither Atlas nor anyone else can recover it for them. That's not an oversight to fix later — it's the actual price of the phrase being genuinely theirs rather than something a company could hand back on request. A recoverable-by-Atlas safety net would mean Atlas has power over recovery, which defeats the point.

**What this needs, concretely:** the portal itself (a real page, separate from any single relying party), the one-time phrase generation and display flow, a second-factor enrollment step at registration, and the "authorize a new device" logic in the identity service. Real, scoped work — not yet built, not yet tested.

## A principle worth naming explicitly: Presence gets shared. Data doesn't.

The way a government portal checks whether someone's alive by asking a bank a single yes-or-no question — never requesting the underlying personal data — is exactly the pattern the token architecture in `Scope_Unify_Presence.md` already implements. One relying party attests a Presence is valid; another trusts that attestation. The actual credential never crosses between them. This isn't a new feature to design — it's the principle the whole signed-token approach has been building toward, worth stating outright rather than leaving implicit.

## Gap 2: What Atlas itself can see

An identity service that logs every authentication in full detail — exact relying party, timestamp, frequency — becomes a place where someone's whole pattern of activity is visible to Atlas, even if no individual relying party can see it. That undermines "ours" from a different direction than Gap 1: not "can someone else's cloud lock me out," but "can Atlas itself watch too much."

**Decided, superseding the earlier blind-signature direction: Atlas sees the destination URL or IP, and classifies it into a small set of categories — bank, airline, home, and so on — nothing more granular than that.** No behavioral profiling, no fine-grained browsing history beyond the category itself. Alongside that: a real safety blocklist — known dark web destinations and known terrorist-affiliated infrastructure get blocked outright, not just logged.

**Worth being precise about the tradeoff, since this replaces a stronger privacy guarantee, not extends it:** true blind signatures — Atlas structurally unable to see the destination at all, even in category form — is incompatible with this. Seeing enough to categorize and block is real visibility, not "Atlas promises not to look." This is a deliberate, narrower privacy stance than the one decided a few minutes earlier the same night: category-level visibility, in exchange for a real safety backstop, instead of zero visibility with no backstop at all.

## Decisions needed

Both open questions below were resolved later the same night — recorded here for the history, not as open items. See the Gap 1 and Gap 2 sections above for the actual decisions.

1. ~~Is multi-device peer-authorization the primary recovery path, or a secondary option alongside platform keychain sync?~~ — Resolved: neither. A recovery portal checking a self-held phrase, protected by a second factor.
2. ~~For Gap 2, start with the simple transparency answer, or invest in the stronger cryptographic one from the start?~~ — Resolved, then revised the same night: not blind signatures after all. Category-level visibility (bank/airline/home) plus a real safety blocklist, in exchange for a genuine backstop instead of zero visibility.

## Where this sits relative to the other two scoping documents

This isn't downstream of `Scope_Unify_Presence.md` — it shapes how that identity service should be built in the first place. Worth reading this one *before* Phase 1 begins, not after, so recovery and logging decisions aren't retrofitted onto something already built. `Scope_Declared_Origin.md` stays fully independent of this — that capability doesn't change based on how recovery or logging get solved here.
