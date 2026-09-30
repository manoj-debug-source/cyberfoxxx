"""
Unified Enterprise Border Screening Engine combining Modules 1-4:
Module 1: OCR Extraction & MRZ Parsing
Module 2: Document Standards & ICAO 9303 Checksums + Watchlist Lookup
Module 3: Tampering & Forgery Forensics (ELA Heatmap, Noise Inconsistency, Stamp & Font)
Module 4: Biometric Face Verification & Anti-Spoofing Presentation Attack Detection
"""

from pathlib import Path
from typing import List, Optional, Union
from PIL import Image

from document_engine.config import (
    DECISION_POLICIES,
    SEVERITY_THRESHOLDS,
    WEIGHT_FIELD_VALIDATION,
    WEIGHT_IMAGE_FORENSICS,
    WEIGHT_FACE_VERIFICATION,
    WEIGHT_OCR_CONFIDENCE,
)
from document_engine.face_verifier import FaceVerifier
from document_engine.image_forensics import ImageForensicAnalyzer
from document_engine.mrz_validator import DocumentValidator
from document_engine.ocr_extractor import OCRExtractor
from document_engine.schema import (
    DocumentScreeningFieldsRequest,
    DocumentScreeningResult,
    EvidenceItem,
    FaceVerificationResult,
    OCRResult,
    PassportData,
    VisaData,
    WatchlistHit,
)


