"""
Atlas — Route Path Selection
============================

Lets a person change where the internet sees them from, at will, instead of
being assigned an egress once at signup and never being able to move it.

This is the difference between "Atlas gave me a VPN endpoint" and "I control
how I'm presented" — which is the actual thesis. Before this, `presence_provision
.match_exit_node()` did a one-time keyword match on the home address and that
was permanent. A traveler is the entire use case, and a traveler needs to
re-declare their origin.

What this module can and cannot do — stated plainly
---------------------------------------------------
Headscale CANNOT push an exit-node selection to a client. Exit-node choice is a
client-side setting in Tailscale; the coordination server grants *permission* to
route, it does not dictate the route. So "selecting a path" here means:

  1. Record the person's declared choice (server-side, authoritative)
  2. Verify the chosen egress is real, online, and route-approved
  3. Hand back the exact command that applies it on the device

Step 3 is manual today. When the native client agent from STATUS.md Part 3.5
exists, it will consume the same API and apply the change itself with no
command to paste. The API is deliberately shaped for that future consumer now,
so the agent won't need a different contract later.
"""

import headscale

# The honest third option: present from where you actually are. Not every
# situation calls for a declared origin — sometimes the truthful answer is the
# right one, and Atlas shouldn't make "route through something" the only choice.
DIRECT = "__direct__"

DIRECT_OPTION = {
    "name": DIRECT,
    "label": "Where I actually am",
    "description": "No egress. Present honestly from your current network.",
    "online": True,
    "exit_route_approved": True,
    "available": True,
    "ip_addresses": [],
}


def _is_exit_node(node):
    """A node is only an exit node if a default route is actually approved."""
    routes = node.get("routes") or []
    return any(r in ("0.0.0.0/0", "::/0") for r in routes)


def _is_serving_exit_route(node):
    """
    Approval is not the same as live. Headscale can approve a 0.0.0.0/0 route
    while the node's own tailscaled isn't currently advertising it — the exact
    gap that let Toronto show as a healthy option in the Lens on Aug 5 while
    `headscale nodes list-routes` showed its Serving column empty. `subnet_routes`
    is what the node is actually broadcasting right now; approved_routes is only
    what it's permitted to broadcast.
    """
    serving = node.get("serving_routes") or []
    return any(r in ("0.0.0.0/0", "::/0") for r in serving)


def list_exit_nodes():
    """
    Every egress the mesh currently offers, discovered live.

    Deliberately NOT read from presence_provision.EXIT_NODE_MAP, which is a
    hardcoded keyword table. Adding a new droplet in a new region should make it
    selectable without a code change; a stale hardcoded list would silently hide
    real capacity or offer egress that no longer exists.
    """
    nodes = []
    for n in headscale.get_nodes():
        if not _is_exit_node(n):
            continue
        serving = _is_serving_exit_route(n)
        nodes.append({
            "name": n.get("name"),
            "label": _friendly_label(n.get("name")),
            "description": _friendly_location(n.get("name")),
            "online": n.get("online", False),
            "exit_route_approved": True,
            "serving_route": serving,
            "available": bool(n.get("online", False)) and serving,
            "ip_addresses": n.get("ip_addresses", []),
            "last_seen": n.get("last_seen"),
        })
    nodes.sort(key=lambda x: (not x["available"], x["name"] or ""))
    return nodes


# Presentation-only mapping. If a name isn't known, the raw node name is shown
# rather than a wrong guess — better to display "EGR-Ams1" than to invent a city.
_LABELS = {
    "EGR-Tor1": ("Toronto", "Canada — Ontario"),
    "EGR-Lon1": ("London", "United Kingdom"),
    "atlas-mesh": ("New York", "United States — NY"),
}


def _friendly_label(name):
    return _LABELS.get(name, (name, None))[0] or name


def _friendly_location(name):
    return _LABELS.get(name, (None, None))[1] or "Egress node"


