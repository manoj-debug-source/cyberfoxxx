from fastapi import APIRouter, Depends

from database.mongodb import db
from utils.jwt import get_current_user


router = APIRouter(
    prefix="/api/audit",
    tags=["Audit Log"]
)


def get_ai_decision(risk):
    """
    Convert Risk Calibration risk level
    into the AI screening decision.
    """

    if not isinstance(risk, dict):
        return None

    risk_level = risk.get("risk_level")

    if not risk_level:
        return None

    risk_level = str(risk_level).upper().strip()

    if risk_level == "LOW":
        return "CLEAR"

    if risk_level == "MEDIUM":
        return "REVIEW"

    if risk_level in ["HIGH", "CRITICAL"]:
        return "REJECT"

    return None


@router.get("/logs")
async def get_audit_logs(
    current_user: dict = Depends(get_current_user)
):

    logs = []

    # Newest screening first
    cursor = db.screenings.find(
        {}
    ).sort(
        "created_at",
        -1
    )

    async for screening in cursor:

        screening_id = screening.get(
            "screening_id"
        )

        # ==========================================
        # RISK / AI RESULT
        # ==========================================

        risk = screening.get("risk") or {}

        if not isinstance(risk, dict):
            risk = {}

        # Actual field returned by your Risk service
        calibrated_risk = risk.get(
            "calibrated_risk"
        )

        risk_level = risk.get(
            "risk_level"
        )

        # Convert risk level to AI decision
        ai_decision = get_ai_decision(
            risk
        )

        # ==========================================
        # OFFICER DECISION
        # ==========================================

        officer_data = screening.get(
            "officer_decision"
        )

        officer_decision = None
        officer_username = None
        officer_time = None

        if isinstance(
            officer_data,
            dict
        ):

            officer_decision = officer_data.get(
                "decision"
            )

            officer_username = officer_data.get(
                "decided_by"
            )

            officer_time = officer_data.get(
                "decided_at"
            )

        elif officer_data:

            officer_decision = str(
                officer_data
            ).upper()

        # ==========================================
        # BLOCKCHAIN
        # ==========================================

        ledger_event = await db.ledger.find_one(
            {
                "screening_id": screening_id
            },
            sort=[
                ("timestamp", -1)
            ]
        )

        on_chain = (
            ledger_event is not None
        )

        blockchain_event = None

        if ledger_event:

            blockchain_event = ledger_event.get(
                "event_type"
            )

        # ==========================================
        # TIMESTAMP
        # ==========================================

        timestamp = screening.get(
            "created_at"
        )

        if not timestamp:
            timestamp = officer_time

        # ==========================================
        # AUDIT RECORD
        # ==========================================

        logs.append(
            {
                "screening_id": screening_id,

                # AI / Risk
                "risk_score": calibrated_risk,
                "calibrated_risk": calibrated_risk,
                "risk_level": risk_level,
                "decision": ai_decision,

                # Officer
                "officer_decision": officer_decision,
                "officer": officer_username,

                # Blockchain
                "on_chain": on_chain,
                "blockchain_event": blockchain_event,

                # Document
                "document_hash": screening.get(
                    "document_hash"
                ),

                # Identity
                "identity_hash": screening.get(
                    "identity_hash"
                ),

                # Creator
                "created_by": screening.get(
                    "created_by"
                ),

                # Time
                "timestamp": timestamp,
            }
        )

    return {
        "items": logs,
        "total": len(logs)
    }