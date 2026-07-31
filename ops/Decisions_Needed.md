# Decisions Needed — Master List

**Purpose:** Every open question from the three scoping documents, in one place, ordered by what actually blocks the most downstream work. Answer these deliberately, with real time set aside — not decided by default just because building started before the question got addressed.

**How to use this:** work top to bottom. The first two decisions shape *how the identity service gets built at all* — get to those before writing any code, even code that seems unrelated. Everything below them can wait longer without cost.

---

## Blocks everything — answer before Phase 1 of the identity service begins

### 1. ~~Recovery: multi-device peer-authorization, or Apple/Google keychain sync?~~ — **Decided: neither. A recovery portal, checking a self-held recovery phrase.**
*From: Scope_Presence_Ownership.md*
Generated once at registration, held only by the person, checked only at the portal. Depends on no company — not Apple, not Google, not Atlas itself. The real cost: no safety net if the phrase is lost too. That's the accepted price of it being genuinely theirs.

### 2. ~~Visibility: simple transparency, blind signatures, or category-level with a blocklist?~~ — **Decided, final: blind signatures.**
*From: Scope_Presence_Ownership.md*
Went through a brief detour to category-visibility with a safety blocklist, then settled back — destination-level filtering (dark web, terrorist-affiliated infrastructure) is correctly the ISP's function, not Atlas's. Once that responsibility is off the table, there's no remaining reason to give up the stronger guarantee. Atlas structurally cannot see which relying party a token is used at.

---

## Blocks Phase 1 specifically — answer while building the identity service

### 3. Where does the identity service actually live?
*From: Scope_Unify_Presence.md*
New subdomain (matching the `mesh.` / `admin.` pattern), or folded into an existing container? Affects the deployment work directly, not just the design.

### 4. ~~What signs the tokens — which algorithm?~~ — **Decided: ES256**
*From: Scope_Unify_Presence.md*
Smaller, faster, and the current security-community recommendation. The compatibility risk that would normally favor the older RS256 doesn't really apply here — since relying-party registration stays closed and curated, ES256 support is simply confirmed during approval, not a blind risk taken on an unknown partner.

### 5. How does key rotation actually work?
*From: Scope_Unify_Presence.md*
If the signing key ever needs to change, every relying party needs a way to notice without breaking. This is an operational design question, not an edge case — needs an answer before the first real relying party depends on the current key.

---

## Can wait — genuinely downstream, no need to force these yet

### 6. How many declared-origin locations, and what's the real infrastructure cost?
*From: Scope_Declared_Origin.md*
This entire capability was explicitly scoped to not start before Phase 1 of the identity service exists. Nothing lost by leaving this open for now.

### 7. How strictly must a relying party verify a declared-origin claim?
*From: Scope_Declared_Origin.md*
Same as above — depends on infrastructure that doesn't exist yet. Revisit once #6 has an answer.

---

---

## New from tonight — genuinely unresolved, worth real time before building

### 8. ~~Malicious-activity monitoring conflicts directly with the privacy decisions already locked in.~~ — **Decided: not Atlas's function.**
Resolved the same way as decision #2, and for the same reason: filtering or flagging malicious destinations is the ISP's layer, not an identity platform's. Atlas's function is proving who someone is — not policing what the open internet is allowed to reach. Taking on fraud/malicious-activity monitoring would mean rebuilding exactly the visibility Gap 2 was designed to avoid, for a responsibility that isn't actually Atlas's to carry. No tension left to hold — the two decisions resolve each other.

### 9. Route Path Selection has a real direction now, but not a full design.
Resolved conceptually: Headscale's existing exit-node capability, driven by a rule the client itself holds — not new invention. Not yet resolved: how that rule is actually represented (stored where, tied to which part of the Presence token), and how it connects to the identity/token work in `Scope_Unify_Presence.md`. Needs its own short scoping pass, not a full one — the hard conceptual part is already solved.

### 10. Homescale — real, narrower than first described, still needs a design pass.
Resolved: this is Headscale's existing "subnet router" pattern, not new network science — one node advertising the devices behind it. Not yet resolved: how the simple, auto-updating status view actually gets built, and the USB one-click provisioning flow (real, precedented — Raspberry Pi imagers work this way — but not yet designed for this specific case).

---

## Provisioning — what actually needs buying before tomorrow's build

**Nothing new needed for the identity service or recovery portal themselves.** Same server, new container, same pattern as every deploy so far — no purchase required.

**One real thing worth checking first: server capacity.** The droplet has been sitting around 69–71% memory usage even before adding an identity service and a portal. Worth checking current headroom before building further:
```
free -h
```
If it's tight, upgrading from the current $4–6/month droplet to the next size (~$12/month for 2GB) is cheap, real insurance against another late-night debugging session caused by the server simply running out of room.

**For Homescale specifically, if you want to actually test it tomorrow, not just design it:** a real piece of hardware to be the Homescale node. A Raspberry Pi (roughly $35–75 depending on model) is the standard, well-precedented choice — or, cheaper still, any spare PC, router, or switch already sitting unused works exactly as well for a first test. No need to buy anything if something spare already exists.

**Nothing else on tonight's list requires a purchase** — the MFA second factor uses a free authenticator app on a phone already owned, and declared-origin infrastructure (a real exit node in a specific location) stays correctly out of scope until after Phase 1, per last night's ordering.

## What's already decided — don't reopen these

- This is a controlled package, not an open internet standard. Atlas approves relying parties, indefinitely.
- Registration to become a relying party stays closed by default.
- Declared-origin routing is an optional capability of the one Presence entity — never a blanket, on-by-default override of normal traffic.
- Public-key verification, not a shared secret, is the right technical approach regardless of how open or closed registration stays.
- Token signing algorithm: ES256.
- Recovery: a portal checking a self-held recovery phrase, generated once at registration. No company-dependent safety net, by design.
- Visibility: blind signatures, final. Atlas structurally cannot see which relying party a token is used at — not a promise, a cryptographic property.
- Destination-level safety filtering (dark web, terrorist-affiliated infrastructure, malicious-activity monitoring generally) is the ISP's function, not Atlas's. This isn't a gap to fill later — it's out of scope on purpose.
