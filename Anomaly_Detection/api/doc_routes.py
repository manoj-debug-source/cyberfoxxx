"""
FastAPI route definitions for Document Fraud & Tampering Anomaly Screening across all 4 modules.
"""

import json
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from document_engine.config import BORDER_WATCHLIST
from document_engine.face_verifier import FaceVerifier
from document_engine.ocr_extractor import OCRExtractor
from document_engine.schema import (
    DocumentScreeningFieldsRequest,
    DocumentScreeningResult,
    FaceVerificationResult,
    OCRResult,
    PassportData,
    VisaData,
    WatchlistHit,
)
from document_engine.screener import DocumentScreener

router = APIRouter(prefix="/api/v1/document", tags=["Document Screening & Anomaly Detection"])
screener = DocumentScreener()
ocr_extractor = OCRExtractor()
face_verifier = FaceVerifier()


@router.get("/health")
def document_engine_health():
    """
    Returns health and operational readiness of all 4 Screening Modules.
    """
    return {
        "status": "HEALTHY",
        "module_1_ocr_extraction": "ACTIVE",
        "module_2_document_validation": "ACTIVE",
        "module_3_tampering_detection": "ACTIVE",
        "module_4_face_verification": "ACTIVE",
        "modules": {
            "module_1_ocr_extraction": "ACTIVE",
            "module_2_document_validation": "ACTIVE",
            "module_3_tampering_detection": "ACTIVE",
            "module_4_face_verification": "ACTIVE",
        },
        "supported_checks": [
            "Error Level Analysis (ELA Heatmap)",
            "Sensor Noise Inconsistency (Photo Splicing)",
            "Visa Stamp Forgery & Ink Uniformity",
            "Text Manipulation & Edge Gradients",
            "EXIF Software Forensics",
            "ICAO 9303 MRZ Checksums",
            "Temporal Sequence & Expiry Validation",
            "SSB / Interpol Border Watchlist Matching",
            "1:1 Biometric Face Verification (Cosine Similarity)",
            "Presentation Attack Detection (PAD / Anti-Spoofing)",
        ],
    }


@router.get("/watchlist", response_model=List[dict])
def get_border_watchlist():
    """
    Returns simulated SSB / Interpol active lookout alerts and stolen passport records.
    """
    return BORDER_WATCHLIST


@router.post("/ocr", response_model=OCRResult)
def extract_ocr_fields(
    raw_text: str = Form(..., description="Raw OCR transcript or MRZ string text"),
    document_type: str = Form("PASSPORT", description="Type of document"),
) -> OCRResult:
    """
    Module 1: Extracts structured identity fields from raw OCR text or MRZ string.
    """
    try:
        return ocr_extractor.extract_from_raw_text(raw_text, default_type=document_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OCR parsing failed: {str(e)}",
        )


@router.post("/face-verify", response_model=FaceVerificationResult)
async def verify_faces_endpoint(
    doc_image: UploadFile = File(..., description="Document portrait or full passport scan"),
    live_face: UploadFile = File(..., description="Live border checkpoint webcam or selfie capture"),
) -> FaceVerificationResult:
    """
    Module 4: 1:1 Biometric Face Matching and Anti-Spoofing Liveness Inspection.
    """
    try:
        doc_bytes = await doc_image.read()
        live_bytes = await live_face.read()
        res, _ = face_verifier.verify_faces(doc_bytes, live_bytes)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Face verification failed: {str(e)}",
        )


@router.post("/screen-fields", response_model=DocumentScreeningResult)
def screen_document_fields(request: DocumentScreeningFieldsRequest) -> DocumentScreeningResult:
    """
    Fast field-level screening for extracted OCR fields, MRZ checksums, and EXIF metadata.
    """
    try:
        return screener.screen_fields_only(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document screening failed: {str(e)}",
        )


@router.post("/screen", response_model=DocumentScreeningResult)
async def screen_document(
    image: UploadFile = File(..., description="Passport or travel document image file (JPG/PNG)"),
    live_face: Optional[UploadFile] = File(None, description="Optional live traveler face photo"),
    document_type: str = Form("PASSPORT"),
    passport_json: Optional[str] = Form(None, description="JSON string of PassportData fields"),
    visa_json: Optional[str] = Form(None, description="JSON string of VisaData fields"),
    metadata_json: Optional[str] = Form(None, description="JSON string of EXIF/metadata"),
    raw_ocr_text: Optional[str] = Form(None, description="Raw OCR or MRZ text transcript"),
) -> DocumentScreeningResult:
    """
    Comprehensive multi-layer border screening across Modules 1-4.
    """
    try:
        image_bytes = await image.read()
        live_face_bytes = await live_face.read() if live_face else None

        passport_data = None
        if passport_json:
            p_dict = json.loads(passport_json)
            passport_data = PassportData(**p_dict)

        visa_data = None
        if visa_json:
            v_dict = json.loads(visa_json)
            visa_data = VisaData(**v_dict)

        metadata_dict = json.loads(metadata_json) if metadata_json else None

        return screener.screen(
            image_input=image_bytes,
            live_face_input=live_face_bytes,
            passport=passport_data,
            visa=visa_data,
            document_type=document_type,
            metadata=metadata_dict,
            raw_ocr_text=raw_ocr_text,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process document screening request: {str(e)}",
        )

