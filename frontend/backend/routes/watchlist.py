from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from database.mongodb import db


router = APIRouter(
    prefix="/api/watchlist",
    tags=["Watchlist / Blacklist"]
)


# =========================================================
# HELPERS
# =========================================================

def normalize(value: Optional[str]) -> str:
    if not value:
        return ""

    return " ".join(
        value.strip().upper().split()
    )


def calculate_match(
    extracted: dict,
    record: dict
):
    matched_fields = []

    extracted_name = normalize(
        extracted.get("name")
    )

    record_name = normalize(
        record.get("name")
    )

    extracted_dob = normalize(
        extracted.get("date_of_birth")
    )

    record_dob = normalize(
        record.get("date_of_birth")
    )

    extracted_document = normalize(
        extracted.get("document_number")
    )

    record_document = normalize(
        record.get("document_number")
    )

    extracted_nationality = normalize(
        extracted.get("nationality")
    )

    record_nationality = normalize(
        record.get("nationality")
    )


    # =====================================================
    # NAME
    # =====================================================

    if (
        extracted_name
        and record_name
        and extracted_name == record_name
    ):
        matched_fields.append("name")


    # =====================================================
    # DATE OF BIRTH
    # =====================================================

    if (
        extracted_dob
        and record_dob
        and extracted_dob == record_dob
    ):
        matched_fields.append("date_of_birth")


    # =====================================================
    # DOCUMENT NUMBER
    # =====================================================

    if (
        extracted_document
        and record_document
        and extracted_document == record_document
    ):
        matched_fields.append("document_number")


    # =====================================================
    # NATIONALITY
    # =====================================================

    if (
        extracted_nationality
        and record_nationality
        and extracted_nationality == record_nationality
    ):
        matched_fields.append("nationality")


    # =====================================================
    # SCORE
    # =====================================================

    score = 0.0

    if "name" in matched_fields:
        score += 0.40

    if "date_of_birth" in matched_fields:
        score += 0.20

    if "document_number" in matched_fields:
        score += 0.30

    if "nationality" in matched_fields:
        score += 0.10


    return score, matched_fields


# =========================================================
# CHECK WATCHLIST
# =========================================================

@router.post(
    "/check/{screening_id}"
)
async def check_watchlist(
    screening_id: str
):

    # -----------------------------------------------------
    # Find screening
    # -----------------------------------------------------

    screening = await db.screenings.find_one(
        {
            "screening_id": screening_id
        }
    )

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )


    # -----------------------------------------------------
    # Get identity information
    # -----------------------------------------------------

    extracted = screening.get(
        "extracted_fields",
        {}
    )


    # Try OCR data
    if not extracted:

        extracted = screening.get(
            "ocr_data",
            {}
        )


    # Try identity data
    if not extracted:

        extracted = screening.get(
            "identity",
            {}
        )


    # -----------------------------------------------------
    # Extract watchlist fields
    # -----------------------------------------------------

    name = extracted.get("name")

    date_of_birth = extracted.get(
        "date_of_birth"
    )

    document_number = extracted.get(
        "document_number"
    )

    nationality = extracted.get(
        "nationality"
    )


    # -----------------------------------------------------
    # If identity data is unavailable
    # -----------------------------------------------------

    if not any(
        [
            name,
            date_of_birth,
            document_number,
            nationality
        ]
    ):

        result = {
            "status": "PENDING",
            "match_found": False,
            "match_type": None,
            "match_score": 0.0,
            "matched_fields": [],
            "record_id": None,
            "message": (
                "Identity information is not "
                "available for watchlist screening."
            )
        }

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "watchlist": {
                        **result,
                        "checked_at": datetime.now(
                            timezone.utc
                        )
                    }
                }
            }
        )

        return {
            "screening_id": screening_id,
            **result
        }


    # =====================================================
    # SEARCH ACTIVE WATCHLIST RECORDS
    # =====================================================

    records = db.watchlist_records.find(
        {
            "status": "ACTIVE"
        }
    )

    best_match = None
    best_score = 0.0
    best_fields = []


    async for record in records:

        score, matched_fields = calculate_match(
            extracted,
            record
        )

        if score > best_score:

            best_score = score

            best_match = record

            best_fields = matched_fields


    # =====================================================
    # DETERMINE RESULT
    # =====================================================

    if best_score >= 0.70:

        status = "MATCH"

        match_found = True

        match_type = "CONFIRMED_MATCH"

        message = (
            "A matching authorized watchlist "
            "record was found."
        )


    elif best_score >= 0.40:

        status = "POTENTIAL_MATCH"

        match_found = True

        match_type = "POTENTIAL_MATCH"

        message = (
            "A potential watchlist match "
            "requires officer review."
        )


    else:

        status = "NO_MATCH"

        match_found = False

        match_type = None

        message = (
            "No matching authorized watchlist "
            "record was found."
        )


    # =====================================================
    # RECORD ID
    # =====================================================

    record_id = None

    if best_match:

        record_id = best_match.get(
            "record_id"
        )


    # =====================================================
    # STORE RESULT
    # =====================================================

    result = {
        "status": status,
        "match_found": match_found,
        "match_type": match_type,
        "match_score": round(
            best_score,
            4
        ),
        "matched_fields": best_fields,
        "record_id": record_id,
        "message": message,
        "checked_at": datetime.now(
            timezone.utc
        )
    }


    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "watchlist": result
            }
        }
    )


    return {
        "screening_id": screening_id,
        **result
    }


# =========================================================
# GET WATCHLIST RESULT
# =========================================================

@router.get(
    "/result/{screening_id}"
)
async def get_watchlist_result(
    screening_id: str
):

    # IMPORTANT:
    # Include screening_id in the projection.
    #
    # Previously only "watchlist" was projected.
    # If watchlist did not exist yet, MongoDB returned
    # an empty dictionary {}, which Python treated as False.
    # That caused the incorrect "Screening not found" error.

    screening = await db.screenings.find_one(
        {
            "screening_id": screening_id
        },
        {
            "_id": 0,
            "screening_id": 1,
            "watchlist": 1
        }
    )


    if screening is None:

        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )


    watchlist = screening.get(
        "watchlist"
    )


    # -----------------------------------------------------
    # Watchlist has not run yet
    # -----------------------------------------------------

    if not watchlist:

        return {
            "screening_id": screening_id,
            "status": "PENDING",
            "match_found": False,
            "match_type": None,
            "match_score": 0.0,
            "matched_fields": [],
            "record_id": None,
            "message": (
                "Watchlist screening has "
                "not been performed yet."
            )
        }


    # -----------------------------------------------------
    # Existing watchlist result
    # -----------------------------------------------------

    return {
        "screening_id": screening_id,
        **watchlist
    }