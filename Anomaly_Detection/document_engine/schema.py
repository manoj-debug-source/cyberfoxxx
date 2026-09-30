"""
Pydantic schemas for document screening requests, validated fields, and forensic outputs across all 4 modules.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class PassportData(BaseModel):
    """
    Extracted data fields from passport visual zone and MRZ.
    """
    name: str = Field(..., description="Full name as printed on passport")
    passport_number: str = Field(..., min_length=6, max_length=15, description="Document number")
    nationality: str = Field(..., min_length=2, max_length=3, description="3-letter ICAO country code (e.g. IND, USA)")
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD or YYMMDD)")
    date_of_expiry: str = Field(..., description="Date of expiry (YYYY-MM-DD or YYMMDD)")
    gender: Literal["M", "F", "X"] = Field(..., description="Gender indicator (M, F, X)")
    mrz_line1: Optional[str] = Field(default=None, description="First line of Machine Readable Zone (44 chars)")
    mrz_line2: Optional[str] = Field(default=None, description="Second line of Machine Readable Zone (44 chars)")


class VisaData(BaseModel):
    """
    Extracted data fields from visa travel authorization.
    """
    visa_number: Optional[str] = Field(default=None, description="Official Visa authorization number")
    visa_type: Optional[str] = Field(default="TOURIST", description="Type of visa (e.g., TOURIST, BUSINESS, STUDENT)")
    entry_validation_date: Optional[str] = Field(default=None, description="Date of entry or validity start (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(default=None, description="Visa expiration date (YYYY-MM-DD)")
    stay_duration_days: Optional[int] = Field(default=None, ge=1, le=365, description="Authorized duration of stay in days")


class NationalIDData(BaseModel):
    """
    Extracted data fields from National ID / Aadhaar card.
    """
    id_number: str = Field(..., description="National ID or UID number")
    name: str = Field(..., description="Full name of citizen")
    date_of_birth: str = Field(..., description="Date of birth")
    gender: str = Field(default="M", description="Gender")
    address: Optional[str] = Field(default=None, description="Registered residential address")


class DrivingLicenseData(BaseModel):
    """
    Extracted data fields from Driving License.
    """
    license_number: str = Field(..., description="Driving license registration number")
    name: str = Field(..., description="Full name of license holder")
    date_of_birth: str = Field(..., description="Date of birth")
    date_of_issue: Optional[str] = Field(default=None, description="License issue date")
    valid_until: Optional[str] = Field(default=None, description="License expiry date")
    vehicle_classes: Optional[str] = Field(default="LMV, MCWG", description="Authorized vehicle classes")


class OCRResult(BaseModel):
    """
    Module 1: OCR and document field extraction output.
    """
    document_type: str = Field(default="PASSPORT", description="Classified document category")
    passport: Optional[PassportData] = Field(default=None, description="Extracted passport fields")
    visa: Optional[VisaData] = Field(default=None, description="Extracted visa fields")
    national_id: Optional[NationalIDData] = Field(default=None, description="Extracted national ID fields")
    mrz_detected: bool = Field(default=False, description="True if ICAO MRZ was found and parsed")
    mrz_lines: List[str] = Field(default_factory=list, description="Extracted raw MRZ lines")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="OCR extraction confidence score")
    extracted_text: str = Field(default="", description="Full extracted OCR text transcript")


class WatchlistHit(BaseModel):
    """
    Interpol / SSB Watchlist hit details.
    """
    passport_number: str = Field(..., description="Matched document number")
    name: str = Field(..., description="Watchlist suspect name")
    category: str = Field(..., description="Category (e.g. INTERPOL RED NOTICE, STOLEN PASSPORT)")
    reason: str = Field(..., description="Enforcement description")
    alert_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Alert severity level")
    issuing_agency: str = Field(..., description="Issuing security agency")


class FaceVerificationResult(BaseModel):
    """
    Module 4: Face Verification & Anti-Spoofing output.
    """
    face_detected_doc: bool = Field(..., description="Whether a face was isolated from document photo")
    face_detected_live: bool = Field(..., description="Whether a face was detected in live checkpoint image")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="1:1 biometric similarity score [0.0 - 1.0]"
    )
    is_match: bool = Field(..., description="True if similarity exceeds verification threshold")
    is_impersonation: bool = Field(..., description="True if face indicates identity impersonation")
    liveness_passed: bool = Field(..., description="True if face passed anti-spoofing / liveness checks")
    liveness_score: float = Field(default=0.95, ge=0.0, le=1.0, description="Liveness confidence score")
    anti_spoof_detail: str = Field(default="3D Live Human Skin Texture Verified", description="Forensic detail")


class DocumentScreeningFieldsRequest(BaseModel):
    """
    Field-level validation screening request (when image is processed client-side or omitted).
    """
    document_type: Literal["PASSPORT", "VISA", "NATIONAL_ID", "DRIVING_LICENSE"] = Field(
        default="PASSPORT", description="Type of travel document"
    )
    passport: Optional[PassportData] = Field(default=None, description="Passport data fields")
    visa: Optional[VisaData] = Field(default=None, description="Visa data fields")
    metadata: Optional[dict] = Field(default_factory=dict, description="Image EXIF/Header metadata")


class EvidenceItem(BaseModel):
    """
    Individual forensic evidence item pinpointing exact tampering or validation failure.
    """
    layer: Literal[
        "OCR_EXTRACTION",
        "DOCUMENT_VALIDATION",
        "IMAGE_FORENSICS",
        "METADATA_ANALYSIS",
        "FACE_VERIFICATION",
        "WATCHLIST",
    ]
    anomaly: str = Field(..., description="Identified anomaly type")
    detail: str = Field(..., description="Factual forensic detail explaining the finding")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class DocumentScreeningResult(BaseModel):
    """
    Unified enterprise border screening decision report across all 4 modules.
    """
    audit_id: str = Field(
        default_factory=lambda: f"SSB-{uuid.uuid4().hex[:8].upper()}",
        description="Unique border screening audit record identifier"
    )
    document_id: str = Field(..., description="Document identifier / passport number")
    document_type: str = Field(..., description="Document category")
    is_anomaly: bool = Field(..., description="True if any tampering or validation anomaly is detected")
    anomaly_score: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated calibrated fraud probability score [0.0 - 1.0]"
    )
    severity: Literal["NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Overall risk severity classification"
    )
    decision: str = Field(..., description="Automated border clearance decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Screening audit timestamp"
    )
    tampering_detected: bool = Field(..., description="True if physical or pixel-level manipulation was found")
    validation_failed: bool = Field(..., description="True if ICAO checksum or logical rules failed")
    face_verified: Optional[bool] = Field(default=None, description="True if live face matches document photo")
    impersonation_detected: bool = Field(default=False, description="True if live face fails match / impersonation")
    watchlist_hit: Optional[WatchlistHit] = Field(default=None, description="SSB / Interpol watchlist alert if found")
    ocr_result: Optional[OCRResult] = Field(default=None, description="Extracted OCR fields")
    face_verification: Optional[FaceVerificationResult] = Field(default=None, description="Biometric verification results")
    detected_fraud_types: List[str] = Field(default_factory=list, description="List of detected fraud categories")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Prioritized forensic evidence items")
    recommended_action: str = Field(..., description="Prescriptive action for immigration officer")
    ela_heatmap_base64: Optional[str] = Field(default=None, description="Base64 encoded visual ELA heatmap PNG")
