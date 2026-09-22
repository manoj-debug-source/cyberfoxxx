# backend/routes/pipeline.py

import os
import hashlib
import uuid
from datetime import datetime, timezone

import httpx

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    BackgroundTasks,
)

from utils.jwt import get_current_user
from database.mongodb import db

from services.ocr import analyze_document
from services.tamper_detection import analyze_tamper
from services.blockchain import create_ledger_event


router = APIRouter()


# ==========================================================
# CONFIGURATION
# ==========================================================

RISK_SERVICE_URL = os.getenv(
    "RISK_SERVICE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")

RISK_CALIBRATION_URL = (
    f"{RISK_SERVICE_URL}/api/risk/calibrate"
)


# ----------------------------------------------------------
# Teammate anomaly/document screening service
# ----------------------------------------------------------

DOCUMENT_SCREENING_URL = os.getenv(
    "DOCUMENT_SCREENING_URL",
    "http://10.109.60.79:8000",
).rstrip("/")

DOCUMENT_SCREENING_ENDPOINT = os.getenv(
    "DOCUMENT_SCREENING_ENDPOINT",
    "/api/v1/document/screen",
)

DOCUMENT_SCREENING_TIMEOUT = float(
    os.getenv(
        "DOCUMENT_SCREENING_TIMEOUT",
        "60",
    )
)

DOCUMENT_SCREENING_FULL_URL = (
    f"{DOCUMENT_SCREENING_URL}"
    f"{DOCUMENT_SCREENING_ENDPOINT}"
)


# ----------------------------------------------------------
# OCR service
#
# Actual working OCR machine:
#
#     10.109.60.3:8000
#
# Endpoint:
#
#     /analyze-document
# ----------------------------------------------------------

OCR_SERVICE_URL = os.getenv(
    "OCR_SERVICE_URL",
    "http://10.109.60.3:8000",
).rstrip("/")


# ==========================================================
# FILE TYPES
# ==========================================================

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


DOCUMENT_SCREENING_SUPPORTED_TYPES = {
    "image/jpeg",
    "image/png",
}


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def normalize(value):
    """
    Normalize text for reliable comparison.
    """

    if value is None:
        return ""

    return " ".join(
        str(value).strip().upper().split()
    )


def normalize_probability(value):
    """
    Convert probability/percentage to 0..1.
    """

    if value is None:
        return 0.0

    try:

        probability = float(value)

        if probability > 1:
            probability /= 100.0

        return max(
            0.0,
            min(1.0, probability),
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


# ==========================================================
# RECURSIVE VALUE SEARCH
# ==========================================================

def find_value_recursive(
    data,
    possible_keys,
):
    """
    Recursively search dictionaries and lists.

    Handles OCR responses where fields may appear
    at different nesting levels.
    """

    if isinstance(data, dict):

        # --------------------------------------------------
        # Direct key search
        # --------------------------------------------------

        for key in possible_keys:

            if key in data:

                value = data.get(key)

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):

                    return value

        # --------------------------------------------------
        # Case-insensitive normalized key search
        # --------------------------------------------------

        normalized_possible_keys = {
            normalize_key(key)
            for key in possible_keys
        }

        for key, value in data.items():

            if (
                normalize_key(key)
                in normalized_possible_keys
            ):

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):

                    return value

        # --------------------------------------------------
        # Recursive search
        # --------------------------------------------------

        for value in data.values():

            found = find_value_recursive(
                value,
                possible_keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):

                return found

    elif isinstance(data, list):

        for item in data:

            found = find_value_recursive(
                item,
                possible_keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):

                return found

    return None


def normalize_key(value):
    """
    Normalize a dictionary key so that:

        passport_number
        passportNumber
        Passport Number

    can be treated similarly.
    """

    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


# ==========================================================
# DOCUMENT NUMBER
# ==========================================================

def extract_document_number(data):
    """
    Extract passport/document number.

    Supports the actual OCR response:

        passport_number
    """

    value = find_value_recursive(
        data,
        [
            "document_number",
            "documentNumber",
            "document_no",
            "documentNo",
            "passport_number",
            "passportNumber",
            "passport_no",
            "passportNo",
            "id_number",
            "idNumber",
        ],
    )

    if value:

        return str(value).strip()

    return None


# ==========================================================
# OCR CONFIDENCE
# ==========================================================

