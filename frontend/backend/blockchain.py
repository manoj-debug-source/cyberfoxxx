import os
import hashlib
import uuid
import json

import httpx

from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from database.mongodb import db
from utils.jwt import get_current_user
from services.ocr import analyze_document
from services.tamper_detection import analyze_tamper
from services.blockchain import create_ledger_event


router = APIRouter(
    prefix="/pipeline",
    tags=["Screening Pipeline"]
)


# =========================================================
# CONFIGURATION
# =========================================================

RISK_SERVICE_URL = os.getenv(
    "RISK_SERVICE_URL",
    "http://127.0.0.1:8001"
)

RISK_CALIBRATION_URL = (
    f"{RISK_SERVICE_URL}/api/risk/calibrate"
)


DOCUMENT_SCREENING_URL = os.getenv(
    "DOCUMENT_SCREENING_URL",
    "http://10.109.60.79:8000"
)

DOCUMENT_SCREENING_ENDPOINT = os.getenv(
    "DOCUMENT_SCREENING_ENDPOINT",
    "/api/v1/document/screen"
)


IDENTITY_VALIDATION_URL = os.getenv(
    "IDENTITY_VALIDATION_URL",
    "http://10.22.80.181:8003"
)

IDENTITY_VALIDATION_ENDPOINT = os.getenv(
    "IDENTITY_VALIDATION_ENDPOINT",
    "/validate-identity"
)


REMOTE_TIMEOUT = float(
    os.getenv("REMOTE_SERVICE_TIMEOUT", "60")
)


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".pdf",
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def normalize_probability(value):
    """
    Convert a probability into a value between 0 and 1.
    """

    if value is None:
        return 0.0

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if value > 1:
        value = value / 100

    return max(0.0, min(1.0, value))


def extract_document_number(ocr_result):
    """
    Try to extract a document/passport number
    from different OCR result structures.
    """

    if not isinstance(ocr_result, dict):
        return None

    possible_keys = [
        "document_number",
        "passport_number",
        "id_number",
        "number",
        "passport_no",
    ]

    for key in possible_keys:
        value = ocr_result.get(key)

        if value:
            return str(value).strip()

    fields = ocr_result.get("fields")

    if isinstance(fields, dict):
        for key in possible_keys:
            value = fields.get(key)

            if value:
                return str(value).strip()

    return None


def extract_ocr_confidence(ocr_result):
    """
    Extract OCR confidence from different possible
    response structures.
    """

    if not isinstance(ocr_result, dict):
        return 1.0

    candidates = [
        ocr_result.get("confidence"),
        ocr_result.get("ocr_confidence"),
        ocr_result.get("average_confidence"),
    ]

    for value in candidates:

        if value is not None:
            return normalize_probability(value)

    return 1.0


def extract_mrz_result(ocr_result):
    """
    Extract MRZ result if available.
    """

    if not isinstance(ocr_result, dict):
        return None

    return (
        ocr_result.get("mrz")
        or ocr_result.get("mrz_result")
        or ocr_result.get("mrz_data")
    )


def get_nested_value(data, *keys):
    """
    Safely retrieve a nested value.
    """

    current = data

    for key in keys:

        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def generate_identity_hash(identity_data):
    """
    Generate deterministic SHA-256 hash for identity data.

    The raw identity data is NOT stored inside the hash.
    """

    normalized = {
        "full_name": str(
            identity_data.get("full_name", "")
        ).strip().upper(),

        "date_of_birth": str(
            identity_data.get("date_of_birth", "")
        ).strip(),

        "gender": str(
            identity_data.get("gender", "")
        ).strip().upper(),

        "id_type": str(
            identity_data.get("id_type", "")
        ).strip().upper(),

        "id_number": str(
            identity_data.get("id_number", "")
        ).strip().upper(),

        "address": str(
            identity_data.get("address", "")
        ).strip().upper(),

        "phone": str(
            identity_data.get("phone", "")
        ).strip(),
    }

    canonical_data = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()


