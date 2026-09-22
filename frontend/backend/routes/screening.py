import uuid
import hashlib
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Depends,
)

from database.mongodb import db
from models.screening import ScreeningCreate
from services.blockchain import create_ledger_event
from utils.jwt import get_current_user


router = APIRouter(
    prefix="/api/screening",
    tags=["Screening"]
)


# =====================================================
# DOCUMENT UPLOAD
# =====================================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):

    allowed_types = [
        "image/jpeg",
        "image/png",
        "application/pdf",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and PDF files are allowed."
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    document_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    screening_id = (
        f"SCR-{uuid.uuid4().hex[:8].upper()}"
    )

    screening = {
        "screening_id": screening_id,
        "filename": file.filename,
        "document_hash": document_hash,
        "content_type": file.content_type,
        "status": "CREATED",
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["username"],
    }

    await db.screenings.insert_one(screening)

    await create_ledger_event(
        screening_id=screening_id,
        event_type="SCREENING_CREATED",
        document_hash=document_hash,
        created_by=current_user["username"],
    )

    return {
        "success": True,
        "scan_id": screening_id,
        "screening_id": screening_id,
        "filename": file.filename,
        "document_hash": document_hash,
        "status": "CREATED",
        "created_by": current_user["username"],
    }


# =====================================================
# CREATE SCREENING
# =====================================================

@router.post("/create")
async def create_screening(
    data: ScreeningCreate,
    current_user: dict = Depends(get_current_user)
):

    screening_id = (
        f"SCR-{uuid.uuid4().hex[:8].upper()}"
    )

    screening = {
        "screening_id": screening_id,
        "filename": data.filename,
        "document_hash": data.document_hash,
        "status": "CREATED",
        "created_at": datetime.now(timezone.utc),
        "created_by": current_user["username"],
    }

    await db.screenings.insert_one(screening)

    await create_ledger_event(
        screening_id=screening_id,
        event_type="SCREENING_CREATED",
        document_hash=data.document_hash,
        created_by=current_user["username"],
    )

    return {
        "success": True,
        "scan_id": screening_id,
        "screening_id": screening_id,
        "filename": data.filename,
        "document_hash": data.document_hash,
        "status": "CREATED",
        "created_by": current_user["username"],
    }


# =====================================================
# SCREENING STATS
# =====================================================

@router.get("/stats")
async def get_screening_stats(
    current_user: dict = Depends(get_current_user)
):

    total_screenings = await db.screenings.count_documents({})

    clear_count = await db.screenings.count_documents({
        "status": "CLEAR"
    })

    review_count = await db.screenings.count_documents({
        "status": "REVIEW"
    })

    rejected_count = await db.screenings.count_documents({
        "status": "REJECTED"
    })

    return {
        "total_screenings": total_screenings,
        "clear": clear_count,
        "review": review_count,
        "rejected": rejected_count
    }


# =====================================================
# OFFICER DECISION
# =====================================================

@router.post("/{screening_id}/decision")
async def submit_screening_decision(
    screening_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):

    # -----------------------------------------------
    # Validate decision
    # -----------------------------------------------

    decision = str(
        data.get("decision", "")
    ).upper().strip()

    allowed_decisions = [
        "CLEAR",
        "REVIEW",
        "REJECTED",
    ]

    if decision not in allowed_decisions:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid screening decision.",
                "allowed_decisions": allowed_decisions,
            }
        )

    # -----------------------------------------------
    # Find screening
    # -----------------------------------------------

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    # -----------------------------------------------
    # Prevent accidental repeated decision
    # -----------------------------------------------

    existing_decision = screening.get(
        "officer_decision"
    )

    if existing_decision:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "A final officer decision has already been recorded.",
                "decision": existing_decision.get("decision"),
                "decided_by": existing_decision.get("decided_by"),
                "decided_at": existing_decision.get("decided_at"),
            }
        )

    # -----------------------------------------------
    # Timestamp
    # -----------------------------------------------

    decided_at = datetime.now(timezone.utc)

    username = current_user.get(
        "username",
        "unknown"
    )

    # -----------------------------------------------
    # Store decision
    # -----------------------------------------------

    officer_decision = {
        "decision": decision,
        "decided_by": username,
        "decided_at": decided_at,
    }

    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "status": decision,
                "officer_decision": officer_decision,
            }
        }
    )

    # -----------------------------------------------
    # Blockchain / audit ledger
    # -----------------------------------------------

    event_type = (
        "SCREENING_CLEARED"
        if decision == "CLEAR"
        else "SCREENING_REVIEW"
        if decision == "REVIEW"
        else "SCREENING_REJECTED"
    )

    await create_ledger_event(
        screening_id=screening_id,
        event_type=event_type,
        document_hash=screening.get(
            "document_hash"
        ),
        created_by=username,
    )

    # -----------------------------------------------
    # Response
    # -----------------------------------------------

    return {
        "success": True,
        "screening_id": screening_id,
        "decision": decision,
        "decided_by": username,
        "decided_at": decided_at,
        "message": (
            "Screening cleared."
            if decision == "CLEAR"
            else "Screening sent for secondary inspection."
            if decision == "REVIEW"
            else "Screening rejected."
        ),
    }