def extract_ocr_confidence(data):
    """
    Extract OCR confidence.

    Supports:

        ocr_confidence
        confidence
        average_word_confidence
    """

    value = find_value_recursive(
        data,
        [
            "ocr_confidence",
            "ocrConfidence",
            "average_word_confidence",
            "averageWordConfidence",
            "confidence_score",
            "confidenceScore",
        ],
    )

    if value is None:

        return 0.0

    try:

        confidence = float(value)

        if confidence > 1:

            confidence /= 100.0

        return max(
            0.0,
            min(1.0, confidence),
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0.0


# ==========================================================
# MRZ RESULT
# ==========================================================

def extract_mrz_result(data):

    if not isinstance(data, dict):

        return None

    result = find_value_recursive(
        data,
        [
            "mrz",
            "MRZ",
            "mrz_result",
            "mrzResult",
        ],
    )

    return result


# ==========================================================
# NESTED VALUE
# ==========================================================

def extract_nested_value(
    data,
    keys,
):
    """
    Generic recursive field extractor.
    """

    value = find_value_recursive(
        data,
        keys,
    )

    if value in (
        None,
        "",
        [],
        {},
    ):

        return None

    return value


# ==========================================================
# OCR FIELD EXTRACTION
# ==========================================================

def extract_ocr_identity_fields(
    ocr_result,
):
    """
    Convert the OCR/MRZ response into the normalized
    identity structure used by CYBERFOXXX.

    Actual OCR response example:

        given_names
        nationality
        sex
        passport_number
        date_of_birth

    becomes:

        name
        nationality
        gender
        document_number
        date_of_birth
    """

    if not isinstance(
        ocr_result,
        (dict, list),
    ):

        return {}


    extracted = {}


    # ======================================================
    # NAME
    # ======================================================

    name = extract_nested_value(
        ocr_result,
        [
            "name",
            "full_name",
            "fullName",
            "full name",
            "given_names",
            "givenNames",
            "given_name",
            "givenName",
            "passenger_name",
            "passengerName",
            "holder_name",
            "holderName",
        ],
    )

    if name:

        extracted["name"] = str(
            name
        ).strip()


    # ======================================================
    # DATE OF BIRTH
    # ======================================================

    date_of_birth = extract_nested_value(
        ocr_result,
        [
            "date_of_birth",
            "dateOfBirth",
            "dob",
            "birth_date",
            "birthDate",
            "date of birth",
        ],
    )

    if date_of_birth:

        extracted["date_of_birth"] = str(
            date_of_birth
        ).strip()


    # ======================================================
    # DOCUMENT NUMBER
    # ======================================================

    document_number = (
        extract_document_number(
            ocr_result
        )
    )

    if document_number:

        extracted["document_number"] = (
            document_number
        )


    # ======================================================
    # NATIONALITY
    # ======================================================

    nationality = extract_nested_value(
        ocr_result,
        [
            "nationality",
            "nationality_code",
            "nationalityCode",
            "country_code",
            "countryCode",
        ],
    )

    if nationality:

        extracted["nationality"] = str(
            nationality
        ).strip()


    # ======================================================
    # GENDER
    # ======================================================

    gender = extract_nested_value(
        ocr_result,
        [
            "gender",
            "sex",
        ],
    )

    if gender:

        extracted["gender"] = str(
            gender
        ).strip()


    # ======================================================
    # ADDRESS
    # ======================================================

    address = extract_nested_value(
        ocr_result,
        [
            "address",
            "residential_address",
            "permanent_address",
        ],
    )

    if address:

        extracted["address"] = str(
            address
        ).strip()


    return extracted


# ==========================================================
# WATCHLIST IDENTITY EXTRACTION
# ==========================================================

def extract_watchlist_identity(
    ocr_result,
):
    """
    Convert OCR/MRZ output into exactly the structure
    expected by the Watchlist module.
    """

    return extract_ocr_identity_fields(
        ocr_result
    )


# ==========================================================
# WATCHLIST MATCHING
# ==========================================================

def calculate_watchlist_match(
    extracted,
    record,
):
    """
    Compare extracted identity information
    with one active watchlist record.
    """

    matched_fields = []


    # ======================================================
    # NAME
    # ======================================================

    extracted_name = normalize(
        extracted.get("name")
    )

    record_name = normalize(
        record.get("name")
    )

    if (
        extracted_name
        and record_name
        and extracted_name == record_name
    ):

        matched_fields.append(
            "name"
        )


    # ======================================================
    # DATE OF BIRTH
    # ======================================================

    extracted_dob = normalize(
        extracted.get("date_of_birth")
    )

    record_dob = normalize(
        record.get("date_of_birth")
    )

    if (
        extracted_dob
        and record_dob
        and extracted_dob == record_dob
    ):

        matched_fields.append(
            "date_of_birth"
        )


    # ======================================================
    # DOCUMENT NUMBER
    # ======================================================

    extracted_document = normalize(
        extracted.get("document_number")
    )

    record_document = normalize(
        record.get("document_number")
    )

    if (
        extracted_document
        and record_document
        and extracted_document
        == record_document
    ):

        matched_fields.append(
            "document_number"
        )


    # ======================================================
    # NATIONALITY
    # ======================================================

    extracted_nationality = normalize(
        extracted.get("nationality")
    )

    record_nationality = normalize(
        record.get("nationality")
    )

    if (
        extracted_nationality
        and record_nationality
        and extracted_nationality
        == record_nationality
    ):

        matched_fields.append(
            "nationality"
        )


    # ======================================================
    # SCORE
    # ======================================================

    score = 0.0

    if "name" in matched_fields:

        score += 0.40

    if "date_of_birth" in matched_fields:

        score += 0.20

    if "document_number" in matched_fields:

        score += 0.30

    if "nationality" in matched_fields:

        score += 0.10


    return (
        score,
        matched_fields,
    )


# ==========================================================
# PERFORM WATCHLIST CHECK
# ==========================================================

async def perform_watchlist_check(
    screening_id,
    ocr_result,
):
    """
    Perform watchlist matching using OCR/MRZ identity data.
    """

    # ------------------------------------------------------
    # Extract normalized identity
    # ------------------------------------------------------

    extracted = extract_watchlist_identity(
        ocr_result
    )

    print(
        f"[WATCHLIST] Extracted identity: "
        f"{screening_id} | {extracted}"
    )


    # ------------------------------------------------------
    # Store identity fields
    # ------------------------------------------------------

    await db.screenings.update_one(
        {
            "screening_id":
                screening_id,
        },
        {
            "$set": {

                "extracted_fields":
                    extracted,

                "watchlist_input":
                    extracted,
            }
        },
    )


    # ------------------------------------------------------
    # Check identity availability
    # ------------------------------------------------------

    has_identity_data = any(
        extracted.get(key)
        for key in [
            "name",
            "date_of_birth",
            "document_number",
            "nationality",
        ]
    )


    if not has_identity_data:

        result = {

            "status":
                "PENDING",

            "match_found":
                False,

            "match_type":
                None,

            "match_score":
                0.0,

            "matched_fields":
                [],

            "record_id":
                None,

            "category":
                None,

            "watchlist_probability":
                0.0,

            "message":
                (
                    "Identity information is not "
                    "available for watchlist screening."
                ),

            "checked_at":
                datetime.now(
                    timezone.utc
                ),
        }


        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "watchlist":
                        result,

                    "pipeline.watchlist": {

                        "status":
                            "PENDING",

                        "result":
                            result,
                    },
                }
            },
        )


        return result


    # ------------------------------------------------------
    # Search active records
    # ------------------------------------------------------

    records = db.watchlist_records.find(
        {
            "status":
                "ACTIVE",
        }
    )


    best_match = None

    best_score = 0.0

    best_fields = []


    async for record in records:

        score, matched_fields = (
            calculate_watchlist_match(
                extracted,
                record,
            )
        )

        print(
            f"[WATCHLIST] Comparing "
            f"{screening_id} with "
            f"{record.get('record_id')} "
            f"score={score}"
        )


        if score > best_score:

            best_score = score

            best_match = record

            best_fields = matched_fields


    # ======================================================
    # DETERMINE RESULT
    # ======================================================

    if best_score >= 0.70:

        status = "MATCH"

        match_found = True

        match_type = (
            "CONFIRMED_MATCH"
        )

        watchlist_probability = 1.0

        message = (
            "A matching authorized "
            "watchlist record was found."
        )

    elif best_score >= 0.40:

        status = "POTENTIAL_MATCH"

        match_found = True

        match_type = (
            "POTENTIAL_MATCH"
        )

        watchlist_probability = 0.5

        message = (
            "A potential watchlist match "
            "requires officer review."
        )

    else:

        status = "NO_MATCH"

        match_found = False

        match_type = None

        watchlist_probability = 0.0

        message = (
            "No matching authorized "
            "watchlist record was found."
        )


    # ======================================================
    # RECORD DETAILS
    # ======================================================

    record_id = None

    category = None

    if best_match:

        record_id = best_match.get(
            "record_id"
        )

        category = best_match.get(
            "category"
        )


    # ======================================================
    # FINAL RESULT
    # ======================================================

    result = {

        "status":
            status,

        "match_found":
            match_found,

        "match_type":
            match_type,

        "match_score":
            round(
                best_score,
                4,
            ),

        "matched_fields":
            best_fields,

        "record_id":
            record_id,

        "category":
            category,

        "watchlist_probability":
            watchlist_probability,

        "message":
            message,

        "checked_at":
            datetime.now(
                timezone.utc
            ),
    }


    # ======================================================
    # SAVE RESULT
    # ======================================================

    await db.screenings.update_one(
        {
            "screening_id":
                screening_id,
        },
        {
            "$set": {

                "watchlist":
                    result,

                "pipeline.watchlist": {

                    "status":
                        "COMPLETED",

                    "result":
                        result,

                    "match_score":
                        round(
                            best_score,
                            4,
                        ),

                    "match_found":
                        match_found,

                    "match_type":
                        match_type,
                },
            }
        },
    )


    print(
        f"[WATCHLIST] Completed: "
        f"{screening_id} | "
        f"status={status} | "
        f"score={best_score}"
    )


    return result


