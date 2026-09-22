# backend/routes/ocr.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import httpx

from utils.jwt import get_current_user
from services.ocr import analyze_document


router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR & MRZ"],
)


# =========================================================
# ALLOWED FILE TYPES
# =========================================================

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_value(value):
    """
    Convert an OCR value into a clean string.
    """

    if value is None:
        return None

    if isinstance(value, str):
        value = " ".join(value.strip().split())
        return value if value else None

    return value


# =========================================================
# FIELD NORMALIZATION
# =========================================================

def normalize_key(key):
    """
    Normalize field names so different naming styles
    can be compared consistently.
    """

    return (
        str(key)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


# =========================================================
# RECURSIVE FIELD SEARCH
# =========================================================

def find_field(data, possible_names):
    """
    Recursively search OCR data for a field.

    Supports:
        {
            "name": "JOHN"
        }

    and:

        {
            "extracted_fields": [
                {
                    "field_name": "given_names",
                    "value": "JOHN"
                }
            ]
        }
    """

    normalized_names = {
        normalize_key(name)
        for name in possible_names
    }

    # -----------------------------------------------------
    # Dictionary
    # -----------------------------------------------------

    if isinstance(data, dict):

        # Direct dictionary keys
        for key, value in data.items():

            normalized_key = normalize_key(key)

            if normalized_key in normalized_names:

                cleaned = normalize_value(value)

                if cleaned is not None:
                    return cleaned

        # Special OCR structure:
        #
        # extracted_fields = [
        #   {
        #       "field_name": "given_names",
        #       "value": "JOHN"
        #   }
        # ]

        field_name = data.get("field_name")

        if field_name is not None:

            normalized_field_name = normalize_key(
                field_name
            )

            if normalized_field_name in normalized_names:

                value = data.get("value")

                cleaned = normalize_value(value)

                if cleaned is not None:
                    return cleaned

        # Search nested structures
        for value in data.values():

            result = find_field(
                value,
                normalized_names
            )

            if result is not None:
                return result

    # -----------------------------------------------------
    # List
    # -----------------------------------------------------

    elif isinstance(data, list):

        for item in data:

            result = find_field(
                item,
                normalized_names
            )

            if result is not None:
                return result

    return None


# =========================================================
# EXTRACT IDENTITY FIELDS
# =========================================================

def extract_identity_fields(data):
    """
    Extract identity information from the OCR/MRZ response.

    No values are invented.
    Only values actually returned by the OCR service
    are used.
    """

    if not isinstance(data, dict):
        return {}

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    name = find_field(
        data,
        {
            "name",
            "full_name",
            "fullname",
            "passenger_name",
            "holder_name",
            "holder",
            "given_name",
            "given_names",
        },
    )

    # -----------------------------------------------------
    # DATE OF BIRTH
    # -----------------------------------------------------

    date_of_birth = find_field(
        data,
        {
            "date_of_birth",
            "dob",
            "birth_date",
            "birthdate",
            "dateofbirth",
        },
    )

    # -----------------------------------------------------
    # DOCUMENT NUMBER
    # -----------------------------------------------------

    document_number = find_field(
        data,
        {
            "document_number",
            "document_no",
            "document_id",
            "id_number",
            "id_no",
            "idnumber",
            "passport_number",
            "passport_no",
            "passportnumber",
        },
    )

    # -----------------------------------------------------
    # NATIONALITY
    # -----------------------------------------------------

    nationality = find_field(
        data,
        {
            "nationality",
            "nationality_code",
            "country_code",
            "nationalitycode",
        },
    )

    # -----------------------------------------------------
    # GENDER
    # -----------------------------------------------------

    gender = find_field(
        data,
        {
            "gender",
            "sex",
        },
    )

    # -----------------------------------------------------
    # ADDRESS
    # -----------------------------------------------------

    address = find_field(
        data,
        {
            "address",
            "residential_address",
            "permanent_address",
        },
    )

    identity_fields = {}

    if name is not None:
        identity_fields["name"] = name

    if date_of_birth is not None:
        identity_fields["date_of_birth"] = date_of_birth

    if document_number is not None:
        identity_fields["document_number"] = document_number

    if nationality is not None:
        identity_fields["nationality"] = nationality

    if gender is not None:
        identity_fields["gender"] = gender

    if address is not None:
        identity_fields["address"] = address

    return identity_fields


# =========================================================
# OCR ANALYSIS ENDPOINT
# =========================================================

@router.post("/analyze")
async def analyze_ocr(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    CYBERFOXXX OCR endpoint.

    Frontend calls:

        POST /api/ocr/analyze

    This backend then forwards the document to:

        POST http://10.109.60.3:8000/analyze-document
    """

    # -----------------------------------------------------
    # 1. Validate file type
    # -----------------------------------------------------

    if file.content_type not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and PDF files are allowed.",
        )

    # -----------------------------------------------------
    # 2. Read uploaded file
    # -----------------------------------------------------

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    # -----------------------------------------------------
    # 3. Send document to OCR service
    # -----------------------------------------------------

    try:

        response = await analyze_document(
            file_bytes=file_bytes,
            filename=file.filename or "document",
            content_type=(
                file.content_type
                or "application/octet-stream"
            ),
        )

    except httpx.TimeoutException as exc:

        raise HTTPException(
            status_code=504,
            detail="OCR service timed out.",
        ) from exc

    except httpx.RequestError as exc:

        raise HTTPException(
            status_code=502,
            detail=f"OCR service unavailable: {str(exc)}",
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=f"OCR service connection failed: {str(exc)}",
        ) from exc

    # -----------------------------------------------------
    # 4. Check OCR service response
    # -----------------------------------------------------

    if response.status_code >= 400:

        raise HTTPException(
            status_code=502,
            detail={
                "message": "OCR service returned an error",
                "service_status": response.status_code,
                "service_response": response.text,
            },
        )

    # -----------------------------------------------------
    # 5. Parse JSON
    # -----------------------------------------------------

    try:

        result = response.json()

    except ValueError as exc:

        raise HTTPException(
            status_code=502,
            detail="OCR service returned invalid JSON.",
        ) from exc

    # -----------------------------------------------------
    # 6. Extract normalized identity fields
    # -----------------------------------------------------

    identity_fields = extract_identity_fields(
        result
    )

    document_number = identity_fields.get(
        "document_number"
    )

    # -----------------------------------------------------
    # 7. Return CYBERFOXXX response
    # -----------------------------------------------------

    return {
        "success": True,
        "filename": file.filename,
        "processed_by": current_user.get("username"),
        "document_number": document_number,
        "identity_fields": identity_fields,
        "ocr_result": result,
    }