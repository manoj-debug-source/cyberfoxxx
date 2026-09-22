import os
import httpx


DOCUMENT_SCREENING_URL = os.getenv(
    "DOCUMENT_SCREENING_URL",
    "http://10.109.60.79:8000"
)

DOCUMENT_SCREENING_ENDPOINT = os.getenv(
    "DOCUMENT_SCREENING_ENDPOINT",
    "/api/v1/document/screen"
)


async def analyze_anomaly(
    file_bytes: bytes,
    filename: str,
    content_type: str
):
    """
    Forward the uploaded document to the teammate's
    Document Fraud & Tampering Screening API.

    External service:
    POST /api/v1/document/screen

    The external service performs:
    - ELA
    - Sensor noise inconsistency
    - EXIF forensics
    - ICAO 9303 MRZ validation
    - Expiry/temporal validation
    - Cross-field consistency
    """

    files = {
        "image": (
            filename,
            file_bytes,
            content_type
        )
    }

    data = {
        "document_type": "PASSPORT"
    }

    url = (
        f"{DOCUMENT_SCREENING_URL}"
        f"{DOCUMENT_SCREENING_ENDPOINT}"
    )

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(
            url,
            files=files,
            data=data
        )

    return response