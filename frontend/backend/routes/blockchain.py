from fastapi import APIRouter, HTTPException

from services.blockchain import (
    create_ledger_event,
    get_ledger_events,
    verify_ledger_chain,
)

from services.identity_linkage import generate_identity_hash


router = APIRouter(
    prefix="/api/blockchain",
    tags=["Blockchain Ledger"],
)


# ==========================================================
# VERIFY BLOCKCHAIN / LEDGER CHAIN
# ==========================================================

@router.get("/verify")
async def verify_chain():
    """
    Verify the integrity of the blockchain-style audit ledger.
    """

    return await verify_ledger_chain()


# ==========================================================
# GET LEDGER EVENTS
# ==========================================================

@router.get("/ledger")
async def get_ledger():
    """
    Return all blockchain audit ledger events.
    """

    return await get_ledger_events()


# ==========================================================
# CREATE LEDGER EVENT
# ==========================================================

@router.post("/event")
async def add_ledger_event(event: dict):
    """
    Create a new blockchain audit event.

    Required:
        screening_id
        event_type

    Optional:
        identity_hash
        document_hash
        created_by
    """

    required_fields = [
        "screening_id",
        "event_type",
    ]

    for field in required_fields:

        if field not in event:

            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}",
            )

    return await create_ledger_event(
        screening_id=event["screening_id"],
        event_type=event["event_type"],
        identity_hash=event.get("identity_hash"),
        document_hash=event.get("document_hash"),
        created_by=event.get("created_by"),
    )


# ==========================================================
# LINK IDENTITY TO LEDGER
# ==========================================================

@router.post("/link-identity")
async def link_identity_to_ledger(data: dict):
    """
    Generate an identity hash and store an
    IDENTITY_LINKED event in the blockchain ledger.
    """

    if "screening_id" not in data:

        raise HTTPException(
            status_code=400,
            detail="Missing screening_id",
        )

    if "identity_data" not in data:

        raise HTTPException(
            status_code=400,
            detail="Missing identity_data",
        )

    identity_hash = generate_identity_hash(
        data["identity_data"]
    )

    return await create_ledger_event(
        screening_id=data["screening_id"],
        event_type="IDENTITY_LINKED",
        identity_hash=identity_hash,
        document_hash=data.get("document_hash"),
        created_by=data.get("created_by"),
    )