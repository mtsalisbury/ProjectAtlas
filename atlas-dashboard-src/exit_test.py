import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("/opt/atlas-dashboard/logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "exit_node_runs.jsonl"

KNOWN_EXIT_IPS = {
    "EGR-Lon1": "144.126.200.88",
    "EGR-Tor1": "134.122.41.187",
}

def check(exit_node: str, observed_ip: str):
    expected = KNOWN_EXIT_IPS.get(exit_node)
    if expected is None:
        raise ValueError(f"Unknown exit node: {exit_node}")

    result = {
        "exit_node": exit_node,
        "expected_ip": expected,
        "observed_ip": observed_ip,
        "passed": observed_ip == expected,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result
