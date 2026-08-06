# Runbook — Home Egress / Multi-Group Routing Go-Live

Designed and written Aug 5–6, nothing here has touched real infrastructure
yet. Converts "designed" into "proven," same standard as every other runbook
in this project — real observed values, not "it worked."

**What this builds:** the Mac's traffic gets split by destination into four
groups — MFA/security-sensitive (always home), USA (NY), Canada (Toronto),
everything else (direct, local, untouched) — plus the phone gets a simple
stopgap for the MFA-from-home piece using the stock Tailscale app.

**Can't run tonight:** the home Pi step. It needs local/wired access to your
house network to give the Pi its first Tailscale identity — nothing in this
session's sandbox has a path into your home network. Everything else below
doesn't depend on the Pi and can run now.

---

## Step 1 — Add SOCKS proxies to NY and Toronto (can run now)

From your Mac, in the repo:

```bash
cd ~/Documents/GitHub/ProjectAtlas/ops/home-egress
chmod +x add-socks-proxy.sh

# Toronto — prefer its mesh IP per the standing "always SSH to mesh
# addresses" rule (STATUS.md)
NODE_HOST=100.64.0.6 ./add-socks-proxy.sh

# NY / atlas-mesh — this IS the control-plane server, reach it by its
# known public IP
NODE_HOST=192.241.147.167 ./add-socks-proxy.sh
```

Each run prints the mesh `IP:port` to use as `TORONTO_SOCKS` / `NY_SOCKS`
later. **Write both down.**

**Verify each one:**

```bash
ssh root@100.64.0.6 systemctl status atlas-mesh-socks
ssh root@192.241.147.167 systemctl status atlas-mesh-socks
```

Both should show `active (running)`.

---

## Step 2 — Set up the home Pi (tomorrow, at the house)

Get the Pi on the network first (wired, or however you normally reach it),
copy `ops/home-egress/setup-home-node.sh` onto it, then on the Pi itself:

```bash
sudo NODE_NAME=EGR-Home1 ./setup-home-node.sh
```

If the Pi can't SSH out to the control host (`192.241.147.167`) from your
home network for some reason, the script will say so — in that case run the
`approve-routes` / `rename` commands it would have run, by hand, from your
Mac instead, using the node ID it prints.

**Verify:**

```bash
ssh root@192.241.147.167 "docker exec headscale headscale nodes list-routes"
```

`EGR-Home1` should show Approved + Available + Serving, same as NY/Toronto.

Write down the mesh `IP:port` it prints for `HOME_SOCKS`.

**Also right away:** on your phone, open the stock Tailscale app, select
`EGR-Home1` as the exit node. That's the entire MFA-from-home rule on iOS
for now — every app's traffic goes through home until a real per-app iOS
client exists (not started, this is the honest stopgap).

---

## Step 3 — Fill in MFA domains (before Step 4 matters)

Edit `ops/home-egress/mac-client/rules/mfa-home.txt` — replace the empty
placeholder with your actual bank(s), authenticator app(s), anything doing
push or step-up MFA. One domain per line. This is the one list that can't be
guessed for you.

---

## Step 4 — Mac rule router

```bash
brew install sing-box
cd ~/Documents/GitHub/ProjectAtlas/ops/home-egress/mac-client

NY_SOCKS=<from Step 1> \
TORONTO_SOCKS=<from Step 1> \
HOME_SOCKS=<from Step 2> \
python3 generate-config.py

sudo sing-box run -c config.json
```

Leave it running in its own terminal for the first test — don't daemonize
yet.

---

## Step 5 — Live verification (the actual proof, not a guess)

With sing-box running:

1. Visit a "what's my IP" site through a **USA-listed domain** (e.g.
   `walmart.com`) — should show NY's egress IP (`144.126.200.88` — wait,
   that's London's; confirm NY's actual public IP from
   `ssh root@192.241.147.167 curl -4 icanhazip.com` and use that as the
   expected value).
2. Visit `walmart.ca` — should show Toronto's egress IP (`134.122.41.187`).
3. Visit a site **not in any rule file** — should show your real, current
   IP (direct).
4. Visit a domain you added to `mfa-home.txt` — should show home's egress
   IP (get it the same way as NY's, from the Pi).

Record the actual IPs observed for each, not just pass/fail — same
standard as every other proof in this project.

---

## Known open items, honest as of tonight

- Nothing above has run once against real infrastructure.
- No iOS app exists for per-group routing on the phone — only the
  whole-device stopgap (Step 2's last part).
- DNS-over-HTTPS in some browsers may bypass sniffing — flagged in
  `mac-client/README.md`, not yet tested for.
- MFA push notifications riding Apple's shared push infrastructure aren't
  isolable this way — only each app's own direct traffic is.
- Not yet running as a LaunchDaemon — manual `sudo sing-box run` only,
  deliberately, until proven once by hand first.
