from fastapi import APIRouter, HTTPException, Depends
import httpx

from utils.jwt import get_current_user
from services.identity_validation import validate_identity


router = APIRouter()


@router.post("/validate")
async def validate(
    identity_data: dict,
    current_user: dict = Depends(get_current_user)
):
    try:
        response = await validate_identity(identity_data)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text
            )

        return {
            "success": True,
            "validated_by": current_user.get("username"),
            "identity_validation": response.json()
        }

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Identity Validation service unavailable: {str(e)}"
        )