# backend/services/ocr.py

import os
import httpx


# =========================================================
# OCR SERVICE CONFIGURATION
# =========================================================

OCR_SERVICE_URL = os.getenv(
    "OCR_SERVICE_URL",
    "http://10.109.60.3:8000"
)

OCR_ENDPOINT = os.getenv(
    "OCR_ENDPOINT",
    "/analyze-document"
)

OCR_TIMEOUT = float(
    os.getenv(
        "OCR_TIMEOUT",
        "120"
    )
)


# =========================================================
# OCR ANALYSIS
# =========================================================

async def analyze_document(
    file_bytes: bytes,
    filename: str,
    content_type: str,
):
    """
    Send an identity document to the external
    OCR + MRZ service.

    Remote OCR service:

        http://10.109.60.3:8000/analyze-document
    """

    url = (
        OCR_SERVICE_URL.rstrip("/")
        + "/"
        + OCR_ENDPOINT.lstrip("/")
    )

    files = {
        "file": (
            filename,
            file_bytes,
            content_type,
        )
    }

    timeout = httpx.Timeout(
        OCR_TIMEOUT,
        connect=20.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        response = await client.post(
            url,
            files=files,
        )

    return response