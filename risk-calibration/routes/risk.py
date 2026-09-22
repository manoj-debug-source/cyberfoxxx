from fastapi import APIRouter

from model.risk_model import RiskInput, RiskOutput
from services.calibration import calibrate_risk


router = APIRouter(
    prefix="/api/risk",
    tags=["Risk Calibration"]
)


@router.post(
    "/calibrate",
    response_model=RiskOutput
)
async def calibrate(data: RiskInput):
    """
    Receive model outputs and return a risk assessment.
    """

    result = calibrate_risk(data)

    return result