def build_identity_validation_payload(
    ocr_result,
    mrz_result,
):
    """
    Convert OCR/MRZ information into the schema
    expected by the Identity Validation service.
    """

    identity_source = {}

    if isinstance(ocr_result, dict):
        identity_source.update(ocr_result)

        fields = ocr_result.get("fields")

        if isinstance(fields, dict):
            identity_source.update(fields)

    if isinstance(mrz_result, dict):
        identity_source.update(mrz_result)

    full_name = (
        identity_source.get("full_name")
        or identity_source.get("name")
        or identity_source.get("passenger_name")
        or identity_source.get("holder_name")
        or ""
    )

    date_of_birth = (
        identity_source.get("date_of_birth")
        or identity_source.get("dob")
        or ""
    )

    gender = (
        identity_source.get("gender")
        or identity_source.get("sex")
        or ""
    )

    id_number = (
        identity_source.get("id_number")
        or identity_source.get("passport_number")
        or identity_source.get("document_number")
        or identity_source.get("passport_no")
        or ""
    )

    address = (
        identity_source.get("address")
        or ""
    )

    phone = (
        identity_source.get("phone")
        or identity_source.get("phone_number")
        or None
    )

    return {
        "full_name": str(full_name).strip(),
        "date_of_birth": str(date_of_birth).strip(),
        "gender": str(gender).strip(),
        "id_type": "PASSPORT",
        "id_number": str(id_number).strip(),
        "address": str(address).strip(),
        "phone": (
            str(phone).strip()
            if phone is not None
            else None
        ),
    }


def extract_anomaly_probability(anomaly_result):
    """
    Extract anomaly score from the remote document
    screening service.
    """

    if not isinstance(anomaly_result, dict):
        return 0.0

    candidates = [
        anomaly_result.get("anomaly_score"),
        anomaly_result.get("anomaly_probability"),
        anomaly_result.get("score"),
    ]

    for value in candidates:

        if value is not None:
            return normalize_probability(value)

    return 0.0


def extract_tamper_probability(tamper_result):
    """
    Extract tamper probability from local tamper analysis.
    """

    if not isinstance(tamper_result, dict):
        return 0.0

    candidates = [
        tamper_result.get("tamper_probability"),
        tamper_result.get("probability"),
        tamper_result.get("forgery_probability"),
        tamper_result.get("score"),
    ]

    for value in candidates:

        if value is not None:
            return normalize_probability(value)

    return 0.0


def get_identity_validation_score(
    validation_result
):
    """
    Convert identity validation response into
    a normalized risk-compatible value.

    Higher score = stronger identity match.
    """

    if not isinstance(validation_result, dict):
        return 0.0

    validation = validation_result.get(
        "validation",
        validation_result
    )

    if not isinstance(validation, dict):
        return 0.0

    score = validation.get("match_score")

    if score is not None:
        return normalize_probability(score)

    decision = str(
        validation.get("decision", "")
    ).upper()

    if decision == "VALID":
        return 1.0

    if decision == "SUSPICIOUS":
        return 0.5

    return 0.0


# =========================================================
# REMOTE DOCUMENT SCREENING
# =========================================================

async def screen_document_with_teammate(
    file_bytes,
    filename,
    content_type,
):
    """
    Send the document to the remote document screening
    and anomaly detection service.
    """

    url = (
        f"{DOCUMENT_SCREENING_URL}"
        f"{DOCUMENT_SCREENING_ENDPOINT}"
    )

    remote_content_type = (
        content_type
        or "application/octet-stream"
    )

    files = {
        "image": (
            filename,
            file_bytes,
            remote_content_type,
        )
    }

    data = {
        "document_type": "PASSPORT"
    }

    async with httpx.AsyncClient(
        timeout=REMOTE_TIMEOUT
    ) as client:

        response = await client.post(
            url,
            files=files,
            data=data,
        )

        response.raise_for_status()

        return response.json()


# =========================================================
# IDENTITY VALIDATION
# =========================================================

async def validate_identity_remotely(
    identity_payload
):
    """
    Send extracted identity data to the remote
    Identity Validation service.
    """

    url = (
        f"{IDENTITY_VALIDATION_URL}"
        f"{IDENTITY_VALIDATION_ENDPOINT}"
    )

    async with httpx.AsyncClient(
        timeout=REMOTE_TIMEOUT
    ) as client:

        response = await client.post(
            url,
            json=identity_payload,
        )

        response.raise_for_status()

        return response.json()


# =========================================================
# MAIN SCREENING PIPELINE
# =========================================================

