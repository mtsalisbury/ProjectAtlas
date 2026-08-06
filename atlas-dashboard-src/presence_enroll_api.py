"""
Atlas — Client Enrollment & Lens API
====================================

The client-facing tail: what actually ties a person's device to the mesh.

Closes the gap named explicitly in STATUS.md Part 3.8:

    "the backend can now correctly grant permission for a user to route through
     their matched exit node, but nothing yet tells their actual device to
     select and use that exit node."

Mounted as an APIRouter, so main.py needs two new lines and none of its
existing routes are touched:

    import presence_enroll_api
    app.include_router(presence_enroll_api.router)

IMPORTANT: those lines must go ABOVE the final
`app.mount("/", StaticFiles(...))` in main.py. The catch-all static mount
swallows any route registered after it.

Routes (all under /api/presence/, which main.py's middleware already exempts
from the admin ATLAS_TOKEN; these authenticate with X-Presence-Token instead,
so a client can never reach /api/topology):

    POST /api/presence/enroll          issue a pre-auth key + per-platform steps
    POST /api/presence/enroll/mobile   register a pasted node key from the app
    GET  /api/presence/enroll/keys     list outstanding keys for this Presence
    POST /api/presence/enroll/revoke   revoke an outstanding key
    GET  /api/presence/lens            this Presence's own view of itself

Why the Lens lives here and not in the admin dashboard
------------------------------------------------------
STATUS.md Part 3.5: "Client agents are viewers first, with control layered on
top." /api/presence/lens answers, for exactly one Presence: who am I, what
context am I in, which devices are mine, which egress am I presenting from,
and is that actually working right now. It filters by the caller's own context
and never returns the full mesh.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import db
import enrollment
import routing

router = APIRouter(prefix="/api/presence", tags=["presence-client"])


# ---------------------------------------------------------------------------
# Auth — same pattern as main.get_current_user, kept local to avoid a circular
# import between main.py and this router.
# ---------------------------------------------------------------------------

def get_current_user(request: Request):
    token = request.headers.get("x-presence-token", "")
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user


def require_provisioned(user):
    """
    A device can only be enrolled into a Presence that actually exists in
    Headscale. Returns (headscale_username, persona).
    """
    hs_user = user.get("headscale_username")
    if not hs_user:
        raise HTTPException(
            status_code=409,
            detail="Your Presence hasn't been built yet. "
                   "Answer the questionnaire first.",
        )
    return hs_user, db.get_latest_persona(user["id"])


def exit_node_of(persona):
    return (persona or {}).get("exit_node")


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class EnrollRequest(BaseModel):
    platform: str = ""            # macos | linux | windows | mobile
    device_label: str = ""
    reusable: bool = False
    expiration: str = enrollment.DEFAULT_KEY_EXPIRY


class MobileEnrollRequest(BaseModel):
    node_key: str                 # full registration URL or bare key
    device_label: str = ""


class RevokeRequest(BaseModel):
    key: str


class PathRequest(BaseModel):
    path: str                     # exit node name, or "__direct__"
    allow_lan: bool = True
    reason: str = ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/enroll")
def enroll_device(req: EnrollRequest, request: Request):
    """
    Issue a pre-auth key for this Presence and return per-platform instructions.

    This is the step that was missing. Provisioning granted the ACL permission;
    this hands the device an actual way in, pre-pointed at the right
    coordination server and the right exit node.
    """
    user = get_current_user(request)
    hs_user, persona = require_provisioned(user)
    exit_node = exit_node_of(persona)

    try:
        key = enrollment.create_preauth_key(
            hs_user, expiration=req.expiration, reusable=req.reusable
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Resolve the exit node to its mesh IP so the enrollment command doesn't
    # depend on MagicDNS. If the mesh is unreachable we still issue the key and
    # fall back to the name — a usable command beats no command.
    selector = None
    if exit_node:
        try:
            selector = routing.exit_node_selector(routing.resolve_path(exit_node))
        except Exception:
            selector = None

    return {
        "presence": {"email": user["email"], "context": hs_user},
        "exit_node": exit_node,
        "key": key["key"],
        "login_server": key["login_server"],
        "expires_in": key["expiration"],
        "reusable": key["reusable"],
        "issued_at": key["issued_at"],
        "instructions": enrollment.build_enrollment_instructions(
            key, exit_node, exit_node_selector=selector),
        "requested_platform": req.platform or None,
        "device_label": req.device_label or None,
    }


@router.get("/enroll/mobile-steps")
def mobile_steps(request: Request):
    """
    Mobile setup instructions, without issuing a key.

    The mobile path can't use a pre-auth key at all, so minting one just to
    render instructions would burn a credential nobody redeems. Served from the
    same generator as the real thing, so the coordination-server URL can't drift.
    """
    get_current_user(request)
    stub = {"key": "", "login_server": enrollment.LOGIN_SERVER}
    return enrollment.build_enrollment_instructions(stub)["mobile"]


@router.post("/enroll/mobile")
def enroll_mobile(req: MobileEnrollRequest, request: Request):
    """
    Register a phone or tablet from the link its Tailscale app displays.

    STATUS.md Part 2 records, correctly, that the mobile apps cannot accept a
    pre-auth key — that's a Tailscale limitation and isn't being re-litigated.
    What this removes is the *administrator* from mobile onboarding, which was
    the real bottleneck: previously someone had to reach Mike so he could run
    `headscale nodes register` by hand. Now they paste the link their own app
    already shows them. Not zero-touch; one-paste and self-service.
    """
    user = get_current_user(request)
    hs_user, persona = require_provisioned(user)

    try:
        result = enrollment.register_node(hs_user, req.node_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    exit_node = exit_node_of(persona)
    result["device_label"] = req.device_label or None
    result["exit_node"] = exit_node
    result["next_step"] = (
        "Registered. On the device, open Tailscale → Exit Node and select "
        "{} to present from there.".format(exit_node) if exit_node else "Registered."
    )
    return result


@router.get("/enroll/keys")
def list_keys(request: Request):
    """Outstanding keys for this Presence, so a person can audit and revoke."""
    user = get_current_user(request)
    hs_user, _ = require_provisioned(user)
    try:
        return {"keys": enrollment.list_preauth_keys(hs_user)}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enroll/revoke")
def revoke_key(req: RevokeRequest, request: Request):
    user = get_current_user(request)
    hs_user, _ = require_provisioned(user)
    try:
        enrollment.expire_preauth_key(hs_user, req.key)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"revoked": True, "revoked_at": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Route Path Selection
# ---------------------------------------------------------------------------

@router.get("/paths")
def list_paths(request: Request):
    """
    Every egress this Presence can choose from, discovered live from the mesh.

    Includes "where I actually am" as a first-class option — presenting
    honestly is a legitimate choice, not the absence of one.
    """
    user = get_current_user(request)
    persona = db.get_latest_persona(user["id"]) if user.get("id") else None
    current = exit_node_of(persona)
    try:
        paths = routing.available_paths(current)
    except Exception as e:
        raise HTTPException(status_code=503,
                            detail="Can't reach the mesh to list egress options: " + str(e))
    return {
        "current": current or routing.DIRECT,
        "paths": paths,
        "history": db.get_path_history(user["id"], limit=10) if user.get("id") else [],
    }


@router.post("/path")
def set_path(req: PathRequest, request: Request):
    """
    Change this Presence's declared origin.

    Records the choice server-side and returns the command that applies it on
    the device. Headscale can't push exit-node selection to a client — that's
    a client-side setting — so this is authoritative about *intent*, and the
    device still has to act on it. The native client agent will consume this
    same endpoint and apply it without a command to paste.
    """
    user = get_current_user(request)
    hs_user, persona = require_provisioned(user)
    previous = exit_node_of(persona)

    try:
        path = routing.resolve_path(req.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503,
                            detail="Can't reach the mesh to verify that egress: " + str(e))

    target = path["name"]
    stored = None if target == routing.DIRECT else target

    if not db.set_persona_exit_node(user["id"], stored):
        raise HTTPException(status_code=409, detail="No persona to update.")
    db.record_path_change(user["id"], previous, stored, req.reason)

    # Pass the resolved path (not just the name) so the command can use the
    # node's mesh IP, which doesn't depend on MagicDNS being enabled.
    switch = routing.build_switch_command(path, allow_lan=req.allow_lan)

    return {
        "changed": (previous or routing.DIRECT) != target,
        "previous": previous or routing.DIRECT,
        "current": target,
        "label": path.get("label"),
        "summary": routing.describe_change(previous, target),
        "apply": switch,
        "note": ("Your choice is saved. Run the command above on each device "
                 "to apply it — Atlas records where you've chosen to appear "
                 "from, but the device performs the switch."),
        "changed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/lens")
def lens(request: Request):
    """
    The Lens: this Presence's own view of itself.

    Deliberately degrades rather than 500s. If the mesh is unreachable, a person
    can still see who they are and what they chose — STATUS.md Part 3.5:
    "this should be reviewable offline ... rather than treating connectivity as
    a precondition for visibility."
    """
    user = get_current_user(request)
    hs_user = user.get("headscale_username")
    persona = db.get_latest_persona(user["id"]) if user.get("id") else None

    devices, mesh_error = [], None
    if hs_user:
        try:
            for n in enrollment.nodes_for_user(hs_user):
                devices.append({
                    "name": n.get("name"),
                    "online": n.get("online", False),
                    "ip_addresses": n.get("ip_addresses", []),
                    "last_seen": n.get("last_seen"),
                })
        except Exception as e:
            mesh_error = str(e)

    exit_node_name = exit_node_of(persona)
    exit_node = None
    if exit_node_name and mesh_error is None:
        try:
            exit_node = enrollment.get_exit_node_info(exit_node_name)
        except Exception:
            exit_node = None

    return {
        # Who you are — the part that doesn't change when the network does.
        "presence": {
            "email": user["email"],
            "context": hs_user,
            "provisioned": bool(hs_user),
        },
        # How you've chosen to be presented.
        # A null exit node means a deliberate choice to present from your real
        # location — not a missing setting. The two must not look the same.
        "presentation": {
            "exit_node": exit_node_name,
            "presenting_directly": exit_node_name is None,
            "label": (routing._friendly_label(exit_node_name)
                      if exit_node_name else "Where I actually am"),
            "exit_node_online": (exit_node or {}).get("online"),
            "exit_route_approved": (exit_node or {}).get("exit_route_approved"),
            "exit_route_serving": (exit_node or {}).get("exit_route_serving"),
            "egress_ip": ((exit_node or {}).get("ip_addresses") or [None])[0],
        },
        # The devices currently carrying this Presence.
        "devices": devices,
        "device_count": len(devices),
        "online_device_count": sum(1 for d in devices if d["online"]),
        # The questionnaire answers, under their real meanings (see main.py's
        # /api/presence/status for the same mapping).
        "persona": {
            "goal": (persona or {}).get("q1"),
            "devices_owned": (persona or {}).get("q2"),
            "home": (persona or {}).get("q3"),
            "presented_as": (persona or {}).get("q4"),
            "skill_level": (persona or {}).get("q5"),
            "built_at": (persona or {}).get("built_at"),
        } if persona else None,
        "mesh_reachable": mesh_error is None,
        "mesh_error": mesh_error,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
