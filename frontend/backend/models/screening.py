from pydantic import BaseModel
from typing import Optional


class ScreeningCreate(BaseModel):
    filename: str
    document_hash: Optional[str] = None


class ScreeningResponse(BaseModel):
    screening_id: str
    filename: str
    document_hash: Optional[str] = None
    status: str