@router.post("/screen")
async def run_screening_pipeline(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Complete CYBERFOXXX screening pipeline.

    Flow:

    Document Upload
        ↓
    SHA-256
        ↓
    OCR
        ↓
    MRZ
        ↓
    Tamper Detection
        ↓
    Anomaly Detection
        ↓
    Identity Validation
        ↓
    Identity Hash
        ↓
    Risk Calibration
        ↓
    AI Recommendation

    Officer decision and Identity Linkage happen
    after this pipeline.
    """

    # =====================================================
    # USER
    # =====================================================

    created_by = (
        current_user.get("username")
        or current_user.get("email")
        or current_user.get("sub")
        or "unknown"
    )

    # =====================================================
    # FILE VALIDATION
    # =====================================================

    filename = file.filename or "uploaded_document"

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. "
                "Allowed: JPG, JPEG, PNG, PDF"
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    # =====================================================
    # SCREENING ID
    # =====================================================

    screening_id = (
        f"SCR-{uuid.uuid4().hex[:8].upper()}"
    )

    scan_id = screening_id

    # =====================================================
    # DOCUMENT SHA-256
    # =====================================================

    document_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    now = datetime.now(timezone.utc)

    # =====================================================
    # INITIAL PIPELINE STATE
    # =====================================================

    pipeline_state = {

        "sha256": {
            "status": "COMPLETED",
            "hash": document_hash,
        },

        "ocr": {
            "status": "PENDING",
        },

        "mrz": {
            "status": "PENDING",
        },

        "tamper": {
            "status": "PENDING",
        },

        "anomaly": {
            "status": "PENDING",
        },

        "identity_validation": {
            "status": "PENDING",
        },

        "face_liveness": {
            "status": "PENDING",
        },

        "risk": {
            "status": "PENDING",
        },

        "decision": {
            "status": "PENDING",
        },
    }

    # =====================================================
    # CREATE SCREENING RECORD
    # =====================================================

    screening_document = {

        "screening_id": screening_id,

        "scan_id": scan_id,

        "filename": filename,

        "content_type": file.content_type,

        "document_hash": document_hash,

        "status": "PROCESSING",

        "created_at": now,

        "created_by": created_by,

        "pipeline": pipeline_state,

        "ocr": None,

        "ocr_result": None,

        "mrz": None,

        "tamper": None,

        "tamper_analysis": None,

        "document_screening": None,

        "anomaly": None,

        "anomaly_analysis": None,

        "identity_validation": None,

        "identity_data": None,

        "identity_hash": None,

        "face": None,

        "face_analysis": None,

        "risk": None,

        "ai_decision": None,

        "officer_decision": None,

    }

    await db.screenings.insert_one(
        screening_document
    )

    # =====================================================
    # LEDGER: SCREENING CREATED
    # =====================================================

    try:

        await create_ledger_event(
            screening_id=screening_id,
            event_type="SCREENING_CREATED",
            document_hash=document_hash,
            created_by=created_by,
        )

    except Exception as exc:

        print(
            f"[LEDGER WARNING] "
            f"SCREENING_CREATED failed: {exc}"
        )

    # =====================================================
    # OCR + MRZ
    # =====================================================

    ocr_result = None
    mrz_result = None

    try:

        ocr_result = await analyze_document(
            file_bytes,
            filename,
        )

        mrz_result = extract_mrz_result(
            ocr_result
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "ocr": ocr_result,
                    "ocr_result": ocr_result,

                    "mrz": mrz_result,

                    "pipeline.ocr": {
                        "status": "COMPLETED"
                    },

                    "pipeline.mrz": {
                        "status": "COMPLETED"
                    },
                }
            },
        )

    except Exception as exc:

        print(
            f"[OCR WARNING] {exc}"
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "pipeline.ocr": {
                        "status": "FAILED",
                        "error": str(exc),
                    },

                    "pipeline.mrz": {
                        "status": "FAILED",
                        "error": str(exc),
                    },
                }
            },
        )

    # =====================================================
    # TAMPER DETECTION
    # =====================================================

    tamper_result = None

    if extension in {
        ".jpg",
        ".jpeg",
        ".png",
    }:

        try:

            tamper_result = await analyze_tamper(
                file_bytes,
                filename,
            )

            await db.screenings.update_one(
                {
                    "screening_id": screening_id
                },
                {
                    "$set": {
                        "tamper": tamper_result,

                        "tamper_analysis": tamper_result,

                        "pipeline.tamper": {
                            "status": "COMPLETED",
                            "result": tamper_result,
                        },
                    }
                },
            )

        except Exception as exc:

            print(
                f"[TAMPER WARNING] {exc}"
            )

            await db.screenings.update_one(
                {
                    "screening_id": screening_id
                },
                {
                    "$set": {
                        "pipeline.tamper": {
                            "status": "FAILED",
                            "error": str(exc),
                        }
                    }
                },
            )

    else:

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "pipeline.tamper": {
                        "status": "SKIPPED",
                        "reason": (
                            "PDF tamper analysis "
                            "requires image rendering"
                        ),
                    }
                }
            },
        )

    # =====================================================
    # REMOTE ANOMALY + DOCUMENT SCREENING
    # =====================================================

    remote_screening = None
    anomaly_result = None

    try:

        remote_screening = (
            await screen_document_with_teammate(
                file_bytes=file_bytes,
                filename=filename,
                content_type=file.content_type,
            )
        )

        anomaly_result = (
            remote_screening.get(
                "anomaly_result"
            )
            if isinstance(remote_screening, dict)
            else None
        )

        # Some service versions return the result
        # directly instead of anomaly_result.
        if anomaly_result is None:
            anomaly_result = remote_screening

        anomaly_probability = (
            extract_anomaly_probability(
                anomaly_result
            )
        )

        anomaly_is_anomaly = (
            anomaly_result.get(
                "is_anomaly"
            )
            if isinstance(
                anomaly_result,
                dict
            )
            else None
        )

        anomaly_decision = (
            anomaly_result.get(
                "decision"
            )
            if isinstance(
                anomaly_result,
                dict
            )
            else None
        )

        anomaly_severity = (
            anomaly_result.get(
                "severity"
            )
            if isinstance(
                anomaly_result,
                dict
            )
            else None
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {

                    "document_screening":
                        remote_screening,

                    "anomaly":
                        anomaly_result,

                    "anomaly_analysis":
                        anomaly_result,

                    "pipeline.anomaly": {

                        "status": "COMPLETED",

                        "score":
                            anomaly_probability,

                        "is_anomaly":
                            anomaly_is_anomaly,

                        "decision":
                            anomaly_decision,

                        "severity":
                            anomaly_severity,
                    },
                }
            },
        )

    except Exception as exc:

        print(
            f"[REMOTE ANOMALY WARNING] "
            f"{exc}"
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "pipeline.anomaly": {
                        "status": "FAILED",
                        "error": str(exc),
                    }
                }
            },
        )

    # =====================================================
    # IDENTITY VALIDATION
    # =====================================================

    identity_validation_result = None
    identity_payload = None
    identity_hash = None

    try:

        identity_payload = (
            build_identity_validation_payload(
                ocr_result,
                mrz_result,
            )
        )

        # Generate deterministic identity hash
        identity_hash = generate_identity_hash(
            identity_payload
        )

        # Store submitted identity data
        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "identity_data":
                        identity_payload,

                    "identity_hash":
                        identity_hash,
                }
            },
        )

        # -------------------------------------------------
        # Call Identity Validation API
        # -------------------------------------------------

        identity_validation_result = (
            await validate_identity_remotely(
                identity_payload
            )
        )

        validation = (
            identity_validation_result.get(
                "validation",
                {}
            )
            if isinstance(
                identity_validation_result,
                dict
            )
            else {}
        )

        validation_decision = (
            validation.get(
                "decision"
            )
            if isinstance(validation, dict)
            else None
        )

        validation_score = (
            validation.get(
                "match_score"
            )
            if isinstance(validation, dict)
            else None
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {

                    "identity_validation":
                        identity_validation_result,

                    "pipeline.identity_validation": {

                        "status": "COMPLETED",

                        "decision":
                            validation_decision,

                        "match_score":
                            validation_score,

                        "identity_hash":
                            identity_hash,
                    },
                }
            },
        )

        # -------------------------------------------------
        # LEDGER: IDENTITY VALIDATED
        # -------------------------------------------------

        try:

            await create_ledger_event(
                screening_id=screening_id,
                event_type="IDENTITY_VALIDATED",

                identity_hash=identity_hash,

                document_hash=document_hash,

                created_by=created_by,
            )

        except Exception as exc:

            print(
                f"[LEDGER WARNING] "
                f"IDENTITY_VALIDATED failed: {exc}"
            )

    except Exception as exc:

        print(
            f"[IDENTITY VALIDATION WARNING] "
            f"{exc}"
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "pipeline.identity_validation": {
                        "status": "FAILED",
                        "error": str(exc),
                    }
                }
            },
        )

    # =====================================================
    # RISK CALIBRATION
    # =====================================================

    risk_result = None

    try:

        ocr_confidence = (
            extract_ocr_confidence(
                ocr_result
            )
        )

        mrz_confidence = 1.0

        if isinstance(
            mrz_result,
            dict
        ):

            mrz_confidence = normalize_probability(
                mrz_result.get(
                    "confidence",
                    mrz_result.get(
                        "mrz_confidence",
                        1.0,
                    ),
                )
            )

        tamper_probability = (
            extract_tamper_probability(
                tamper_result
            )
        )

        anomaly_probability = (
            extract_anomaly_probability(
                anomaly_result
            )
        )

        identity_validation_score = (
            get_identity_validation_score(
                identity_validation_result
            )
        )

        # -------------------------------------------------
        # IMPORTANT
        #
        # Identity Linkage is NOT used here.
        # Identity Linkage happens AFTER officer decision.
        #
        # The current risk service expects an
        # identity_linkage_score, so we use the
        # pre-decision identity validation score as
        # the available identity signal.
        # -------------------------------------------------

        risk_payload = {

            "screening_id":
                screening_id,

            "ocr_confidence":
                ocr_confidence,

            "mrz_confidence":
                mrz_confidence,

            "tamper_probability":
                tamper_probability,

            "anomaly_probability":
                anomaly_probability,

            "face_match_probability":
                1.0,

            "watchlist_probability":
                (
                    1.0
                    if (
                        isinstance(
                            identity_validation_result,
                            dict
                        )
                        and str(
                            identity_validation_result
                            .get(
                                "validation",
                                {}
                            )
                            .get(
                                "decision",
                                ""
                            )
                        ).upper()
                        in {
                            "BLACKLISTED",
                            "FAKE",
                        }
                    )
                    else 0.0
                ),

            "identity_linkage_score":
                identity_validation_score,
        }

        async with httpx.AsyncClient(
            timeout=REMOTE_TIMEOUT
        ) as client:

            response = await client.post(
                RISK_CALIBRATION_URL,
                json=risk_payload,
            )

            response.raise_for_status()

            risk_result = response.json()

        # Risk service normally returns:
        # {
        #   "risk": {...}
        # }

        risk_data = (
            risk_result.get(
                "risk",
                risk_result,
            )
            if isinstance(
                risk_result,
                dict
            )
            else risk_result
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {

                    "risk":
                        risk_data,

                    "pipeline.risk": {

                        "status":
                            "COMPLETED",

                        "result":
                            risk_data,
                    },
                }
            },
        )

    except Exception as exc:

        print(
            f"[RISK WARNING] {exc}"
        )

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {
                    "pipeline.risk": {
                        "status": "FAILED",
                        "error": str(exc),
                    }
                }
            },
        )

    # =====================================================
    # AI RECOMMENDATION
    # =====================================================

    ai_decision = "REVIEW"

    try:

        risk_data = (
            risk_result.get(
                "risk",
                risk_result,
            )
            if isinstance(
                risk_result,
                dict
            )
            else {}
        )

        risk_level = str(
            risk_data.get(
                "risk_level",
                risk_data.get(
                    "level",
                    ""
                ),
            )
        ).upper()

        if risk_level == "LOW":

            ai_decision = "CLEAR"

        elif risk_level == "MEDIUM":

            ai_decision = "REVIEW"

        elif risk_level in {
            "HIGH",
            "CRITICAL",
        }:

            ai_decision = "REJECT"

        else:

            # Fall back to anomaly result
            anomaly_decision_text = str(
                (
                    anomaly_result or {}
                ).get(
                    "decision",
                    ""
                )
            ).upper()

            if "REJECT" in anomaly_decision_text:
                ai_decision = "REJECT"

            elif "CLEAR" in anomaly_decision_text:
                ai_decision = "CLEAR"

            else:
                ai_decision = "REVIEW"

        await db.screenings.update_one(
            {
                "screening_id": screening_id
            },
            {
                "$set": {

                    "ai_decision":
                        ai_decision,

                    "pipeline.decision": {

                        "status":
                            "COMPLETED",

                        "recommendation":
                            ai_decision,
                    },

                    "status":
                        "AI_RECOMMENDATION_COMPLETED",
                }
            },
        )

    except Exception as exc:

        print(
            f"[AI DECISION WARNING] "
            f"{exc}"
        )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "success": True,

        "screening_id":
            screening_id,

        "scan_id":
            scan_id,

        "filename":
            filename,

        "document_hash":
            document_hash,

        "identity_hash":
            identity_hash,

        "status":
            "AI_RECOMMENDATION_COMPLETED",

        "pipeline":
            pipeline_state,

        "ocr":
            ocr_result,

        "mrz":
            mrz_result,

        "tamper":
            tamper_result,

        "document_screening":
            remote_screening,

        "anomaly":
            anomaly_result,

        "identity_validation":
            identity_validation_result,

        "risk":
            risk_result,

        "ai_decision":
            ai_decision,

        "message":
            "Screening pipeline completed through AI recommendation. Officer final decision is required.",
    }