def available_paths(current_exit_node=None):
    """
    The full set of choices to show a person, current selection marked.

    Offline egress is returned but flagged unavailable rather than hidden.
    Silently dropping an option a person previously chose would leave them
    wondering where it went; showing it greyed out with a reason is honest.
    """
    paths = [dict(DIRECT_OPTION)]
    paths.extend(list_exit_nodes())
    for p in paths:
        p["current"] = (p["name"] == current_exit_node) or (
            current_exit_node in (None, "", DIRECT) and p["name"] == DIRECT
        )
    return paths


def resolve_path(name):
    """
    Validate a requested path. Returns the path dict, or raises ValueError.

    Rejecting an offline egress here is deliberate: letting someone select a
    dead exit node would produce exactly the symptom that cost a full day on
    Aug 3 — a connection that looks established but passes no traffic.
    """
    if name in (None, "", DIRECT):
        return dict(DIRECT_OPTION)

    for node in list_exit_nodes():
        if node["name"] == name:
            if not node["online"]:
                raise ValueError(
                    "{} is offline right now. Choose another egress, or present "
                    "from where you actually are.".format(_friendly_label(name))
                )
            if not node["serving_route"]:
                raise ValueError(
                    "{} is online but isn't currently serving its exit route — "
                    "its Tailscale client isn't advertising it right now, even "
                    "though the mesh has approved it. Choose another egress, or "
                    "present from where you actually are.".format(_friendly_label(name))
                )
            return node

    raise ValueError("'{}' isn't an egress this mesh offers.".format(name))


def exit_node_selector(path):
    """
    What to actually put after `--exit-node=`.

    Prefers the node's mesh IP over its name. Tailscale accepts either, but the
    name only resolves if MagicDNS is enabled on the coordination server, and
    Headscale's MagicDNS is optional and often off. Names also get normalised
    (`EGR-Tor1` -> `egr-tor1`), so a name that looks right in the dashboard can
    fail on the device. The 100.64.x.x address is stable and unambiguous.

    Accepts either a path dict (from resolve_path) or a bare name.
    """
    if isinstance(path, dict):
        ips = path.get("ip_addresses") or []
        # Prefer IPv4 in the CGNAT range Tailscale assigns.
        for ip in ips:
            if ip.startswith("100."):
                return ip
        if ips:
            return ips[0]
        return path.get("name")
    return path


def build_switch_command(path, allow_lan=True):
    """
    The exact command that applies a path on an already-enrolled device.

    `tailscale set` (not `tailscale up`) is used deliberately — it changes one
    setting on a running connection instead of re-running the whole login flow,
    so it won't prompt for re-authentication.

    allow_lan defaults to True because STATUS.md Part 3.5 names this exact
    setting as the kind of thing that is "buried, non-obvious, and meaningless
    to someone who isn't a network engineer." Without it, selecting an exit node
    silently breaks printers, NAS boxes, and anything else on the local network
    — and the person has no idea why.
    """
    name = path.get("name") if isinstance(path, dict) else path

    if name in (None, "", DIRECT):
        return {
            "command": "tailscale set --exit-node=",
            "explanation": "Clears your egress. You'll present from whatever "
                           "network you're actually on.",
            "selector": "",
        }

    selector = exit_node_selector(path)
    cmd = "tailscale set --exit-node={}".format(selector)
    if allow_lan:
        cmd += " --exit-node-allow-lan-access"

    label = _friendly_label(name)
    note = ("Local devices (printers, NAS) stay reachable." if allow_lan
            else "Local network access is disabled while active.")
    # Name the egress in words, since the command itself now shows an IP that
    # means nothing to a person reading it.
    return {
        "command": cmd,
        "explanation": "Routes your traffic out through {} ({}). {}".format(
            label, selector, note),
        "selector": selector,
    }


def describe_change(from_node, to_node):
    """One plain sentence about what just changed, for the person, not the log."""
    f = _friendly_label(from_node) if from_node and from_node != DIRECT else "your real location"
    t = _friendly_label(to_node) if to_node and to_node != DIRECT else "your real location"
    if f == t:
        return "No change — you're still presenting from {}.".format(t)
    return "The internet will now see you from {} instead of {}.".format(t, f)
