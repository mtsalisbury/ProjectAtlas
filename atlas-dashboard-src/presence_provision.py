import json
import subprocess
import re
from pathlib import Path

ACL_PATH = Path("/root/atlas-mesh/config/acl.hujson")

EXIT_NODE_MAP = {
    "toronto": "EGR-Tor1",
    "ontario": "EGR-Tor1",
    "canada": "EGR-Tor1",
    "london": "EGR-Lon1",
    "uk": "EGR-Lon1",
    "united kingdom": "EGR-Lon1",
    "england": "EGR-Lon1",
}
DEFAULT_EXIT_NODE = "EGR-Tor1"

def match_exit_node(home_address: str) -> str:
    lowered = home_address.lower()
    for keyword, node in EXIT_NODE_MAP.items():
        if keyword in lowered:
            return node
    return DEFAULT_EXIT_NODE

def create_headscale_user(username: str):
    result = subprocess.run(
        ["docker", "exec", "headscale", "headscale", "users", "create", username],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0 and "already exists" not in result.stderr.lower():
        raise RuntimeError("failed to create headscale user: " + result.stderr)
    return True

def add_user_to_personal_group(headscale_username: str):
    with open(ACL_PATH) as f:
        raw = f.read()

    policy = json.loads(raw)
    member = headscale_username + "@"

    if member not in policy["groups"]["group:personal"]:
        policy["groups"]["group:personal"].append(member)

    new_raw = json.dumps(policy, indent=2)

    tmp_path = ACL_PATH.parent / "acl.hujson.tmp"
    with open(tmp_path, "w") as f:
        f.write(new_raw)

    test = subprocess.run(
        ["docker", "exec", "headscale", "headscale", "configtest"],
        capture_output=True, text=True, timeout=10
    )
    if test.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError("ACL validation failed, not applied: " + test.stderr)

    tmp_path.replace(ACL_PATH)

    reload = subprocess.run(
        ["docker", "restart", "headscale"],
        capture_output=True, text=True, timeout=30
    )
    if reload.returncode != 0:
        raise RuntimeError("headscale restart failed: " + reload.stderr)
    return True

def provision_presence(headscale_username: str, home_address: str):
    create_headscale_user(headscale_username)
    add_user_to_personal_group(headscale_username)
    exit_node = match_exit_node(home_address)
    return {"headscale_username": headscale_username, "exit_node": exit_node}
