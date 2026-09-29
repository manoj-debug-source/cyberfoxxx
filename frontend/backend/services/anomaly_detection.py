import os
import httpx


# ==========================================================
# EXTERNAL DOCUMENT SCREENING SERVICE
# ==========================================================

DOCUMENT_SCREENING_URL = os.getenv(
    "DOCUMENT_SCREENING_URL",
    "http://10.109.60.79:8000"
)

DOCUMENT_SCREENING_ENDPOINT = os.getenv(
    "DOCUMENT_SCREENING_ENDPOINT",
    "/api/v1/document/screen"
)


# ==========================================================
# ANALYZE DOCUMENT FOR ANOMALIES
# ==========================================================

async def analyze_anomaly(
    file_bytes: bytes,
    filename: str,
    content_type: str
):
    """
    Forward the uploaded document to the external
    Document Fraud & Tampering Screening API.

    External endpoint:
        POST /api/v1/document/screen

    The external service performs:

    - ELA analysis
    - Sensor noise inconsistency analysis
    - EXIF forensics
    - ICAO 9303 MRZ validation
    - Expiry / temporal validation
    - Cross-field consistency checks

    This service only forwards the document and returns
    the external service response. Interpretation of the
    returned anomaly score is handled by the CYBERFOXXX
    backend.
    """

    if not file_bytes:
        raise ValueError(
            "Document data is empty."
        )

    if not filename:
        filename = "document"

    if not content_type:
        content_type = "application/octet-stream"

    # ------------------------------------------------------
    # Multipart file
    # ------------------------------------------------------

    files = {
        "image": (
            filename,
            file_bytes,
            content_type
        )
    }

    # ------------------------------------------------------
    # External service form data
    # ------------------------------------------------------

    data = {
        "document_type": "PASSPORT"
    }

    # ------------------------------------------------------
    # Build endpoint URL safely
    # ------------------------------------------------------

    url = (
        f"{DOCUMENT_SCREENING_URL.rstrip('/')}/"
        f"{DOCUMENT_SCREENING_ENDPOINT.lstrip('/')}"
    )

    # ------------------------------------------------------
    # Send request
    # ------------------------------------------------------

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(
            url,
            files=files,
            data=data
        )

    return response