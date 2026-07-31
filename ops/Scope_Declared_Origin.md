# Scope: Declared-Origin Routing — A Capability of the Presence Entity, Not a Separate System

**Status:** Scoping only, for next session | **One Presence entity, growing more capable — not two systems sitting side by side**

## What a relying party actually sees today, and why that matters here

A bank's fraud check mostly relies on two things: IP address (revealing rough location and whether it's a known VPN/datacenter range) and device fingerprint (recognizing a returning device). The native Geolocation API — precise, GPS-based — is separate and opt-in per site; most banks don't use it at all, since asking for that permission on a login screen feels invasive.

This matters for scope: **this capability must never sit between a device and the internet as a blanket intercept.** Normal traffic — Geolocation API calls, IP-based signals, everything — stays completely untouched, for every app and every site, by default. The declared-origin capability only activates where a user has explicitly set a rule for one specific relying party — not a system-wide override. Reveals normally everywhere by default; hides only where explicitly, narrowly configured. This is the opposite default from a VPN, which hides everything unless turned off.

## What this is

There is one Presence entity per person. Today it can prove *who* you are, via the passkey work already tested. This scope adds a second thing that same entity can optionally carry: a verified, declared *home* location — the way a phone number stays tied to home no matter where the phone physically is. Not a separate feature bolted alongside Presence. A second capability of the one entity, added on top of the first.

## Say the honest part first, plainly

The underlying mechanism — routing traffic through a fixed exit point tied to a location — **is the same mechanism a VPN uses.** There's no version of this that's technically different depending on who built it, and trying to make it *seem* different without actually being different would be the kind of dishonesty this project has avoided everywhere else. Worth remembering that plainly before building anything.

## What actually makes this different from a VPN, for real

A VPN is anonymous by design — that's its entire point, and exactly why banks blocklist known VPN ranges. The exit IP could belong to anyone; there's no way to tell a legitimate traveler from someone with something to hide.

**A Presence is not anonymous.** The passkey work from tonight already proves *who* is asking, cryptographically, before location ever enters the conversation. So the real feature isn't "hide your location" — it's **"declare a location, attached to an identity a relying party can independently verify is real and accountable."** Verified routing, not anonymous routing. That's a genuinely different trust category, even though the pipe underneath looks similar to a VPN's.

## The honest risk, not solved tonight

Even with identity attached, the traffic still physically exits from some IP range. If that range gets recognized and blocklisted the same way VPN ranges already are, this doesn't help — *unless* the relying party is actually checking the verification claim, not just the IP address the way they do today. This only works if relying parties adopt checking the Presence claim instead of (or alongside) the IP. That's a real, unresolved dependency, not a detail.

## Where this actually connects to yesterday's scoping — a simplification, not a new system

This doesn't need its own separate architecture. Once the identity service from `Scope_Unify_Presence.md` exists — issuing signed tokens for a Presence — a declared home location is just **one more attested claim in that same token**, not a new mechanism. Build the identity service first; this rides on top of it rather than duplicating it.

## Decisions needed before scoping goes further

1. **Real infrastructure cost.** Offering "your traffic looks like it's from home" requires an actual exit point in that location — a real server, in a real place. Cost scales with how many locations are offered, unlike the core Presence work, which needed none of this.
2. **Who verifies the declared-location claim, and how strictly?** Does a relying party need to trust Atlas's attestation the same way they'd trust the passkey Presence claim, or does this need something stronger given how easy location claims are to fake without real infrastructure behind them?
3. **Confirmed, not re-litigated: this stays an optional capability, not a required one.** A Presence should work fully — proving identity, nothing more — without this ever being turned on. Adding it later shouldn't be a redesign; it should look like the entity simply gained a new claim it can carry, the same way a person can add a passport without becoming a different person.

## Suggested order

Do not start this before Phase 1 of `Scope_Unify_Presence.md` (the identity service itself) exists — this depends on it directly rather than standing alone. Once that's real, this becomes a scoping conversation about one additional token claim and real exit-node infrastructure, not a fresh architecture.
