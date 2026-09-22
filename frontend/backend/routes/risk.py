import os

from fastapi import APIRouter, Depends, HTTPException
import httpx

from database.mongodb import db
from utils.jwt import get_current_user


router = APIRouter(
    prefix="/api/risk",
    tags=["Risk"]
)


RISK_SERVICE_URL = os.getenv(
    "RISK_SERVICE_URL",
    "http://127.0.0.1:8001"
)

RISK_CALIBRATION_URL = (
    f"{RISK_SERVICE_URL}/api/risk/calibrate"
)


@router.post("/calibrate")
async def calibrate_risk(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Send model outputs from the main backend
    to the separate Risk Calibration service.
    """

    required_fields = [
        "screening_id",
        "ocr_confidence",
        "mrz_confidence",
        "tamper_probability",
        "anomaly_probability",
        "face_match_probability",
        "watchlist_probability",
        "identity_linkage_score",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required risk input fields",
                "missing_fields": missing_fields
            }
        )

    screening_id = data["screening_id"]

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    try:
        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                RISK_CALIBRATION_URL,
                json=data
            )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Risk Calibration service is unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Risk Calibration service returned an error",
                "service_status": response.status_code
            }
        )

    risk_result = response.json()

    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "risk": risk_result,
                "status": "RISK_CALCULATED",
                "risk_calculated_by": current_user["username"],
            }
        }
    )

    return {
        "success": True,
        "screening_id": screening_id,
        "risk": risk_result,
        "calculated_by": current_user["username"],
    }


@router.post("/calibrate-from-screening/{screening_id}")
async def calibrate_from_screening(
    screening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically obtain the identity linkage score
    and anomaly score from an existing screening,
    then send them to the Risk Calibration service.
    """

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    # -----------------------------------------
    # 1. Get Identity Linkage Score
    # -----------------------------------------

    identity_linkage = screening.get(
        "identity_linkage"
    )

    if not identity_linkage:
        raise HTTPException(
            status_code=400,
            detail="Identity linkage has not been performed yet"
        )

    identity_linkage_score = identity_linkage.get(
        "linkage_score"
    )

    if identity_linkage_score is None:
        raise HTTPException(
            status_code=400,
            detail="Identity linkage score is missing"
        )

    # -----------------------------------------
    # 2. Get Anomaly Screening Result
    # -----------------------------------------

    anomaly = (
        screening.get("anomaly")
        or screening.get("anomaly_analysis")
    )

    if not anomaly:
        raise HTTPException(
            status_code=400,
            detail="Anomaly screening has not been performed yet"
        )

    anomaly_score = anomaly.get(
        "anomaly_score"
    )

    if anomaly_score is None:
        raise HTTPException(
            status_code=400,
            detail="Anomaly score is missing from screening result"
        )

    # -----------------------------------------
    # 3. Build Risk Calibration Input
    # -----------------------------------------

    risk_input = {
        "screening_id": screening_id,
        "ocr_confidence": 1.0,
        "mrz_confidence": 1.0,
        "tamper_probability": 0.0,
        "anomaly_probability": float(anomaly_score),
        "face_match_probability": 1.0,
        "watchlist_probability": 0.0,
        "identity_linkage_score": float(identity_linkage_score)
    }

    # -----------------------------------------
    # 4. Call Risk Calibration Service
    # -----------------------------------------

    try:
        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                RISK_CALIBRATION_URL,
                json=risk_input
            )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Risk Calibration service is unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Risk Calibration service returned an error",
                "service_status": response.status_code,
                "service_response": response.text
            }
        )

    try:
        risk_result = response.json()

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Risk Calibration service returned invalid JSON"
        )

    # -----------------------------------------
    # 5. Store Risk Result in MongoDB
    # -----------------------------------------

    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "risk": risk_result,
                "risk_input": risk_input,
                "status": "RISK_CALCULATED",
                "risk_calculated_by": current_user["username"]
            }
        }
    )

    # -----------------------------------------
    # 6. Return Result
    # -----------------------------------------

    return {
        "success": True,
        "screening_id": screening_id,
        "identity_linkage_score": float(identity_linkage_score),
        "anomaly_probability": float(anomaly_score),
        "risk_input": risk_input,
        "risk": risk_result,
        "calculated_by": current_user["username"]
    }


@router.get("/{screening_id}")
async def get_risk_result(
    screening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve the stored risk result for a screening.
    """

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found"
        )

    risk = screening.get("risk")

    if not risk:
        raise HTTPException(
            status_code=404,
            detail="Risk assessment has not been calculated yet"
        )

    return {
        "success": True,
        "screening_id": screening_id,
        "risk": risk,
        "status": screening.get("status"),
        "calculated_by": screening.get("risk_calculated_by")
    }