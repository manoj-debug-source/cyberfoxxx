from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from dotenv import load_dotenv
from pydantic import BaseModel
from rapidfuzz import fuzz
from typing import Optional
import os
import re

# Load environment variables
load_dotenv()

# FastAPI application
app = FastAPI(
    title="AI Fake Identity Detection API",
    description="Identity Validation Registry and Fuzzy Matching Backend",
    version="1.0.0"
)

# MongoDB connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://127.0.0.1:27017"
)

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

# Database
db = client["identity_validation"]

# Collections
identities = db["identities"]
identity_registry = db["identity_registry"]


# Identity data model
class Identity(BaseModel):
    full_name: str
    date_of_birth: str
    gender: str
    id_type: str
    id_number: str
    address: str
    phone: Optional[str] = None


# Normalize text
def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# Fuzzy matching
def fuzzy_match(value1: str, value2: str) -> float:

    value1 = normalize_text(value1)
    value2 = normalize_text(value2)

    if not value1 or not value2:
        return 0.0

    return float(
        fuzz.token_sort_ratio(value1, value2)
    )


# Home
@app.get("/")
def home():

    return {
        "message": "AI Fake Identity Detection Backend is running",
        "status": "active"
    }


# Health check
@app.get("/health")
def health():

    try:

        client.admin.command("ping")

        return {
            "status": "healthy",
            "mongodb": "connected"
        }

    except Exception as e:

        return {
            "status": "error",
            "mongodb": "not connected",
            "error": str(e)
        }


# Add identity to registry
@app.post("/registry/add")
def add_identity_to_registry(identity: Identity):

    try:

        client.admin.command("ping")

        # Check duplicate ID
        existing_identity = identity_registry.find_one(
            {
                "id_number": identity.id_number
            }
        )

        if existing_identity:

            raise HTTPException(
                status_code=400,
                detail="Identity already exists in registry"
            )

        # Convert identity to dictionary
        registry_data = identity.model_dump()

        # Demo registry information
        registry_data["status"] = "VALID"
        registry_data["blacklisted"] = False

        # Insert into registry
        result = identity_registry.insert_one(
            registry_data
        )

        return {
            "status": "success",
            "message": "Identity added to validation registry",
            "registry_id": str(result.inserted_id)
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Registry error: {str(e)}"
        )


# Get all registered identities
@app.get("/registry")
def get_registry():

    try:

        client.admin.command("ping")

        records = []

        for record in identity_registry.find():

            record["_id"] = str(record["_id"])
            records.append(record)

        return {
            "count": len(records),
            "registry": records
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to fetch registry: {str(e)}"
        )


# Validate identity
@app.post("/validate-identity")
def validate_identity(identity: Identity):

    try:

        client.admin.command("ping")

        # Normalize submitted data
        submitted_name = normalize_text(
            identity.full_name
        )

        submitted_address = normalize_text(
            identity.address
        )

        submitted_dob = identity.date_of_birth.strip()

        submitted_id = identity.id_number.strip().upper()

        submitted_gender = normalize_text(
            identity.gender
        )

        submitted_id_type = normalize_text(
            identity.id_type
        )

        # Search by exact ID number first
        candidates = list(
            identity_registry.find(
                {
                    "id_number": submitted_id
                }
            )
        )

        # If ID is not found, search by ID type
        if not candidates:

            candidates = list(
                identity_registry.find(
                    {
                        "id_type": identity.id_type
                    }
                )
            )

        # No registry record
        if not candidates:

            validation_result = {
                "decision": "FAKE",
                "match_score": 0,
                "matched_registry_id": None,
                "reason": "No matching identity found in registry"
            }

            stored_data = identity.model_dump()

            stored_data["validation"] = validation_result

            identities.insert_one(stored_data)

            return {
                "status": "completed",
                "validation": validation_result
            }

        # Find best match
        best_match = None
        best_score = 0

        for record in candidates:

            # Name similarity
            name_score = fuzzy_match(
                submitted_name,
                record.get("full_name", "")
            )

            # Address similarity
            address_score = fuzzy_match(
                submitted_address,
                record.get("address", "")
            )

            # DOB exact match
            registry_dob = str(
                record.get(
                    "date_of_birth",
                    ""
                )
            ).strip()

            dob_match = (
                submitted_dob == registry_dob
            )

            # ID exact match
            registry_id = str(
                record.get(
                    "id_number",
                    ""
                )
            ).strip().upper()

            id_match = (
                submitted_id == registry_id
            )

            # Gender match
            registry_gender = normalize_text(
                record.get(
                    "gender",
                    ""
                )
            )

            gender_match = (
                submitted_gender == registry_gender
            )

            # ID type match
            registry_id_type = normalize_text(
                record.get(
                    "id_type",
                    ""
                )
            )

            id_type_match = (
                submitted_id_type == registry_id_type
            )

            # Calculate score
            score = 0.0

            # Name = 40%
            score += name_score * 0.40

            # Address = 20%
            score += address_score * 0.20

            # DOB = 15%
            if dob_match:
                score += 15

            # ID number = 15%
            if id_match:
                score += 15

            # Gender = 5%
            if gender_match:
                score += 5

            # ID type = 5%
            if id_type_match:
                score += 5

            score = round(score, 2)

            # Keep highest score
            if score > best_score:

                best_score = score

                best_match = {
                    "record": record,
                    "name_score": round(
                        name_score,
                        2
                    ),
                    "address_score": round(
                        address_score,
                        2
                    ),
                    "dob_match": dob_match,
                    "id_match": id_match,
                    "gender_match": gender_match,
                    "id_type_match": id_type_match,
                    "score": score
                }

        # Best matching record
        record = best_match["record"]
        score = best_match["score"]

        # Check blacklist
        if record.get("blacklisted", False):

            decision = "BLACKLISTED"

            reason = (
                "Identity exists in registry but is blacklisted"
            )

        # Check status
        elif record.get("status", "VALID") != "VALID":

            decision = "INVALID"

            reason = (
                "Identity exists in registry but its status is invalid"
            )

        # High match
        elif score >= 80:

            decision = "VALID"

            reason = (
                "Identity strongly matches the registry record"
            )

        # Partial match
        elif score >= 50:

            decision = "SUSPICIOUS"

            reason = (
                "Partial identity match detected"
            )

        # Low match
        else:

            decision = "FAKE"

            reason = (
                "Identity does not sufficiently match the registry"
            )

        # Validation result
        validation_result = {

            "decision": decision,

            "match_score": score,

            "matched_registry_id": str(
                record["_id"]
            ),

            "reason": reason,

            "field_analysis": {

                "name_similarity": best_match[
                    "name_score"
                ],

                "address_similarity": best_match[
                    "address_score"
                ],

                "date_of_birth_match": best_match[
                    "dob_match"
                ],

                "id_number_match": best_match[
                    "id_match"
                ],

                "gender_match": best_match[
                    "gender_match"
                ],

                "id_type_match": best_match[
                    "id_type_match"
                ]
            }
        }

        # Store validation history
        stored_identity = identity.model_dump()

        stored_identity["validation"] = validation_result

        identities.insert_one(
            stored_identity
        )

        # Return result
        return {

            "status": "completed",

            "submitted_identity": {

                "full_name": identity.full_name,

                "date_of_birth": identity.date_of_birth,

                "gender": identity.gender,

                "id_type": identity.id_type,

                "id_number": identity.id_number,

                "address": identity.address,

                "phone": identity.phone
            },

            "validation": validation_result
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {str(e)}"
        )