class DocumentScreener:
    """
    Unified 4-Module Border Checkpoint Anomaly Screening Engine.
    """

    def __init__(self):
        self.image_analyzer = ImageForensicAnalyzer()
        self.validator = DocumentValidator()
        self.ocr_extractor = OCRExtractor()
        self.face_verifier = FaceVerifier()

    def screen(
        self,
        image_input: Optional[Union[str, Path, bytes, Image.Image]] = None,
        live_face_input: Optional[Union[str, Path, bytes, Image.Image]] = None,
        passport: Optional[PassportData] = None,
        visa: Optional[VisaData] = None,
        document_type: str = "PASSPORT",
        metadata: Optional[dict] = None,
        raw_ocr_text: Optional[str] = None,
    ) -> DocumentScreeningResult:
        """
        Executes end-to-end multi-layer screening across all 4 modules.
        """
        evidence: List[EvidenceItem] = []
        fraud_types: List[str] = []
        ocr_result: Optional[OCRResult] = None
        face_result: Optional[FaceVerificationResult] = None
        watchlist_hit: Optional[WatchlistHit] = None
        ela_heatmap_b64: Optional[str] = None

        image_score = 0.0
        field_score = 0.0
        face_score = 0.0
        ocr_score = 0.0

        tampering_detected = False
        validation_failed = False
        face_verified = None
        impersonation_detected = False

        # --- MODULE 1: OCR Extraction ---
        if raw_ocr_text:
            ocr_result = self.ocr_extractor.extract_from_raw_text(raw_ocr_text, default_type=document_type)
            if passport is None and ocr_result.passport:
                passport = ocr_result.passport
            if visa is None and ocr_result.visa:
                visa = ocr_result.visa

        # --- MODULE 3: Image Forensics & ELA Tampering Detection ---
        if image_input is not None:
            (
                tampering_detected,
                image_score,
                img_evidence,
                img_frauds,
            ) = self.image_analyzer.analyze_image(image_input, metadata)
            evidence.extend(img_evidence)
            fraud_types.extend(img_frauds)
            ela_heatmap_b64 = self.image_analyzer.last_ela_heatmap_base64

        # --- MODULE 2: Document Validation, MRZ Checksums & Watchlists ---
        if passport is not None or visa is not None:
            (
                validation_failed,
                field_score,
                fld_evidence,
                fld_frauds,
            ) = self.validator.validate(passport=passport, visa=visa)
            evidence.extend(fld_evidence)
            fraud_types.extend(fld_frauds)
            watchlist_hit = self.validator.last_watchlist_hit

        # --- MODULE 4: Face Verification & Anti-Spoofing ---
        if image_input is not None and live_face_input is not None:
            face_result, face_ev = self.face_verifier.verify_faces(
                doc_image_input=image_input,
                live_image_input=live_face_input,
            )
            face_verified = face_result.is_match
            impersonation_detected = face_result.is_impersonation
            if face_ev:
                evidence.append(face_ev)
            if face_result.is_impersonation:
                fraud_types.append("Biometric Identity Impersonation")
                face_score = 0.95
            elif not face_result.liveness_passed:
                fraud_types.append("Biometric Presentation Attack / Spoof")
                face_score = 0.90
            elif not face_result.is_match:
                fraud_types.append("Facial Biometric Mismatch")
                face_score = 0.65
            else:
                face_score = 0.0

        # --- MULTI-FACTOR SCORE FUSION ---
        active_weights = []
        scores = []

        if image_input is not None:
            active_weights.append(WEIGHT_IMAGE_FORENSICS)
            scores.append(image_score)

        if passport is not None or visa is not None:
            active_weights.append(WEIGHT_FIELD_VALIDATION)
            scores.append(field_score)

        if live_face_input is not None:
            active_weights.append(WEIGHT_FACE_VERIFICATION)
            scores.append(face_score)

        if ocr_result is not None:
            active_weights.append(WEIGHT_OCR_CONFIDENCE)
            scores.append(ocr_score)

        if active_weights and sum(active_weights) > 0:
            norm_weights = [w / sum(active_weights) for w in active_weights]
            raw_score = sum(w * s for w, s in zip(norm_weights, scores))
        else:
            raw_score = 0.0

        # Critical severity overrides
        if watchlist_hit is not None:
            raw_score = max(raw_score, 0.98)
        if impersonation_detected:
            raw_score = max(raw_score, 0.92)
        has_critical = any(e.severity == "CRITICAL" for e in evidence)
        if has_critical:
            raw_score = max(raw_score, 0.88)

        final_score = round(float(min(1.0, max(0.05, raw_score))), 3)
        is_anomaly = (
            tampering_detected
            or validation_failed
            or impersonation_detected
            or (watchlist_hit is not None)
            or (final_score >= SEVERITY_THRESHOLDS["MEDIUM"])
        )

        # Decision & Severity Classification
        severity, decision = self._classify_decision(final_score, is_anomaly)

        # Confidence Calculation
        dist = abs(final_score - 0.50)
        confidence = round(float(min(0.99, 0.65 + dist * 0.7)), 3)

        # Prescriptive Action Synthesis
        action = self._synthesize_action(decision, evidence, fraud_types, watchlist_hit)

        doc_id = (
            passport.passport_number
            if passport
            else (visa.visa_number if visa else "UNKNOWN_DOC")
        )

        return DocumentScreeningResult(
            document_id=doc_id,
            document_type=document_type,
            is_anomaly=is_anomaly,
            anomaly_score=final_score,
            severity=severity,
            decision=decision,
            confidence=confidence,
            tampering_detected=tampering_detected,
            validation_failed=validation_failed,
            face_verified=face_verified,
            impersonation_detected=impersonation_detected,
            watchlist_hit=watchlist_hit,
            ocr_result=ocr_result,
            face_verification=face_result,
            detected_fraud_types=list(set(fraud_types)),
            evidence=evidence,
            recommended_action=action,
            ela_heatmap_base64=ela_heatmap_b64,
        )

    def screen_fields_only(
        self, request: DocumentScreeningFieldsRequest
    ) -> DocumentScreeningResult:
        """
        Fast screening when only extracted OCR fields and metadata are supplied.
        """
        return self.screen(
            image_input=None,
            live_face_input=None,
            passport=request.passport,
            visa=request.visa,
            document_type=request.document_type,
            metadata=request.metadata,
        )

    def _classify_decision(self, score: float, is_anomaly: bool) -> tuple:
        if not is_anomaly and score < SEVERITY_THRESHOLDS["LOW"]:
            return "NORMAL", DECISION_POLICIES["ALLOW"]
        elif score < SEVERITY_THRESHOLDS["LOW"]:
            return "LOW", DECISION_POLICIES["ALLOW"]
        elif score < SEVERITY_THRESHOLDS["MEDIUM"]:
            return "LOW", DECISION_POLICIES["VERIFY"]
        elif score < SEVERITY_THRESHOLDS["HIGH"]:
            return "MEDIUM", DECISION_POLICIES["VERIFY"]
        elif score < SEVERITY_THRESHOLDS["CRITICAL"]:
            return "HIGH", DECISION_POLICIES["SECONDARY"]
        else:
            return "CRITICAL", DECISION_POLICIES["REJECT"]

    def _synthesize_action(
        self,
        decision: str,
        evidence: List[EvidenceItem],
        fraud_types: List[str],
        watchlist_hit: Optional[WatchlistHit] = None,
    ) -> str:
        if watchlist_hit:
            return (
                f"CODE RED ESCALATION: INTERPOL / SSB WATCHLIST ALERT. "
                f"Detain passenger immediately. Match: {watchlist_hit.category} ({watchlist_hit.reason}). "
                f"Notify {watchlist_hit.issuing_agency} and transfer custody to armed border patrol."
            )
        elif "REJECT" in decision:
            frauds_str = ", ".join(fraud_types) if fraud_types else "Document Forgery"
            return (
                f"IMMEDIATE ACTION: Detain document holder at primary checkpoint. "
                f"Confiscate document under suspected forgery ({frauds_str}). "
                f"Escalate to Special Border Investigation Unit for physical forensic analysis."
            )
        elif "SECONDARY" in decision:
            return (
                "ACTION REQUIRED: Flag passenger for Secondary Immigration Screening. "
                "Conduct physical ultraviolet (UV) and infrared (IR) security thread verification and supervisor interview."
            )
        elif "VERIFY" in decision:
            return (
                "ADVISORY: Conduct routine passenger interview to confirm travel intent, "
                "return ticket, and lodging arrangements."
            )
        else:
            return "CLEARED: Document and biometric match verified authentic. Authorize passenger to proceed."