# ==========================================================
# TEAMMATE DOCUMENT SCREENING
# ==========================================================

async def screen_document_with_teammate(
    file_bytes,
    filename,
    content_type,
    document_type="PASSPORT",
):
    """
    Call teammate's anomaly/document screening service.
    """

    files = {
        "image": (
            filename,
            file_bytes,
            content_type,
        )
    }

    data = {
        "document_type":
            document_type,
    }


    async with httpx.AsyncClient(
        timeout=
            DOCUMENT_SCREENING_TIMEOUT,
    ) as client:

        response = await client.post(
            DOCUMENT_SCREENING_FULL_URL,
            files=files,
            data=data,
        )


    if response.status_code >= 400:

        raise RuntimeError(
            "Teammate Document Screening "
            "service returned HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )


    try:

        result = response.json()

    except ValueError as exc:

        raise RuntimeError(
            "Teammate Document Screening "
            "service returned invalid JSON."
        ) from exc


    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "Teammate Document Screening "
            "service returned an unexpected response."
        )


    return result


# ==========================================================
# ANOMALY VALUE EXTRACTION
# ==========================================================

def extract_anomaly_value(
    data,
    keys,
):
    """
    Search both top-level and nested anomaly_result
    structures.

    Supports responses such as:

        {
            "anomaly_score": 0.08
        }

    and:

        {
            "anomaly_result": {
                "anomaly_score": 0.08
            }
        }
    """

    value = find_value_recursive(
        data,
        keys,
    )

    return value


