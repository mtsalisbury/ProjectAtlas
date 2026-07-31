# Atlas Architecture — Full Component Map

**Purpose:** Every piece named in one place, honestly marked — built and tested, scoped but not built, or not yet designed at all. This is the synthesis of both nights, not a new plan.

---

## 1. User

The person. Not a technical component — the actual human this entire system exists to serve, and the only party who ever holds the recovery phrase.

## 2. Devices (Soft Features) — App or Engine

**Status: partially built, partially scoped.** Today, this is borrowed software — the real Tailscale client for the mesh, a browser for the passkey flow. Scoped, not built: a real Atlas-branded app that hides that underlying machinery entirely (named in the original build roadmap as real, ongoing engineering work, not a weekend task).

## 3. VPN Backend

**Status: built and tested.** This is Headscale — the actual mesh, the WireGuard tunnels, the three contexts, the ACL isolation policy. Proven across H5, H6, and the cross-context isolation test. This is the most mature piece of the whole system.

## 4. Identity

**Status: scoped in detail, not yet built.** The identity service from `Scope_Unify_Presence.md` — passkey registration and login, moved out of the demo bank into its own real service, signing tokens with ES256 instead of a shared secret, publishing its public key for any approved relying party to verify against independently.

## 5. Route Path Selection

**Status: not yet formally defined as its own component — worth naming precisely now.** This is the decision logic that, for any given destination, chooses *which* path traffic actually takes: through the mesh (Track A), through a declared-origin exit point (the optional capability from `Scope_Declared_Origin.md`), or straight out to the ordinary internet, untouched, which is and stays the default for everything not explicitly configured. This component doesn't exist yet even as a design — it's the connective logic between the VPN backend and the declared-origin layer, and it deserves its own scoping pass before being built.

## 6. Presence

**Status: defined, partially built.** The entity itself — one identity per person, capable of carrying more than one claim over time. Today it can carry a passkey-verified identity claim (built, tested). Scoped, not built: a declared-origin claim as a second, optional capability of the same entity, per last night's reframing.

## 7. API — Direct Answer to End Device / Server / Internet Utility

**Status: proven in miniature, not yet generalized.** This is the actual interface an outside relying party queries — "is this Presence valid," answered without handing over the underlying credential. The bank-to-airline token trust from two nights ago is a working, tested proof of this exact mechanism, at small scale, with a shared secret standing in for what should be public-key verification. The government-checking-a-bank example from tonight is the plain-language version of what this API's job is.

## 8. Functional Recovery

**Status: fully scoped tonight, not yet built.** The portal, the one-time recovery phrase, the second factor protecting the portal itself. The most fully-reasoned piece of tonight's work — every real tradeoff named, including the honest one: no safety net if the phrase is lost too.

## 9. Summary of Traffic and Simple Traffic Mapping

**Status: the one genuine gap — not scoped yet, worth being honest about that rather than implying it already exists.** The closest things that exist today are Headplane (the admin dashboard, built but never finished being configured) and the raw `nodes list` from Headscale — neither of which actually summarizes *traffic*, only device presence and status. A real "what's flowing, through which path, right now" view doesn't exist yet, even as a design. This is a legitimate next scoping document, not something to fold into tonight's work by assumption.

---

## How they actually connect

```
User
  └─ Devices (Soft Features / App)
        ├─→ VPN Backend (built) ──────────┐
        └─→ Identity (scoped) ─────┐      │
                                    ▼      ▼
                                 Presence (entity)
                                    │
                          Route Path Selection (undefined)
                          ┌─────────┼─────────┐
                          ▼         ▼         ▼
                   Mesh path   Declared-   Ordinary
                   (built)     origin      internet
                               (scoped)    (default,
                                            untouched)
                                    │
                                    ▼
                    API — presence attestation to
                    relying party (proven in miniature)
                                    │
                                    ▼
                         End device / server / internet

Functional Recovery sits outside this flow entirely — it's what
a User reaches for when Devices are lost, independent of any
single path above.

Traffic Summary and Mapping would sit alongside this whole diagram,
observing it — not yet designed.
```

## What this document actually settles

Nothing new gets decided here — every status above points back to a document already written. What this adds is the missing thing: **seeing all nine pieces in one place, in the order you actually think about them**, instead of scattered across four separate scoping documents written on different nights. Two real gaps surfaced by doing this: Route Path Selection and Traffic Summary/Mapping don't have scoping documents of their own yet. Worth treating those as the next two, not folding them into existing ones by assumption.
