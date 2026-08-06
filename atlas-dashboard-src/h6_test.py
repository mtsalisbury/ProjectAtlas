import json
from datetime import datetime, timezone
from pathlib import Path
import headscale

LOG_DIR = Path("/opt/atlas-dashboard/logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "h6_runs.jsonl"

def snapshot(node_id: int, label: str, network: dict):
    """Capture identity (Headscale) + client-provided network state."""
    nodes = headscale.get_nodes()
    node = next((n for n in nodes if n["id"] == node_id), None)
    if node is None:
        raise ValueError(f"No node with id {node_id}")

    return {
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "identity": {
            "node_id": node["id"],
            "name": node["name"],
            "context": node["context"],
            "mesh_ip": node["ip_addresses"][0] if node["ip_addresses"] else None,
        },
        "network": network,
    }

def compare(snap_a: dict, snap_b: dict):
    """Diff two snapshots: identity must match, network must differ."""
    identity_match = snap_a["identity"] == snap_b["identity"]
    network_changed = snap_a["network"] != snap_b["network"]

    result = {
        "snapshot_a": snap_a,
        "snapshot_b": snap_b,
        "identity_match": identity_match,
        "network_changed": network_changed,
        "passed": identity_match and network_changed,
        "compared_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result
