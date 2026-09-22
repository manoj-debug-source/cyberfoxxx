from difflib import SequenceMatcher

from utils.hashing import sha256_hash


# ============================================================
# 1. Normalize identity
# ============================================================

def normalize_identity(identity_data: dict) -> dict:
    """
    Normalize identity information so that small formatting
    differences do not create completely different identities.

    Supported identity fields:
        - name
        - contact_number
        - document_number
    """

    normalized = {}

    if not isinstance(identity_data, dict):
        return normalized

    for key, value in identity_data.items():

        # Ignore empty values
        if value is None:
            continue

        if isinstance(value, str):

            value = value.strip()

            if not value:
                continue

            value = value.lower()

        normalized[key] = value

    return normalized


# ============================================================
# 2. Generate deterministic identity hash
# ============================================================

def generate_identity_hash(identity_data: dict) -> str:
    """
    Generate a deterministic SHA-256 identity hash.

    The same normalized identity information will generate
    the same hash.
    """

    normalized_data = normalize_identity(
        identity_data
    )

    return sha256_hash(normalized_data)


# ============================================================
# 3. String similarity
# ============================================================

def string_similarity(
    value1,
    value2
) -> float:
    """
    Calculate similarity between two values.

    Returns:
        1.0  -> exact match
        0.0  -> completely different

    Used mainly for names.
    """

    if value1 is None or value2 is None:
        return 0.0

    value1 = str(value1).strip().lower()
    value2 = str(value2).strip().lower()

    if not value1 or not value2:
        return 0.0

    if value1 == value2:
        return 1.0

    return SequenceMatcher(
        None,
        value1,
        value2
    ).ratio()


# ============================================================
# 4. Contact number normalization
# ============================================================

def normalize_contact_number(
    value
) -> str | None:
    """
    Normalize contact numbers by removing common formatting
    characters.

    Example:

        +91 98765-43210
        +919876543210

    are treated as the same number.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    cleaned = (
        value
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    return cleaned.lower()


# ============================================================
# 5. Compare identity fields
# ============================================================

def compare_identity_fields(
    identity_a: dict,
    identity_b: dict
) -> dict:
    """
    Compare two identity records.

    Fields used:

        1. Name
        2. Contact Number
        3. Document Number

    Date of birth and nationality are intentionally NOT used.
    """

    if not isinstance(identity_a, dict):
        identity_a = {}

    if not isinstance(identity_b, dict):
        identity_b = {}

    # --------------------------------------------------------
    # Normalize both identities
    # --------------------------------------------------------

    identity_a = normalize_identity(identity_a)
    identity_b = normalize_identity(identity_b)

    # --------------------------------------------------------
    # Fields used for identity comparison
    # --------------------------------------------------------

    fields = [
        "name",
        "contact_number",
        "document_number"
    ]

    evidence = {}
    scores = []

    # --------------------------------------------------------
    # Compare each available field
    # --------------------------------------------------------

    for field in fields:

        value_a = identity_a.get(field)
        value_b = identity_b.get(field)

        # If either record does not contain this field,
        # skip the field instead of treating it as a mismatch.
        if value_a is None or value_b is None:
            continue

        # ----------------------------------------------------
        # Name
        # ----------------------------------------------------

        if field == "name":

            score = string_similarity(
                value_a,
                value_b
            )

        # ----------------------------------------------------
        # Contact number
        # ----------------------------------------------------

        elif field == "contact_number":

            contact_a = normalize_contact_number(
                value_a
            )

            contact_b = normalize_contact_number(
                value_b
            )

            if contact_a and contact_b:
                score = (
                    1.0
                    if contact_a == contact_b
                    else 0.0
                )
            else:
                continue

        # ----------------------------------------------------
        # Document number
        # ----------------------------------------------------

        elif field == "document_number":

            document_a = str(
                value_a
            ).strip().lower()

            document_b = str(
                value_b
            ).strip().lower()

            score = (
                1.0
                if document_a == document_b
                else 0.0
            )

        else:
            continue

        # ----------------------------------------------------
        # Store evidence
        # ----------------------------------------------------

        scores.append(score)

        evidence[field] = {
            "match": score == 1.0,
            "score": round(
                score,
                4
            )
        }

    # ========================================================
    # 6. Calculate overall score
    # ========================================================

    if scores:

        overall_score = (
            sum(scores)
            / len(scores)
        )

    else:

        overall_score = 0.0

    # ========================================================
    # 7. Return comparison
    # ========================================================

    return {
        "score": round(
            overall_score,
            4
        ),
        "evidence": evidence
    }


# ============================================================
# 8. Prepare identity linkage
# ============================================================

async def link_identity(
    identity_data: dict,
    screening_id: str
):
    """
    Prepare normalized identity information and generate
    its SHA-256 identity hash.

    Database matching is handled by routes/identity.py.
    """

    normalized_identity = normalize_identity(
        identity_data
    )

    if not normalized_identity:
        return {
            "screening_id": screening_id,
            "identity_hash": None,
            "identity_data": {}
        }

    identity_hash = generate_identity_hash(
        normalized_identity
    )

    return {
        "screening_id": screening_id,
        "identity_hash": identity_hash,
        "identity_data": normalized_identity
    }