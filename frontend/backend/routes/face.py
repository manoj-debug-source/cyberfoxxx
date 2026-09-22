from fastapi import APIRouter, UploadFile, File, HTTPException

from services.face_auth import (
    extract_id_face,
    liveness_check,
    verify_face
)

router = APIRouter()


@router.post("/extract-id")
async def extract_id(
    file: UploadFile = File(...)
):
    file_bytes = await file.read()

    response = await extract_id_face(
        file_bytes,
        file.filename or "document.jpg",
        file.content_type or "image/jpeg"
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


@router.post("/liveness")
async def check_liveness(
    session_id: str,
    file: UploadFile = File(...)
):
    file_bytes = await file.read()

    response = await liveness_check(
        session_id,
        file_bytes,
        file.filename or "live.jpg",
        file.content_type or "image/jpeg"
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


@router.post("/verify")
async def verify(
    session_id: str,
    file: UploadFile = File(...)
):
    file_bytes = await file.read()

    response = await verify_face(
        session_id,
        file_bytes,
        file.filename or "live.jpg",
        file.content_type or "image/jpeg"
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()