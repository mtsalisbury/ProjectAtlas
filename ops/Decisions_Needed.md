# Decisions Needed — Master List

**Purpose:** Every open question from the three scoping documents, in one place, ordered by what actually blocks the most downstream work. Answer these deliberately, with real time set aside — not decided by default just because building started before the question got addressed.

**How to use this:** work top to bottom. The first two decisions shape *how the identity service gets built at all* — get to those before writing any code, even code that seems unrelated. Everything below them can wait longer without cost.

---

## Blocks everything — answer before Phase 1 of the identity service begins

### 1. ~~Recovery: multi-device peer-authorization, or Apple/Google keychain sync?~~ — **Decided: neither. A recovery portal, checking a self-held recovery phrase.**
*From: Scope_Presence_Ownership.md*
Generated once at registration, held only by the person, checked only at the portal. Depends on no company — not Apple, not Google, not Atlas itself. The real cost: no safety net if the phrase is lost too. That's the accepted price of it being genuinely theirs.

### 2. Visibility: start with the simple transparency answer, or invest in the stronger cryptographic one (blind signatures) from the start?
*From: Scope_Presence_Ownership.md*
The simple answer ships faster. The strong one is a structural guarantee, not a promise — but it changes how the identity service issues tokens from the ground up. Retrofitting this later is expensive; deciding it now is cheap.

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

## What's already decided — don't reopen these

- This is a controlled package, not an open internet standard. Atlas approves relying parties, indefinitely.
- Registration to become a relying party stays closed by default.
- Declared-origin routing is an optional capability of the one Presence entity — never a blanket, on-by-default override of normal traffic.
- Public-key verification, not a shared secret, is the right technical approach regardless of how open or closed registration stays.
- Token signing algorithm: ES256.
- Recovery: a portal checking a self-held recovery phrase, generated once at registration. No company-dependent safety net, by design.
