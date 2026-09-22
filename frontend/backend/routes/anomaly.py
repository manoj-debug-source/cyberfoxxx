from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Depends,
)
import httpx

from database.mongodb import db
from utils.jwt import get_current_user
from services.anomaly_detection import analyze_anomaly


router = APIRouter()


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    screening_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Forward the document to the external
    Document Screening & Anomaly Detection service.

    The returned result is also stored inside
    the corresponding CYBERFOXXX screening.
    """

    # -------------------------------------------------
    # Validate file type
    # -------------------------------------------------

    allowed_types = [
        "image/jpeg",
        "image/png",
        "application/pdf"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and PDF files are allowed."
        )

    # -------------------------------------------------
    # Verify screening exists
    # -------------------------------------------------

    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found."
        )

    # -------------------------------------------------
    # Read uploaded file
    # -------------------------------------------------

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # -------------------------------------------------
    # Call external Document Screening service
    # -------------------------------------------------

    try:
        response = await analyze_anomaly(
            file_bytes=file_bytes,
            filename=file.filename or "document",
            content_type=file.content_type
            or "application/octet-stream"
        )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Anomaly Detection service unavailable: {str(e)}"
        )

    # -------------------------------------------------
    # Handle external service errors
    # -------------------------------------------------

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Anomaly Detection service returned an error",
                "service_status": response.status_code,
                "service_response": response.text
            }
        )

    # -------------------------------------------------
    # Parse response
    # -------------------------------------------------

    try:
        result = response.json()

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Anomaly Detection service returned invalid JSON."
        )

    # -------------------------------------------------
    # Store anomaly result in MongoDB
    # -------------------------------------------------

    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "anomaly": result,
                "anomaly_analysis": result,
                "anomaly_processed_by": current_user.get(
                    "username"
                ),
                "status": "ANOMALY_COMPLETED"
            }
        }
    )

    # -------------------------------------------------
    # Response
    # -------------------------------------------------

    return {
        "success": True,
        "screening_id": screening_id,
        "filename": file.filename,
        "processed_by": current_user.get("username"),
        "anomaly_result": result
    }