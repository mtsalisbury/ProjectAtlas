import subprocess
import json
from datetime import datetime, timezone

def get_nodes():
    result = subprocess.run(
        ["docker", "exec", "headscale", "headscale", "nodes", "list", "--output", "json"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError(f"headscale command failed: {result.stderr}")

    raw_nodes = json.loads(result.stdout)
    nodes = []
    for n in raw_nodes:
        last_seen = None
        if n.get("last_seen"):
            last_seen = datetime.fromtimestamp(
                n["last_seen"]["seconds"], tz=timezone.utc
            ).isoformat()

        nodes.append({
            "id": n["id"],
            "name": n.get("given_name", n.get("name")),
            "context": n.get("user", {}).get("name"),
            "ip_addresses": n.get("ip_addresses", []),
            "online": n.get("online", False),
            "last_seen": last_seen,
            "routes": n.get("approved_routes", []),
            "serving_routes": n.get("subnet_routes", []),
        })
    return nodes

def expire_node(node_id: int):
    result = subprocess.run(
        ["docker", "exec", "headscale", "headscale", "nodes", "expire", "-i", str(node_id)],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError(f"headscale expire failed: {result.stderr}")
    return True
