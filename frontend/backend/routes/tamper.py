from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from database.mongodb import db
from utils.jwt import get_current_user
from services.tamper_detection import analyze_tamper

router = APIRouter()


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    screening_id: str = "",
    current_user: dict = Depends(get_current_user)
):
    allowed_types = [
        "image/jpeg",
        "image/png"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG files are allowed."
        )

    if not screening_id:
        raise HTTPException(
            status_code=400,
            detail="screening_id is required."
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Send image to Tamper Detection service
    response = await analyze_tamper(
        file_bytes=file_bytes,
        filename=file.filename or "document.jpg",
        content_type=file.content_type or "image/jpeg"
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    result = response.json()

    # Make sure the screening exists
    screening = await db.screenings.find_one({
        "screening_id": screening_id
    })

    if not screening:
        raise HTTPException(
            status_code=404,
            detail="Screening not found."
        )

    # Save tamper analysis result in MongoDB
    await db.screenings.update_one(
        {
            "screening_id": screening_id
        },
        {
            "$set": {
                "tamper_analysis": {
                    "prediction": result.get("prediction"),
                    "tamper_probability": result.get(
                        "tamper_probability"
                    ),
                    "genuine_probability": result.get(
                        "genuine_probability"
                    ),
                    "threshold": result.get("threshold"),
                    "raw_model_output": result.get(
                        "raw_model_output"
                    )
                }
            }
        }
    )

    return {
        "success": True,
        "screening_id": screening_id,
        "filename": file.filename,
        "tamper_analysis": result
    }