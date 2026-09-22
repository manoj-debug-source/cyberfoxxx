import os
import httpx


IDENTITY_SERVICE_URL = os.getenv(
    "IDENTITY_SERVICE_URL",
    "http://10.22.84.235:8003"
)


async def validate_identity(identity_data: dict):
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{IDENTITY_SERVICE_URL}/validate-identity",
            json=identity_data
        )

    return response
