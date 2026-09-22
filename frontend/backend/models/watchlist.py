from typing import Optional
from pydantic import BaseModel, Field


class WatchlistRecord(BaseModel):
    record_id: str = Field(..., min_length=1)

    name: str = Field(..., min_length=1)

    date_of_birth: Optional[str] = None

    document_number: Optional[str] = None

    nationality: Optional[str] = None

    status: str = "ACTIVE"

    category: str = "WATCHLIST"


class WatchlistCheckRequest(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    document_number: Optional[str] = None
    nationality: Optional[str] = None


class WatchlistCheckResponse(BaseModel):
    screening_id: str

    status: str

    match_found: bool

    match_type: Optional[str] = None

    match_score: float = 0.0

    matched_fields: list[str] = []

    record_id: Optional[str] = None

    message: str