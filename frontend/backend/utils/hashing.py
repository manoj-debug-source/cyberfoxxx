import hashlib
import json


def sha256_hash(data) -> str:
    """
    Generate a SHA-256 hash from input data.

    Dictionaries are converted to a deterministic JSON string
    before hashing so the same data produces the same hash.
    """

    if isinstance(data, dict):
        data = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":")
        )

    if not isinstance(data, str):
        data = str(data)

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()