# ==========================================================
# BACKGROUND PIPELINE
# ==========================================================

async def process_pipeline_background(
    screening_id,
    file_bytes,
    filename,
    content_type,
    username,
    document_hash,
):

    print(
        f"[PIPELINE] Started: "
        f"{screening_id}"
    )


    # ======================================================
    # VARIABLES
    # ======================================================

    ocr_result = None

    document_number = None

    ocr_confidence = 0.0

    mrz_result = None

    tamper_result = None

    tamper_probability = 0.0

    document_screening_result = None

    anomaly_probability = 0.0

    watchlist_result = None

    watchlist_probability = 0.0

    risk_result = None

    ai_decision = None


    try:

        # ==================================================
        # 1. OCR + MRZ
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "OCR_PROCESSING",

                    "pipeline.ocr": {

                        "status":
                            "PROCESSING",
                    },

                    "pipeline.mrz": {

                        "status":
                            "PROCESSING",
                    },
                }
            },
        )


        try:

            # ------------------------------------------------
            # Call actual OCR machine
            #
            # services.ocr reads:
            #
            # 10.109.60.3:8000/analyze-document
            # ------------------------------------------------

            ocr_response = (
                await analyze_document(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=content_type,
                )
            )


            if (
                ocr_response.status_code
                >= 400
            ):

                raise RuntimeError(
                    "OCR service returned HTTP "
                    f"{ocr_response.status_code}: "
                    f"{ocr_response.text}"
                )


            ocr_result = (
                ocr_response.json()
            )


            print(
                f"[PIPELINE] OCR response: "
                f"{screening_id} | "
                f"{ocr_result}"
            )


            # ------------------------------------------------
            # Extract fields
            # ------------------------------------------------

            document_number = (
                extract_document_number(
                    ocr_result
                )
            )


            ocr_confidence = (
                extract_ocr_confidence(
                    ocr_result
                )
            )


            mrz_result = (
                extract_mrz_result(
                    ocr_result
                )
            )


            # ------------------------------------------------
            # IMPORTANT:
            #
            # Normalize OCR fields immediately.
            #
            # given_names      → name
            # passport_number  → document_number
            # sex              → gender
            # ------------------------------------------------

            extracted_identity = (
                extract_ocr_identity_fields(
                    ocr_result
                )
            )


            # ------------------------------------------------
            # OCR status
            # ------------------------------------------------

            ocr_status = str(
                ocr_result.get(
                    "status",
                    "",
                )
            ).lower()


            if ocr_status in {
                "rescan_required",
                "failed",
                "error",
            }:

                pipeline_ocr_status = (
                    "COMPLETED_WITH_WARNING"
                )

            else:

                pipeline_ocr_status = (
                    "COMPLETED"
                )


            # ------------------------------------------------
            # Save OCR + normalized fields
            # ------------------------------------------------

            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "ocr":
                            ocr_result,

                        "document_number":
                            document_number,

                        "extracted_fields":
                            extracted_identity,

                        "pipeline.ocr": {

                            "status":
                                pipeline_ocr_status,

                            "result":
                                ocr_result,

                            "document_number":
                                document_number,

                            "confidence":
                                ocr_confidence,

                            "extracted_fields":
                                extracted_identity,
                        },

                        "pipeline.mrz": {

                            "status":
                                "COMPLETED",

                            "result":
                                mrz_result,
                        },
                    }
                },
            )


            print(
                f"[PIPELINE] OCR completed: "
                f"{screening_id} | "
                f"identity="
                f"{extracted_identity}"
            )


        except Exception as e:

            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "pipeline.ocr": {

                            "status":
                                "FAILED",

                            "error":
                                str(e),
                        },

                        "pipeline.mrz": {

                            "status":
                                "FAILED",

                            "error":
                                str(e),
                        },
                    }
                },
            )


            print(
                f"[PIPELINE] OCR failed: "
                f"{screening_id}: {e}"
            )


        # ==================================================
        # 2. TAMPER DETECTION
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "TAMPER_PROCESSING",

                    "pipeline.tamper": {

                        "status":
                            "PROCESSING",
                    },
                }
            },
        )


        if content_type in {
            "image/jpeg",
            "image/png",
        }:

            try:

                tamper_response = (
                    await analyze_tamper(
                        file_bytes=file_bytes,
                        filename=filename,
                        content_type=content_type,
                    )
                )


                if (
                    tamper_response.status_code
                    >= 400
                ):

                    raise RuntimeError(
                        "Tamper Detection service "
                        "returned HTTP "
                        f"{tamper_response.status_code}"
                    )


                tamper_result = (
                    tamper_response.json()
                )


                if isinstance(
                    tamper_result,
                    dict,
                ):

                    possible_probability = (
                        find_value_recursive(
                            tamper_result,
                            [
                                "tamper_probability",
                                "probability",
                                "tampered_probability",
                            ],
                        )
                    )


                    tamper_probability = (
                        normalize_probability(
                            possible_probability
                        )
                    )


                await db.screenings.update_one(
                    {
                        "screening_id":
                            screening_id,
                    },
                    {
                        "$set": {

                            "tamper_analysis":
                                tamper_result,

                            "pipeline.tamper": {

                                "status":
                                    "COMPLETED",

                                "result":
                                    tamper_result,

                                "probability":
                                    tamper_probability,
                            },
                        }
                    },
                )


                print(
                    f"[PIPELINE] Tamper completed: "
                    f"{screening_id}"
                )


            except Exception as e:

                await db.screenings.update_one(
                    {
                        "screening_id":
                            screening_id,
                    },
                    {
                        "$set": {

                            "pipeline.tamper": {

                                "status":
                                    "FAILED",

                                "error":
                                    str(e),
                            },
                        }
                    },
                )


                print(
                    f"[PIPELINE] Tamper failed: "
                    f"{screening_id}: {e}"
                )


        else:

            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "pipeline.tamper": {

                            "status":
                                "SKIPPED",

                            "reason":
                                (
                                    "PDF files are not "
                                    "currently supported "
                                    "by local tamper "
                                    "detection."
                                ),
                        },
                    }
                },
            )


        # ==================================================
        # 3. ANOMALY / DOCUMENT SCREENING
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "ANOMALY_PROCESSING",

                    "pipeline.anomaly": {

                        "status":
                            "PROCESSING",
                    },
                }
            },
        )


        if (
            content_type
            in DOCUMENT_SCREENING_SUPPORTED_TYPES
        ):

            try:

                document_screening_result = (
                    await screen_document_with_teammate(
                        file_bytes=file_bytes,
                        filename=filename,
                        content_type=content_type,
                        document_type="PASSPORT",
                    )
                )


                # ------------------------------------------------
                # Extract anomaly score from any nesting level
                # ------------------------------------------------

                anomaly_score_value = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "anomaly_score",
                            "anomaly_probability",
                            "score",
                        ],
                    )
                )


                anomaly_probability = (
                    normalize_probability(
                        anomaly_score_value
                    )
                )


                teammate_is_anomaly = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "is_anomaly",
                        ],
                    )
                )


                teammate_severity = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "severity",
                        ],
                    )
                )


                teammate_decision = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "decision",
                        ],
                    )
                )


                tampering_detected = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "tampering_detected",
                        ],
                    )
                )


                validation_failed = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "validation_failed",
                        ],
                    )
                )


                detected_fraud_types = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "detected_fraud_types",
                        ]
                    )
                    or []
                )


                evidence = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "evidence",
                        ]
                    )
                    or []
                )


                recommended_action = (
                    extract_anomaly_value(
                        document_screening_result,
                        [
                            "recommended_action",
                        ]
                    )
                )


                screening_confidence = (
                    normalize_probability(
                        extract_anomaly_value(
                            document_screening_result,
                            [
                                "confidence",
                            ],
                        )
                    )
                )


                await db.screenings.update_one(
                    {
                        "screening_id":
                            screening_id,
                    },
                    {
                        "$set": {

                            "document_screening":
                                document_screening_result,

                            "anomaly_analysis":
                                document_screening_result,

                            "anomaly":
                                document_screening_result,

                            "pipeline.anomaly": {

                                "status":
                                    "COMPLETED",

                                "score":
                                    anomaly_probability,

                                "is_anomaly":
                                    teammate_is_anomaly,

                                "severity":
                                    teammate_severity,

                                "decision":
                                    teammate_decision,

                                "confidence":
                                    screening_confidence,

                                "tampering_detected":
                                    tampering_detected,

                                "validation_failed":
                                    validation_failed,

                                "detected_fraud_types":
                                    detected_fraud_types,

                                "evidence":
                                    evidence,

                                "recommended_action":
                                    recommended_action,

                                "result":
                                    document_screening_result,
                            },
                        }
                    },
                )


                print(
                    f"[PIPELINE] Anomaly completed: "
                    f"{screening_id} | "
                    f"score="
                    f"{anomaly_probability}"
                )


            except httpx.RequestError as e:

                await db.screenings.update_one(
                    {
                        "screening_id":
                            screening_id,
                    },
                    {
                        "$set": {

                            "pipeline.anomaly": {

                                "status":
                                    "FAILED",

                                "error":
                                    (
                                        "Teammate Document "
                                        "Screening service "
                                        "unavailable"
                                    ),
                            },
                        }
                    },
                )


                print(
                    f"[PIPELINE] Remote anomaly "
                    f"connection failed: "
                    f"{screening_id}: {e}"
                )


            except Exception as e:

                await db.screenings.update_one(
                    {
                        "screening_id":
                            screening_id,
                    },
                    {
                        "$set": {

                            "pipeline.anomaly": {

                                "status":
                                    "FAILED",

                                "error":
                                    str(e),
                            },
                        }
                    },
                )


                print(
                    f"[PIPELINE] Anomaly failed: "
                    f"{screening_id}: {e}"
                )


        else:

            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "pipeline.anomaly": {

                            "status":
                                "SKIPPED",

                            "reason":
                                (
                                    "Remote document "
                                    "screening currently "
                                    "accepts JPG/PNG only."
                                ),
                        },
                    }
                },
            )


        # ==================================================
        # 4. WATCHLIST CHECK
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "WATCHLIST_PROCESSING",

                    "pipeline.watchlist": {

                        "status":
                            "PROCESSING",
                    },
                }
            },
        )


        try:

            watchlist_result = (
                await perform_watchlist_check(
                    screening_id=
                        screening_id,

                    ocr_result=
                        ocr_result or {},
                )
            )


            watchlist_probability = (
                normalize_probability(
                    watchlist_result.get(
                        "watchlist_probability",
                        0.0,
                    )
                )
            )


            print(
                f"[PIPELINE] Watchlist completed: "
                f"{screening_id} | "
                f"status="
                f"{watchlist_result.get('status')} | "
                f"score="
                f"{watchlist_result.get('match_score', 0.0)}"
            )


        except Exception as e:

            watchlist_probability = 0.0

            watchlist_result = {

                "status":
                    "FAILED",

                "match_found":
                    False,

                "match_type":
                    None,

                "match_score":
                    0.0,

                "matched_fields":
                    [],

                "record_id":
                    None,

                "category":
                    None,

                "watchlist_probability":
                    0.0,

                "message":
                    str(e),

                "checked_at":
                    datetime.now(
                        timezone.utc
                    ),
            }


            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "watchlist":
                            watchlist_result,

                        "pipeline.watchlist": {

                            "status":
                                "FAILED",

                            "result":
                                watchlist_result,

                            "error":
                                str(e),
                        },
                    }
                },
            )


            print(
                f"[PIPELINE] Watchlist failed: "
                f"{screening_id}: {e}"
            )


        # ==================================================
        # 5. MODULES NOT YET CONNECTED
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "pipeline.identity_validation": {

                        "status":
                            "PENDING",

                        "reason":
                            (
                                "Identity validation "
                                "endpoint is not yet "
                                "connected."
                            ),
                    },

                    "pipeline.face": {

                        "status":
                            "PENDING",

                        "reason":
                            (
                                "Face and liveness "
                                "endpoint is not yet "
                                "connected."
                            ),
                    },

                    "pipeline.identity_linkage": {

                        "status":
                            "PENDING",

                        "reason":
                            (
                                "Identity linkage runs "
                                "after officer final "
                                "decision."
                            ),
                    },
                }
            },
        )


        # ==================================================
        # 6. RISK CALIBRATION
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "RISK_PROCESSING",

                    "pipeline.risk": {

                        "status":
                            "PROCESSING",
                    },
                }
            },
        )


        try:

            mrz_confidence = (
                ocr_confidence
                if mrz_result is not None
                else 0.0
            )


            risk_input = {

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

                # Face module not connected yet.
                "face_match_probability":
                    1.0,

                "watchlist_probability":
                    watchlist_probability,

                # Identity linkage happens after
                # officer final decision.
                "identity_linkage_score":
                    1.0,
            }


            print(
                f"[PIPELINE] Risk input: "
                f"{screening_id} | "
                f"OCR="
                f"{ocr_confidence} | "
                f"TAMPER="
                f"{tamper_probability} | "
                f"ANOMALY="
                f"{anomaly_probability} | "
                f"WATCHLIST="
                f"{watchlist_probability}"
            )


            async with httpx.AsyncClient(
                timeout=30.0,
            ) as client:

                response = await client.post(
                    RISK_CALIBRATION_URL,
                    json=risk_input,
                )


            if response.status_code != 200:

                raise RuntimeError(
                    "Risk Calibration service "
                    "returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text}"
                )


            risk_result = (
                response.json()
            )


            risk_level = str(
                risk_result.get(
                    "risk_level",
                    "",
                )
            ).upper()


            if not risk_level:

                risk_level = str(
                    risk_result.get(
                        "risk_level_name",
                        "",
                    )
                ).upper()


            # =================================================
            # AI RECOMMENDATION
            # =================================================

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

                ai_decision = "REVIEW"


            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "risk":
                            risk_result,

                        "ai_decision":
                            ai_decision,

                        "status":
                            "RISK_CALCULATED",

                        "risk_calculated_by":
                            username,

                        "pipeline.risk": {

                            "status":
                                "COMPLETED",

                            "result":
                                risk_result,

                            "provisional":
                                True,
                        },

                        "pipeline.decision": {

                            "status":
                                "COMPLETED",

                            "decision":
                                ai_decision,

                            "source":
                                "AI_RECOMMENDATION",

                            "provisional":
                                True,
                        },
                    }
                },
            )


            print(
                f"[PIPELINE] Risk completed: "
                f"{screening_id} | "
                f"AI={ai_decision}"
            )


        except Exception as e:

            await db.screenings.update_one(
                {
                    "screening_id":
                        screening_id,
                },
                {
                    "$set": {

                        "status":
                            "REVIEW_REQUIRED",

                        "pipeline.risk": {

                            "status":
                                "FAILED",

                            "error":
                                str(e),
                        },

                        "pipeline.decision": {

                            "status":
                                "COMPLETED",

                            "decision":
                                "REVIEW",

                            "source":
                                "AUTOMATION_FAILURE",

                            "reason":
                                (
                                    "Automated risk "
                                    "calibration could "
                                    "not be completed. "
                                    "Officer investigation "
                                    "required."
                                ),
                        },

                        "ai_decision":
                            "REVIEW",
                    }
                },
            )


            print(
                f"[PIPELINE] Risk failed; "
                f"case moved to REVIEW: "
                f"{screening_id}: {e}"
            )


        # ==================================================
        # 7. PIPELINE FINISHED
        # ==================================================

        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "pipeline.completed_at":
                        datetime.now(
                            timezone.utc
                        ),

                    "pipeline.status":
                        "COMPLETED",
                }
            },
        )


        print(
            f"[PIPELINE] COMPLETED: "
            f"{screening_id}"
        )


    except Exception as e:

        print(
            f"[PIPELINE] FATAL ERROR: "
            f"{screening_id}: {e}"
        )


        await db.screenings.update_one(
            {
                "screening_id":
                    screening_id,
            },
            {
                "$set": {

                    "status":
                        "REVIEW_REQUIRED",

                    "pipeline.status":
                        "FAILED",

                    "pipeline.fatal_error":
                        str(e),

                    "pipeline.decision": {

                        "status":
                            "COMPLETED",

                        "decision":
                            "REVIEW",

                        "source":
                            "PIPELINE_FAILURE",

                        "reason":
                            (
                                "Automated screening "
                                "pipeline failed. "
                                "Officer investigation "
                                "required."
                            ),
                    },

                    "ai_decision":
                        "REVIEW",
                }
            },
        )


