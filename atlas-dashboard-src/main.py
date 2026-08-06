import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import db

# Must run before importing home_egress_api — that module seeds its table
# at import time, so the table has to exist first. Learned by nearly
# shipping a startup crash: every other import used to happen before
# db.init_db() ran at all.
db.init_db()

import headscale
import h6_test
import exit_test
import h5_test
import presence_provision
import presence_enroll_api
import home_egress_api

app = FastAPI(title="Atlas Dashboard API")
ATLAS_TOKEN = os.environ.get("ATLAS_TOKEN", "")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://presence.rpnwireless.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Presence-Token", "X-Atlas-Token"],
)

@app.middleware("http")
async def check_token(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/presence/"):
        return await call_next(request)
    if path.startswith("/api/") and path != "/health":
        token = request.headers.get("x-atlas-token", "")
        if token != ATLAS_TOKEN:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

@app.get("/health")
def health():
    return {"status": "ok", "service": "atlas-dashboard"}

@app.get("/api/topology")
def topology():
    try:
        return {"nodes": headscale.get_nodes()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SnapshotRequest(BaseModel):
    node_id: int
    label: str
    network: dict

@app.post("/api/test/h6/snapshot")
def h6_snapshot(req: SnapshotRequest):
    try:
        return h6_test.snapshot(req.node_id, req.label, req.network)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CompareRequest(BaseModel):
    snapshot_a: dict
    snapshot_b: dict

@app.post("/api/test/h6/compare")
def h6_compare(req: CompareRequest):
    try:
        return h6_test.compare(req.snapshot_a, req.snapshot_b)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExitCheckRequest(BaseModel):
    exit_node: str
    observed_ip: str

@app.post("/api/test/exit-node/check")
def exit_node_check(req: ExitCheckRequest):
    try:
        return exit_test.check(req.exit_node, req.observed_ip)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class H5Request(BaseModel):
    node_id: int

@app.post("/api/test/h5/run")
def h5_run(req: H5Request):
    try:
        return h5_test.run_recovery_test(req.node_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ProvisionRequest(BaseModel):
    q1: str
    q2: str
    q3: str
    q4: str
    q5: str

def get_current_user(request: Request):
    token = request.headers.get("x-presence-token", "")
    user = db.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user

@app.post("/api/presence/signup")
def presence_signup(req: SignupRequest):
    try:
        user = db.create_user(req.email, req.password)
        return {"token": user["token"], "email": user["email"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/presence/login")
def presence_login(req: LoginRequest):
    user = db.verify_login(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": user["token"], "email": user["email"]}

@app.post("/api/presence/provision")
def presence_provision_endpoint(req: ProvisionRequest, request: Request):
    user = get_current_user(request)
    try:
        headscale_username = "presence-user-" + str(user["id"])
        result = presence_provision.provision_presence(headscale_username, req.q3)
        db.set_headscale_username(user["id"], headscale_username)
        db.save_persona(user["id"], req.q1, req.q2, req.q3, req.q4, req.q5, result["exit_node"])
        return {
            "status": "provisioned",
            "headscale_username": headscale_username,
            "exit_node": result["exit_node"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presence/status")
def presence_status(request: Request):
    user = get_current_user(request)
    persona = db.get_latest_persona(user["id"])
    if not persona:
        return {"provisioned": False}
    return {
        "provisioned": True,
        "email": user["email"],
        "headscale_username": user["headscale_username"],
        "goal": persona["q1"],
        "devices": persona["q2"],
        "home": persona["q3"],
        "presented_as": persona["q4"],
        "skill_level": persona["q5"],
        "exit_node": persona["exit_node"],
        "built_at": persona["built_at"]
    }

# Client-facing enrollment + Lens routes.
# MUST be registered before the static mount below — the catch-all "/" mount
# swallows any route added after it.
app.include_router(presence_enroll_api.router)
app.include_router(home_egress_api.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")
