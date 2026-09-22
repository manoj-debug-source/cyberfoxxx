import os
import httpx


# =========================================================
# FACE SERVICE CONFIGURATION
# =========================================================

FACE_SERVICE_URL = os.getenv(
    "FACE_SERVICE_URL",
    "http://127.0.0.1:8002"
)

FACE_SERVICE_TIMEOUT = float(
    os.getenv("FACE_SERVICE_TIMEOUT", "60")
)


# =========================================================
# URL HELPER
# =========================================================

def build_face_url(endpoint: str) -> str:
    return (
        f"{FACE_SERVICE_URL.rstrip('/')}/"
        f"{endpoint.lstrip('/')}"
    )


# =========================================================
# COMMON VALIDATION
# =========================================================

def validate_file(
    file_bytes: bytes,
    filename: str,
    content_type: str
):
    if not file_bytes:
        raise ValueError("Face image is empty.")

    if not filename:
        filename = "face.jpg"

    if not content_type:
        content_type = "image/jpeg"

    return filename, content_type


# =========================================================
# EXTRACT ID FACE
# =========================================================

async def extract_id_face(
    file_bytes: bytes,
    filename: str,
    content_type: str
):

    filename, content_type = validate_file(
        file_bytes,
        filename,
        content_type
    )

    files = {
        "file": (
            filename,
            file_bytes,
            content_type
        )
    }

    url = build_face_url("/extract-id-face")

    try:

        async with httpx.AsyncClient(
            timeout=FACE_SERVICE_TIMEOUT
        ) as client:

            response = await client.post(
                url,
                files=files
            )

        return response

    except httpx.TimeoutException as exc:

        raise RuntimeError(
            "Face extraction service timed out."
        ) from exc

    except httpx.ConnectError as exc:

        raise RuntimeError(
            "Unable to connect to face extraction service."
        ) from exc

    except httpx.HTTPError as exc:

        raise RuntimeError(
            f"Face extraction service request failed: {exc}"
        ) from exc


# =========================================================
# LIVENESS CHECK
# =========================================================

async def liveness_check(
    session_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str
):

    if not session_id:
        raise ValueError("Session ID is required.")

    filename, content_type = validate_file(
        file_bytes,
        filename,
        content_type
    )

    files = {
        "file": (
            filename,
            file_bytes,
            content_type
        )
    }

    url = build_face_url("/liveness-check")

    try:

        async with httpx.AsyncClient(
            timeout=FACE_SERVICE_TIMEOUT
        ) as client:

            response = await client.post(
                url,
                params={
                    "session_id": session_id
                },
                files=files
            )

        return response

    except httpx.TimeoutException as exc:

        raise RuntimeError(
            "Liveness service timed out."
        ) from exc

    except httpx.ConnectError as exc:

        raise RuntimeError(
            "Unable to connect to liveness service."
        ) from exc

    except httpx.HTTPError as exc:

        raise RuntimeError(
            f"Liveness service request failed: {exc}"
        ) from exc


# =========================================================
# FACE VERIFICATION
# =========================================================

async def verify_face(
    session_id: str,
    file_bytes: bytes,
    filename: str,
    content_type: str
):

    if not session_id:
        raise ValueError("Session ID is required.")

    filename, content_type = validate_file(
        file_bytes,
        filename,
        content_type
    )

    files = {
        "file": (
            filename,
            file_bytes,
            content_type
        )
    }

    url = build_face_url("/verify")

    try:

        async with httpx.AsyncClient(
            timeout=FACE_SERVICE_TIMEOUT
        ) as client:

            response = await client.post(
                url,
                params={
                    "session_id": session_id
                },
                files=files
            )

        return response

    except httpx.TimeoutException as exc:

        raise RuntimeError(
            "Face verification service timed out."
        ) from exc

    except httpx.ConnectError as exc:

        raise RuntimeError(
            "Unable to connect to face verification service."
        ) from exc

    except httpx.HTTPError as exc:

        raise RuntimeError(
            f"Face verification service request failed: {exc}"
        ) from exc