# ==========================================================
# START PIPELINE
# ==========================================================

@router.post("/screen")
async def run_screening_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(
        get_current_user
    ),
):

    # ======================================================
    # 1. VALIDATE FILE
    # ======================================================

    if file.content_type not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only JPG, PNG and PDF files "
                "are allowed."
            ),
        )


    file_bytes = await file.read()


    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )


    # ======================================================
    # 2. BASIC DATA
    # ======================================================

    screening_id = (
        f"SCR-{uuid.uuid4().hex[:8].upper()}"
    )


    document_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()


    username = current_user.get(
        "username",
        "unknown",
    )


    filename = (
        file.filename
        or "document"
    )


    content_type = (
        file.content_type
        or "application/octet-stream"
    )


    # ======================================================
    # 3. CREATE INITIAL CASE
    # ======================================================

    screening = {

        "screening_id":
            screening_id,

        "filename":
            filename,

        "content_type":
            content_type,

        "document_hash":
            document_hash,

        "status":
            "PIPELINE_STARTED",

        "created_by":
            username,

        "created_at":
            datetime.now(
                timezone.utc
            ),

        "pipeline": {

            "status":
                "PROCESSING",

            "sha256": {

                "status":
                    "COMPLETED",

                "document_hash":
                    document_hash,
            },

            "ocr": {

                "status":
                    "PENDING",
            },

            "mrz": {

                "status":
                    "PENDING",
            },

            "tamper": {

                "status":
                    "PENDING",
            },

            "anomaly": {

                "status":
                    "PENDING",
            },

            "watchlist": {

                "status":
                    "PENDING",
            },

            "identity_validation": {

                "status":
                    "PENDING",
            },

            "face": {

                "status":
                    "PENDING",
            },

            "identity_linkage": {

                "status":
                    "PENDING",
            },

            "risk": {

                "status":
                    "PENDING",
            },

            "decision": {

                "status":
                    "PENDING",
            },
        },
    }


    await db.screenings.insert_one(
        screening
    )


    # ======================================================
    # 4. BLOCKCHAIN EVENT
    # ======================================================

    try:

        await create_ledger_event(
            screening_id=
                screening_id,

            event_type=
                "SCREENING_CREATED",

            document_hash=
                document_hash,

            created_by=
                username,
        )

    except Exception as e:

        print(
            f"[PIPELINE] Blockchain event failed: "
            f"{screening_id}: {e}"
        )


    # ======================================================
    # 5. BACKGROUND PROCESSING
    # ======================================================

    background_tasks.add_task(
        process_pipeline_background,

        screening_id,

        file_bytes,

        filename,

        content_type,

        username,

        document_hash,
    )


    # ======================================================
    # 6. RETURN IMMEDIATELY
    # ======================================================

    return {

        "success":
            True,

        "screening_id":
            screening_id,

        "created_by":
            username,

        "status":
            "PIPELINE_STARTED",

        "document": {

            "filename":
                filename,

            "content_type":
                content_type,

            "document_hash":
                document_hash,
        },

        "message":
            (
                "Screening created successfully. "
                "Automated pipeline processing "
                "started."
            ),
    }


# ==========================================================
# PIPELINE STATUS
# ==========================================================

@router.get("/{screening_id}")
async def get_pipeline_status(
    screening_id: str,
    current_user: dict = Depends(
        get_current_user
    ),
):

    screening = await db.screenings.find_one(
        {
            "screening_id":
                screening_id,
        },
        {
            "_id": 0,
        },
    )


    if not screening:

        raise HTTPException(
            status_code=404,
            detail="Screening not found.",
        )


    return {

        "success":
            True,

        "screening_id":
            screening_id,

        "status":
            screening.get(
                "status"
            ),

        "pipeline":
            screening.get(
                "pipeline"
            ),

        "ai_decision":
            screening.get(
                "ai_decision"
            ),

        "risk":
            screening.get(
                "risk"
            ),

        "anomaly":
            screening.get(
                "anomaly"
            ),

        "tamper_analysis":
            screening.get(
                "tamper_analysis"
            ),

        "ocr":
            screening.get(
                "ocr"
            ),

        "mrz":
            screening.get(
                "mrz"
            ),

        "watchlist":
            screening.get(
                "watchlist"
            ),

        "extracted_fields":
            screening.get(
                "extracted_fields"
            ),
    }