
import hashlib
import json
from pathlib import Path


STATE_DIR = Path("state") / "ticket_snapshots"


def canonical_json(data):
    """Serialize data consistently for reliable comparison."""
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def ticket_hash(ticket):
    """Calculate a fingerprint of the relevant Jira ticket fields."""
    relevant_fields = {
        "issue_key": ticket.get("issue_key"),
        "summary": ticket.get("summary"),
        "description": ticket.get("description"),
        "issue_type": ticket.get("issue_type"),
        "labels": ticket.get("labels", []),
    }

    serialized = canonical_json(relevant_fields)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def snapshot_path(issue_key):
    """Return the snapshot path for a Jira issue."""
    safe_key = "".join(
        char for char in issue_key
        if char.isalnum() or char in "-_"
    )

    if not safe_key:
        raise ValueError("Invalid Jira issue key")

    return STATE_DIR / f"{safe_key}.json"


def detect_ticket_change(ticket):
    """
    Compare the latest ticket with its last successfully processed snapshot.

    Returns: new, unchanged, or changed.
    """
    path = snapshot_path(ticket["issue_key"])
    current_hash = ticket_hash(ticket)

    if not path.exists():
        return {
            "status": "new",
            "previous": None,
            "current_hash": current_hash,
        }

    with path.open("r", encoding="utf-8") as file:
        previous = json.load(file)

    if previous.get("hash") == current_hash:
        status = "unchanged"
    else:
        status = "changed"

    return {
        "status": status,
        "previous": previous.get("ticket"),
        "current_hash": current_hash,
    }



import hashlib
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = PROJECT_ROOT / "state" / "ticket_snapshots"


def _ticket_fingerprint(ticket):
    """Create a stable hash of the relevant Jira ticket content."""

    relevant = {
        "issue_key": ticket.get("issue_key"),
        "summary": ticket.get("summary"),
        "description": ticket.get("description"),
        "labels": sorted(ticket.get("labels", [])),
    }

    content = json.dumps(
        relevant,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def detect_ticket_change(ticket):
    """Determine whether a Jira ticket is new, changed, or unchanged."""

    issue_key = ticket.get("issue_key")

    if not issue_key:
        raise ValueError("Ticket is missing issue_key")

    snapshot_path = STATE_DIR / f"{issue_key}.json"

    if not snapshot_path.exists():
        return {"status": "new", "issue_key": issue_key}

    previous = json.loads(snapshot_path.read_text(encoding="utf-8"))
    current_hash = _ticket_fingerprint(ticket)

    if previous.get("fingerprint") == current_hash:
        return {"status": "unchanged", "issue_key": issue_key}

    return {"status": "changed", "issue_key": issue_key}


def save_ticket_snapshot(ticket):
    """Save the ticket fingerprint after successful PR publication."""

    issue_key = ticket.get("issue_key")

    if not issue_key:
        raise ValueError("Ticket is missing issue_key")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "issue_key": issue_key,
        "fingerprint": _ticket_fingerprint(ticket),
    }

    path = STATE_DIR / f"{issue_key}.json"
    path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
