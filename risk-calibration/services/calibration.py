from model.risk_model import RiskInput


MODEL_VERSION = "risk-calibrator-v1"


def calculate_raw_risk(data: RiskInput) -> float:
    """
    Calculate an initial risk signal from the model outputs.

    This is a PLACEHOLDER aggregation layer for the API prototype.

    It is NOT the final calibrated ML model.
    The trained calibration model can replace this later.
    """

    # Positive risk signals
    tamper_risk = data.tamper_probability
    anomaly_risk = data.anomaly_probability
    watchlist_risk = data.watchlist_probability

    # Convert positive evidence into risk.
    identity_risk = 1.0 - data.identity_linkage_score
    face_risk = 1.0 - data.face_match_probability

    # Low OCR/MRZ confidence increases risk.
    ocr_risk = 1.0 - data.ocr_confidence
    mrz_risk = 1.0 - data.mrz_confidence

    # Initial aggregation.
    raw_risk = (
        0.25 * tamper_risk
        + 0.20 * anomaly_risk
        + 0.15 * watchlist_risk
        + 0.10 * identity_risk
        + 0.10 * face_risk
        + 0.10 * ocr_risk
        + 0.10 * mrz_risk
    )

    return round(
        max(0.0, min(1.0, raw_risk)),
        4
    )


def classify_risk(risk: float) -> str:
    """
    Convert risk probability into a human-readable category.

    These are prototype thresholds and must be validated
    with real validation data before production use.
    """

    if risk < 0.25:
        return "LOW"

    if risk < 0.50:
        return "MEDIUM"

    if risk < 0.75:
        return "HIGH"

    return "CRITICAL"


def calibrate_risk(data: RiskInput) -> dict:
    """
    Produce the current risk result.

    The current implementation uses the raw aggregation
    as a temporary stand-in for the future calibrated model.
    """

    raw_risk = calculate_raw_risk(data)

    return {
        "screening_id": data.screening_id,
        "calibrated_risk": raw_risk,
        "risk_level": classify_risk(raw_risk),
        "model_version": MODEL_VERSION,
        "calibration_method": "prototype-weighted-aggregation"
    }