from datetime import datetime, timezone

from database.mongodb import db
from utils.hashing import sha256_hash


async def create_ledger_event(
    screening_id: str,
    event_type: str,
    identity_hash: str | None = None,
    document_hash: str | None = None,
    created_by: str | None = None,
):
    previous_event = await db.ledger.find_one(
        {},
        sort=[("timestamp", -1)]
    )

    previous_hash = (
        previous_event["event_hash"]
        if previous_event
        else None
    )

    timestamp = datetime.now(timezone.utc)

    event_data = {
        "screening_id": screening_id,
        "event_type": event_type,
        "identity_hash": identity_hash,
        "document_hash": document_hash,
        "previous_hash": previous_hash,
        "timestamp": timestamp.isoformat(),
        "created_by": created_by,
    }

    event_hash = sha256_hash(event_data)

    ledger_event = {
        **event_data,
        "event_hash": event_hash,
    }

    result = await db.ledger.insert_one(ledger_event)

    ledger_event["_id"] = str(result.inserted_id)

    return ledger_event


async def get_ledger_events():
    events = []

    cursor = db.ledger.find(
        {}
    ).sort("timestamp", 1)

    async for event in cursor:
        event["_id"] = str(event["_id"])
        events.append(event)

    return events


async def verify_ledger_chain():
    events = await get_ledger_events()

    if not events:
        return {
            "valid": True,
            "chain_length": 0,
            "message": "Ledger is empty"
        }

    previous_hash = None

    for index, event in enumerate(events):

        if event.get("previous_hash") != previous_hash:
            return {
                "valid": False,
                "chain_length": len(events),
                "broken_at_index": index,
                "reason": "Previous hash mismatch"
            }

        event_data = {
            "screening_id": event["screening_id"],
            "event_type": event["event_type"],
            "identity_hash": event.get("identity_hash"),
            "document_hash": event.get("document_hash"),
            "previous_hash": event.get("previous_hash"),
            "timestamp": (
                event["timestamp"].isoformat()
                if hasattr(event["timestamp"], "isoformat")
                else event["timestamp"]
            ),
            "created_by": event.get("created_by"),
        }

        calculated_hash = sha256_hash(event_data)

        if event.get("event_hash") != calculated_hash:
            return {
                "valid": False,
                "chain_length": len(events),
                "broken_at_index": index,
                "reason": "Event hash mismatch"
            }

        previous_hash = event["event_hash"]

    return {
        "valid": True,
        "chain_length": len(events),
        "message": "Ledger chain verified successfully"
    }
