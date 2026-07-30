# Runbook: OIDC Setup — Automatic Registration for Atlas Mesh

**Status:** Planning only — not yet executed | **Goal:** eliminate the manual "copy key, forward to server" step entirely

## What this changes, in one sentence

Right now, joining the mesh means a person gets a key and someone (you, over SSH) has to manually register it. With OIDC configured, the person signs in with a real identity provider instead, and Headscale completes registration itself, automatically, the moment that login succeeds — no key ever gets copied by anyone.

## What doesn't change

The person still sees one login screen. This isn't zero-touch — it removes the *admin's* manual step, not the user's single sign-in. That distinction matters so expectations stay accurate once this is built.

## Decisions to make before starting — answer these first, don't skip ahead

1. **Which identity provider?**
   - Google — fastest to set up if you or your users already have Google accounts.
   - Microsoft/Entra ID — better fit if this is ever positioned toward corporate/employment users.
   - Self-hosted (Authentik, Zitadel) — full control, no dependency on a third party, but it's its own separate build project, not a quick add-on.
   - *This decision can differ per context* — nothing says `personal` and `employment` have to use the same provider. Worth deciding whether they should.

2. **Who's allowed to register at all?**
   OIDC configs support restricting by specific email addresses, or by domain (e.g., anyone `@yourcompany.com`). Decide this now — an open registration page with no restriction means anyone who finds the URL and has a Google account could attempt to join.

3. **How does a new person's context get decided?**
   Right now, contexts (`personal`, `employment`, `pseudonymous`) are assigned manually when an admin runs the register command. OIDC doesn't automatically know which context someone should land in — that has to be decided: is it based on which URL/provider they used, their email domain, or still a manual step after the automatic login?

## The actual steps, once those decisions are made

### Step 1 — Register an OIDC application with the chosen provider
Done on the provider's side (Google Cloud Console, Azure Portal, or your self-hosted provider's admin panel), not on our server.

**You'll need to provide the provider with:**
- A redirect URI: `https://mesh.rpnwireless.com/oidc/callback`
- An application name
- Requested scopes: `openid`, `profile`, `email`

**You'll get back:**
- A Client ID
- A Client Secret (treat this like a password — same handling as the cookie secret and API keys from tonight, never committed to the repo)

### Step 2 — Add the `oidc:` block to Headscale's `config.yaml`
This is where the Client ID, Client Secret, issuer URL, and the access restriction from Decision 2 above all get entered.

**Checkpoint:** restart Headscale and check its logs specifically for OIDC initialization — a misconfigured client ID or secret fails loudly and clearly here, before anyone tries to log in.

### Step 3 — Visit the registration URL and confirm the page itself changed
Before testing a real login, just load `mesh.rpnwireless.com` fresh. **Success looks like:** a real "Sign in with [Provider]" page instead of the old plain page showing a command to copy. If it still shows the old page, OIDC didn't actually take effect — check Step 2 again before going further.

### Step 4 — Complete one real login and watch what happens
**Success looks like:** the device shows up in `headscale nodes list` (or Headplane) automatically, with no `docker exec ... register` command run by anyone.

**If it doesn't appear:** this is the moment to check Headscale's logs for the callback — a redirect URI mismatch between what's registered with the provider and what's in `config.yaml` is the most common failure here.

### Step 5 — Confirm the context assignment matches what was decided in the pre-work
Whatever was decided in "Decision 3" above — verify it actually happened. This is the step most likely to need a second pass once you see it work for real the first time.

## What "seeing the function" looks like, concretely

The whole point of this runbook, before touching anything: once built, the entire flow becomes — someone taps a link, signs in once with Face ID or a password they already know, and their device is simply *there*, in the dashboard, correctly contextualized, with nothing forwarded by hand at any point. That's the actual product experience underneath tonight's manual testing.

## Known open question, not yet answered

Whether OIDC login on a *mobile* device still requires the browser hop we confirmed can't be skipped tonight, or whether it changes that in any way, hasn't been tested — worth confirming empirically once this is built, not assumed either way.
