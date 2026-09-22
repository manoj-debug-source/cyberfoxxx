import os
import httpx


TAMPER_SERVICE_URL = os.getenv(
    "TAMPER_SERVICE_URL",
    "http://127.0.0.1:9000"
)


async def analyze_tamper(
    file_bytes: bytes,
    filename: str,
    content_type: str
):

    files = {
        "file": (
            filename,
            file_bytes,
            content_type
        )
    }

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(
            f"{TAMPER_SERVICE_URL}/predict",
            files=files
        )

    return response