# KB: Device Onboarding Flow — Pre-Auth Key to Dashboard

**Status:** Draft v0.1 | **Covers:** Atlas mesh infrastructure (Headscale + Headplane) | **Last updated:** July 2026

## Purpose

This document describes the intended flow for a device joining the Atlas mesh using a pre-generated key — no manual URL, no copy-pasted registration key, no approval step. It exists so that if something breaks, whoever's looking at it can identify *which* step failed rather than staring at one large system and guessing.

Each step below states what success looks like and what a failure at that specific step tells you.

## Infrastructure Map

Before troubleshooting anything, know what's actually talking to what:

```
Cloudflare DNS (rpnwireless.com)
  ├─ mesh.rpnwireless.com  → same server IP
  └─ admin.rpnwireless.com → same server IP
        │
        ▼
DigitalOcean VM (atlas-mesh, 192.241.147.167)
        │
        ▼
Caddy (reverse proxy, handles TLS for both domains)
  ├─ mesh.rpnwireless.com  → headscale container (port 8080)
  └─ admin.rpnwireless.com → headplane container (port 3000)
        │
        ▼
Headscale (control plane, source of truth for users, devices, ACL policy)
        ▲
        │ (talks to Headscale via API key)
Headplane (dashboard — read/write view into Headscale, no independent data of its own)
```

If something is broken, the first question is always: **which layer is it in?** DNS, Caddy/TLS, Headscale itself, Headplane, or the ACL policy. The steps below map directly onto this stack.

## The Intended Flow

### Step 1 — Admin generates a pre-auth key

Done ahead of time, before any user connects anything. Via Headplane's dashboard, or on the server:
```bash
docker exec headscale headscale preauthkeys create --user <context-name>
```

**Success looks like:** a key is returned, tied to a specific context (`personal`, `employment`, etc.), with a visible expiration.

**If this fails:** the problem is at the Headscale layer, not the network or the device. Check that the named user/context actually exists (`headscale users list`) — a typo in the context name is the most common cause.

### Step 2 — Key is delivered to the device

For now, this is manual (copy the key, give it to the device). In a real product, this would be embedded in an install link or QR code — not yet built.

**Success looks like:** the person setting up the device has the key string, unexpired.

**If this fails:** pre-auth keys have a defined expiration (set at creation) — if too much time passed between generating the key and using it, it's simply expired. Generate a new one; there's no way to "extend" an expired key.

### Step 3 — Device connects using the key

```bash
tailscale up --login-server https://mesh.rpnwireless.com --authkey <key>
```

**Success looks like:** the command returns immediately with confirmation — **no browser URL should appear.** That's the actual signal that pre-auth worked: if a `mesh.rpnwireless.com/register/...` link shows up instead, the key wasn't accepted and the client silently fell back to the old manual-approval flow.

**If this fails (falls back to manual flow):** the key was wrong, already used (if not marked reusable), or expired. Go back to Step 1 and generate a fresh one — don't try to reuse the same key string.

### Step 4 — Device appears in the node list

```bash
docker exec headscale headscale nodes list
```
or the equivalent view in Headplane's dashboard.

**Success looks like:** the device appears, assigned to the correct context, status `online`, with a recent `Last seen` timestamp.

**If it doesn't appear at all:** check Headscale's own logs (`docker compose logs headscale --tail 50`) for a registration error — this is a server-side rejection, not a client problem.

**If it appears under the wrong context:** the pre-auth key used was generated for the wrong user in Step 1. The fix is at Step 1, not here.

### Step 5 — Connectivity respects the ACL policy

From the newly connected device, try to reach a peer in the *same* context, and separately, a peer in a *different* context:
```bash
tailscale ping <same-context-peer-address>
tailscale ping <different-context-peer-address>
```

**Success looks like:** the same-context ping succeeds; the different-context ping fails with `no matching peer`.

**If both pings succeed** (no isolation): the ACL policy either isn't loaded or reverted to allow-all. Check `config.yaml` on the server for the `policy:` block, and confirm `acl.hujson` still exists and is syntactically valid.

**If both pings fail** (nothing reachable, even same-context): the ACL policy is too restrictive, or there's an unrelated network/DERP problem. Check Headscale's logs for policy-loading errors first.

### Step 6 — The dashboard reflects real state

Headplane should show everything above — users, devices, status, context assignment — without needing SSH access to confirm it.

**If Headplane shows stale or missing data:** it's not a Headscale problem, it's specifically the connection *between* Headplane and Headscale. Check:
- Is the API key Headplane is using still valid, or expired? (Keys were created with a 90-day expiration.)
- Is the `headplane` container itself running? (`docker compose ps`)
- Check `docker compose logs headplane --tail 50` for authentication errors specifically.

## Quick Reference: Symptom → Where to Look

| Symptom | Likely layer | What to check |
|---|---|---|
| Can't reach `admin.rpnwireless.com` or `mesh.rpnwireless.com` at all | DNS / Caddy | `dig` the domain, confirm Cloudflare A record is correct and "DNS only" (not proxied) |
| Domain loads but shows a certificate warning | Caddy / TLS | `docker compose logs caddy` — look for ACME/Let's Encrypt errors |
| `tailscale up --authkey` falls back to a browser URL | Pre-auth key | Key expired or already used — generate a new one (Step 1) |
| Device never appears in node list | Headscale | `docker compose logs headscale` for registration errors |
| Device appears under the wrong context | Admin error, not a bug | Re-check which user the pre-auth key was created for |
| Devices in different contexts can reach each other | ACL policy | Confirm `policy:` block in `config.yaml` and `acl.hujson` are both present and valid |
| Devices in the *same* context can't reach each other | ACL policy (too strict) or DERP | Check policy syntax first, then Headscale logs for relay/DERP errors |
| Headplane shows outdated info | Headplane ↔ Headscale link | Check API key expiration and `headplane` container logs |

## What This Document Doesn't Cover Yet

This describes the manual pre-auth key flow only — a human still has to generate the key and hand it to the device. It does not yet cover an automated onboarding experience (QR code, install link, or an actual Atlas Agent handling this invisibly), which remains a later-stage build, not something tested tonight.