# =====================================================
# GET COMPLETE SCREENING
# =====================================================

@router.get("/{screening_id}")
async def get_screening(
    screening_id: str,
    current_user: dict = Depends(get_current_user)
):

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    # -------------------------------------------------
    # Return complete screening information
    #
    # Important:
    # The previous version only returned basic metadata.
    # This version also returns:
    #
    # - tamper_analysis
    # - pipeline
    # - OCR
    # - MRZ
    # - anomaly
    # - identity validation
    # - identity linkage
    # - face
    # - risk
    # - officer decision
    # -------------------------------------------------

    return {
        "screening_id": screening.get(
            "screening_id"
        ),

        "scan_id": screening.get(
            "screening_id"
        ),

        "filename": screening.get(
            "filename"
        ),

        "document_hash": screening.get(
            "document_hash"
        ),

        "content_type": screening.get(
            "content_type"
        ),

        "status": screening.get(
            "status"
        ),

        "created_at": screening.get(
            "created_at"
        ),

        "created_by": screening.get(
            "created_by"
        ),

        # ---------------------------------------------
        # Pipeline
        # ---------------------------------------------

        "pipeline": screening.get(
            "pipeline"
        ),

        # ---------------------------------------------
        # Tamper
        # ---------------------------------------------

        "tamper": screening.get(
            "tamper_analysis"
        ),

        "tamper_analysis": screening.get(
            "tamper_analysis"
        ),

        # ---------------------------------------------
        # OCR / MRZ
        # ---------------------------------------------

        "ocr": screening.get(
            "ocr"
        ),

        "ocr_result": screening.get(
            "ocr_result"
        ),

        "mrz": screening.get(
            "mrz"
        ),

        # ---------------------------------------------
        # Anomaly
        # ---------------------------------------------

        "anomaly": screening.get(
            "anomaly"
        ),

        "anomaly_analysis": screening.get(
            "anomaly_analysis"
        ),

        # ---------------------------------------------
        # Identity Validation
        # ---------------------------------------------

        "identity_validation": screening.get(
            "identity_validation"
        ),

        # ---------------------------------------------
        # Identity Linkage
        # ---------------------------------------------

        "identity_data": screening.get(
            "identity_data"
        ),

        "identity_hash": screening.get(
            "identity_hash"
        ),

        "identity_linkage": screening.get(
            "identity_linkage"
        ),

        # ---------------------------------------------
        # Face
        # ---------------------------------------------

        "face": screening.get(
            "face"
        ),

        "face_analysis": screening.get(
            "face_analysis"
        ),

        # ---------------------------------------------
        # Risk
        # ---------------------------------------------

        "risk": screening.get(
            "risk"
        ),

        # ---------------------------------------------
        # Officer decision
        # ---------------------------------------------

        "officer_decision": screening.get(
            "officer_decision"
        ),
    }