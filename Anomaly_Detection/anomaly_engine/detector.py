"""
Anomaly detector core utilizing calibrated Isolation Forest.
Provides continuous [0.0, 1.0] anomaly scores, categorical severity, and confidence estimates.
"""

from typing import Dict, List, Literal, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

from anomaly_engine.config import (
    ANOMALY_SCORE_THRESHOLD,
    MODEL_PARAMS,
    SEVERITY_THRESHOLDS,
)


class AnomalyDetector:
    """
    Calibrated Isolation Forest Anomaly Detector for industrial telemetry.
    """

    def __init__(self, **kwargs):
        params = {**MODEL_PARAMS, **kwargs}
        self.model = IsolationForest(**params)
        self.is_fitted = False
        self.decision_threshold = 0.0
        self.min_decision = -0.35
        self.max_decision = 0.25

    def fit(self, X: np.ndarray) -> "AnomalyDetector":
        """
        Fits the Isolation Forest on preprocessed normal feature matrix.
        Calculates empirical score calibration boundaries.
        """
        self.model.fit(X)
        scores = self.model.decision_function(X)

        # Record empirical score boundaries on baseline normal data
        self.decision_threshold = float(self.model.offset_)
        self.min_decision = float(np.percentile(scores, 0.1))
        self.max_decision = float(np.percentile(scores, 99.9))
        self.is_fitted = True
        return self

    def predict_scores(self, X: np.ndarray) -> np.ndarray:
        """
        Computes calibrated anomaly scores in range [0.0, 1.0].
        0.0 = completely normal baseline, 0.50 = decision threshold, 1.0 = critical anomaly.
        """
        if not self.is_fitted:
            raise RuntimeError("Detector must be fitted before predict_scores can be called.")

        # raw decision function: higher is normal, lower is anomalous
        raw_decisions = self.model.decision_function(X)

        # Calibrated mapping:
        # For raw_decisions >= 0: normal region mapped to [0.0, 0.50]
        # For raw_decisions < 0: anomalous region mapped to [0.50, 1.0]
        calibrated_scores = np.zeros_like(raw_decisions)

        normal_mask = raw_decisions >= 0
        anomaly_mask = ~normal_mask

        # Normal region mapping [0.0, 0.50]
        denom_normal = max(self.max_decision, 1e-4)
        calibrated_scores[normal_mask] = 0.50 - (
            0.50 * (np.clip(raw_decisions[normal_mask], 0, denom_normal) / denom_normal)
        )

        # Anomaly region mapping [0.50, 1.00]
        abs_min_decision = abs(min(self.min_decision, -0.10))
        calibrated_scores[anomaly_mask] = 0.50 + (
            0.50 * (np.clip(-raw_decisions[anomaly_mask], 0, abs_min_decision) / abs_min_decision)
        )

        return np.clip(calibrated_scores, 0.0, 1.0)

    def classify_severity(self, score: float) -> str:
        """
        Maps continuous anomaly score to discrete severity levels.
        """
        if score >= SEVERITY_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif score >= SEVERITY_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif score >= SEVERITY_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        elif score >= SEVERITY_THRESHOLDS["LOW"]:
            return "LOW"
        else:
            return "NORMAL"

    def compute_confidence(self, score: float) -> float:
        """
        Computes decision confidence based on distance from the 0.50 decision threshold.
        """
        # Distance from threshold 0.50 scaled to [0.50, 1.0]
        dist = abs(score - ANOMALY_SCORE_THRESHOLD)
        confidence = 0.50 + dist
        return round(float(np.clip(confidence, 0.50, 0.99)), 3)

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[str], np.ndarray]:
        """
        Performs full inference: returns (is_anomaly, scores, severities, confidences).
        """
        scores = self.predict_scores(X)
        is_anomaly = scores >= ANOMALY_SCORE_THRESHOLD
        severities = [self.classify_severity(float(s)) for s in scores]
        confidences = np.array([self.compute_confidence(float(s)) for s in scores])
        return is_anomaly, scores, severities, confidences
