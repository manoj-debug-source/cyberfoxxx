from fastapi import APIRouter, HTTPException, Depends

from database.mongodb import db
from services.identity_linkage import (
    normalize_identity,
    generate_identity_hash,
    compare_identity_fields,
)
from services.blockchain import create_ledger_event
from utils.jwt import get_current_user


router = APIRouter(
    prefix="/api/identity",
    tags=["Identity Linkage"]
)


@router.post("/link")
async def link_identity(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Link an officer-entered identity to an existing screening.

    Officer provides ONLY:
        - name
        - contact_number

    Backend automatically obtains:
        - screening_id
        - document_number
        - document_hash

    The identity is compared against previous screenings.

    On successful linkage:
        - identity_hash is stored
        - identity_data is stored
        - identity_linkage result is stored
        - pipeline.identity_linkage is marked COMPLETED
        - blockchain/audit event is created
    """

    # =========================================================
    # 1. Validate screening ID
    # =========================================================

    screening_id = data.get("screening_id")

    if not screening_id:
        raise HTTPException(
            status_code=400,
            detail="Missing screening_id"
        )

    screening_id = str(screening_id).strip()

    if not screening_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid screening_id"
        )

    # =========================================================
    # 2. Validate identity data
    # =========================================================

    identity_data = data.get("identity_data")

    if not isinstance(identity_data, dict):
        raise HTTPException(
            status_code=400,
            detail="identity_data must be an object"
        )

    # Officer can provide ONLY these fields
    name = identity_data.get("name")
    contact_number = identity_data.get("contact_number")

    if not name or not str(name).strip():
        raise HTTPException(
            status_code=400,
            detail="Name is required"
        )

    if not contact_number or not str(contact_number).strip():
        raise HTTPException(
            status_code=400,
            detail="Contact number is required"
        )

    name = str(name).strip()
    contact_number = str(contact_number).strip()

    # =========================================================
    # 3. Validate contact number
    # =========================================================

    cleaned_contact = (
        contact_number
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if cleaned_contact.startswith("+"):
        number_part = cleaned_contact[1:]
    else:
        number_part = cleaned_contact

    if not number_part.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Contact number must contain only digits"
        )

    if len(number_part) < 10 or len(number_part) > 15:
        raise HTTPException(
            status_code=400,
            detail="Contact number must contain 10 to 15 digits"
        )

    # =========================================================
    # 4. Find screening
    # =========================================================

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    # =========================================================
    # 5. Prevent duplicate linkage
    # =========================================================

    existing_linkage = screening.get("identity_linkage")

    if existing_linkage:
        raise HTTPException(
            status_code=409,
            detail="Identity has already been linked for this screening"
        )

    # =========================================================
    # 6. Obtain document number
    # =========================================================

    document_number = None

    # Location 1
    document_number = (
        screening.get("identity_data", {})
        .get("document_number")
    )

    # Location 2
    if not document_number:
        document_number = screening.get(
            "document_number"
        )

    # Location 3
    if not document_number:
        document_number = (
            screening.get("ocr", {})
            .get("document_number")
        )

    # Location 4
    if not document_number:
        document_number = (
            screening.get("pipeline", {})
            .get("ocr", {})
            .get("result", {})
            .get("document_number")
        )

    # Location 5
    if not document_number:
        document_number = (
            screening.get("pipeline", {})
            .get("ocr", {})
            .get("result", {})
            .get("fields", {})
            .get("document_number")
        )

    # =========================================================
    # 7. Obtain document hash
    # =========================================================

    document_hash = screening.get("document_hash")

    if not document_hash:

        document_hash = (
            screening.get("pipeline", {})
            .get("sha256", {})
            .get("document_hash")
        )

    if not document_hash:
        raise HTTPException(
            status_code=400,
            detail="Document hash is not available for this screening"
        )

    # =========================================================
    # 8. Build final identity data
    # =========================================================

    # IMPORTANT:
    #
    # Officer enters:
    #   - name
    #   - contact_number
    #
    # Backend obtains:
    #   - document_number
    #
    # DOB is intentionally NOT used.

    final_identity_data = {
        "name": name,
        "contact_number": cleaned_contact,
        "document_number": document_number,
    }

    # =========================================================
    # 9. Normalize identity
    # =========================================================

    normalized_identity = normalize_identity(
        final_identity_data
    )

    if not normalized_identity:
        raise HTTPException(
            status_code=400,
            detail="Identity data is empty after normalization"
        )

    # =========================================================
    # 10. Generate identity SHA-256 hash
    # =========================================================

    identity_hash = generate_identity_hash(
        normalized_identity
    )

    # =========================================================
    # 11. Compare against previous identities
    # =========================================================

    previous_screenings = []

    cursor = db.screenings.find({
        "screening_id": {
            "$ne": screening_id
        },
        "identity_data": {
            "$exists": True
        }
    })

    async for previous in cursor:

        previous_identity = previous.get(
            "identity_data",
            {}
        )

        if not isinstance(previous_identity, dict):
            continue

        comparison = compare_identity_fields(
            normalized_identity,
            previous_identity
        )

        previous_screenings.append({
            "screening_id": previous.get(
                "screening_id"
            ),
            "created_at": previous.get(
                "created_at"
            ),
            "created_by": previous.get(
                "created_by"
            ),
            "comparison": comparison
        })

    # =========================================================
    # 12. Find strongest previous match
    # =========================================================

    strongest_match = None

    for previous in previous_screenings:

        comparison = previous.get(
            "comparison",
            {}
        )

        score = comparison.get(
            "score",
            0.0
        )

        if (
            strongest_match is None
            or score
            > strongest_match["comparison"].get(
                "score",
                0.0
            )
        ):
            strongest_match = previous

    # =========================================================
    # 13. Determine linkage status
    # =========================================================

    if strongest_match is None:

        linkage_score = 0.0
        linkage_status = "NEW_IDENTITY"
        match_found = False

    else:

        linkage_score = strongest_match[
            "comparison"
        ].get(
            "score",
            0.0
        )

        match_found = linkage_score >= 0.80

        if linkage_score >= 0.90:

            linkage_status = "MATCHED"

        elif linkage_score >= 0.70:

            linkage_status = "POSSIBLE_MATCH"

        else:

            linkage_status = "NO_SIGNIFICANT_MATCH"

    # =========================================================
    # 14. Prepare previous match information
    # =========================================================

    previous_matches = []

    for previous in previous_screenings:

        comparison = previous.get(
            "comparison",
            {}
        )

        previous_matches.append({
            "screening_id": previous.get(
                "screening_id"
            ),
            "score": comparison.get(
                "score",
                0.0
            ),
            "evidence": comparison.get(
                "evidence",
                []
            )
        })

    # =========================================================
    # 15. Prepare identity linkage result
    # =========================================================

    identity_linkage_result = {
        "status": linkage_status,
        "match_found": match_found,
        "linkage_score": linkage_score,
        "previous_matches": previous_matches,
    }

    # =========================================================
    # 16. Store identity + COMPLETE pipeline stage
    # =========================================================

    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {

                # -------------------------------------------------
                # Final identity hash
                # -------------------------------------------------

                "identity_hash": identity_hash,

                # -------------------------------------------------
                # Normalized identity
                # -------------------------------------------------

                "identity_data": normalized_identity,

                # -------------------------------------------------
                # Identity linkage result
                # -------------------------------------------------

                "identity_linkage": {
                    "status": linkage_status,
                    "match_found": match_found,
                    "linkage_score": linkage_score,
                    "previous_matches": previous_matches,
                    "linked_by": current_user.get(
                        "username",
                        "unknown"
                    )
                },

                # -------------------------------------------------
                # IMPORTANT:
                # Update the actual pipeline stage.
                #
                # RiskAssessment.jsx reads this location.
                # -------------------------------------------------

                "pipeline.identity_linkage": {
                    "status": "COMPLETED",
                    "result": identity_linkage_result
                }
            }
        }
    )

    # =========================================================
    # 17. Create blockchain / audit ledger event
    # =========================================================

    await create_ledger_event(
        screening_id=screening_id,
        event_type="IDENTITY_LINKED",
        identity_hash=identity_hash,
        document_hash=document_hash,
        created_by=current_user.get(
            "username",
            "unknown"
        ),
    )

    # =========================================================
    # 18. Return result
    # =========================================================

    return {
        "success": True,

        "screening_id": screening_id,

        "event_type": "IDENTITY_LINKED",

        "identity_hash": identity_hash,

        "document_hash": document_hash,

        "identity_linkage": identity_linkage_result,

        "pipeline": {
            "identity_linkage": {
                "status": "COMPLETED",
                "result": identity_linkage_result
            }
        },

        "created_by": current_user.get(
            "username",
            "unknown"
        )
    }