import os
import httpx

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

WINDOWS_AI_URL = os.getenv(
    "WINDOWS_AI_URL",
    "http://192.168.1.100:9000"
)


@router.post("/scan/document")
async def scan_document(file: UploadFile = File(...)):

    try:
        file_bytes = await file.read()

        files = {
            "file": (
                file.filename,
                file_bytes,
                file.content_type
            )
        }

        async with httpx.AsyncClient(timeout=120) as client:

            response = await client.post(
                f"{WINDOWS_AI_URL}/analyze",
                files=files
            )

        response.raise_for_status()

        ai_result = response.json()

        return ai_result

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Windows AI service is unavailable: {str(e)}"
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Windows AI service returned an error: {e.response.text}"
        )