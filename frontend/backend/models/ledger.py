
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LedgerEvent(BaseModel):
    screening_id: str
    event_type: str

    identity_hash: Optional[str] = None
    document_hash: Optional[str] = None

    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None

    timestamp: Optional[datetime] = None

    created_by: Optional[str] = None
