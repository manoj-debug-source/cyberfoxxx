from rapidfuzz.fuzz import ratio


class IdentityValidationService:

    def __init__(self, collection):
        self.collection = collection

    def validate_identity(self, identity):

        # Search by ID number first
        record = self.collection.find_one({
            "id_number": identity.id_number
        })

        if not record:
            return {
                "valid": False,
                "status": "REJECTED",
                "confidence": 0,
                "matched_fields": [],
                "mismatched_fields": ["id_number"],
                "message": "Identity number not found in trusted registry."
            }

        matched = []
        mismatched = []

        # Exact comparisons
        if identity.date_of_birth == record["date_of_birth"]:
            matched.append("date_of_birth")
        else:
            mismatched.append("date_of_birth")

        if identity.gender.lower() == record["gender"].lower():
            matched.append("gender")
        else:
            mismatched.append("gender")

        if identity.id_type.lower() == record["id_type"].lower():
            matched.append("id_type")
        else:
            mismatched.append("id_type")

        if identity.phone == record["phone"]:
            matched.append("phone")
        else:
            mismatched.append("phone")

        # Fuzzy name matching
        name_score = ratio(
            identity.full_name.lower(),
            record["full_name"].lower()
        )

        if name_score >= 90:
            matched.append("full_name")
        else:
            mismatched.append("full_name")

        # Fuzzy address matching
        address_score = ratio(
            identity.address.lower(),
            record["address"].lower()
        )

        if address_score >= 80:
            matched.append("address")
        else:
            mismatched.append("address")

        # ID number already matched
        matched.append("id_number")

        # Calculate confidence
        confidence = round(
            (
                len(matched) / 7
            ) * 100,
            2
        )

        if confidence >= 85:
            status = "VERIFIED"
            valid = True

        elif confidence >= 60:
            status = "REVIEW"
            valid = False

        else:
            status = "REJECTED"
            valid = False

        return {
            "valid": valid,
            "status": status,
            "confidence": confidence,
            "matched_fields": matched,
            "mismatched_fields": mismatched,
            "message": "Identity validation completed."
        }