from pydantic import BaseModel, Field


class RiskInput(BaseModel):
    """
    Input received from the main CYBERFOXXX backend.

    All probability values must be between 0 and 1.
    """

    screening_id: str

    ocr_confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    mrz_confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    tamper_probability: float = Field(
        ge=0.0,
        le=1.0
    )

    anomaly_probability: float = Field(
        ge=0.0,
        le=1.0
    )

    face_match_probability: float = Field(
        ge=0.0,
        le=1.0
    )

    watchlist_probability: float = Field(
        ge=0.0,
        le=1.0
    )

    identity_linkage_score: float = Field(
        ge=0.0,
        le=1.0
    )


class RiskOutput(BaseModel):
    """
    Risk result returned by the calibration service.
    """

    screening_id: str

    calibrated_risk: float

    risk_level: str

    model_version: str
    calibration_method: str