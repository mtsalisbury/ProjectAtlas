import json
import time
from datetime import datetime, timezone
from pathlib import Path

import headscale

LOG_DIR = Path("/opt/atlas-dashboard/logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "h5_runs.jsonl"

def run_recovery_test(target_node_id: int):
    before = headscale.get_nodes()
    before_map = {n["id"]: n for n in before}

    if target_node_id not in before_map:
        raise ValueError(f"Node {target_node_id} not found")

    headscale.expire_node(target_node_id)
    time.sleep(2)

    after = headscale.get_nodes()
    after_map = {n["id"]: n for n in after}

    others_unaffected = True
    other_diffs = []
    for nid, b in before_map.items():
        if nid == target_node_id:
            continue
        a = after_map.get(nid)
        if a is None:
            others_unaffected = False
            other_diffs.append({"id": nid, "issue": "node missing after expiry"})
            continue
        if a["online"] != b["online"] or a["ip_addresses"] != b["ip_addresses"] or a["context"] != b["context"]:
            others_unaffected = False
            other_diffs.append({
                "id": nid, "name": a.get("name"),
                "before": {"online": b["online"], "ip_addresses": b["ip_addresses"], "context": b["context"]},
                "after": {"online": a["online"], "ip_addresses": a["ip_addresses"], "context": a["context"]},
            })

    result = {
        "target_node_id": target_node_id,
        "target_before": before_map[target_node_id],
        "target_after": after_map.get(target_node_id),
        "others_unaffected": others_unaffected,
        "other_diffs": other_diffs,
        "passed": others_unaffected,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result
