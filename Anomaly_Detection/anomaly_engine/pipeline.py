"""
Unified Anomaly Detection Pipeline connecting Preprocessing, Detection, and Explanation.
Handles atomic artifact serialization and deserialization via joblib.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from anomaly_engine.config import ALL_FEATURES, DEFAULT_MODEL_PATH
from anomaly_engine.detector import AnomalyDetector
from anomaly_engine.explainer import AnomalyExplainer
from anomaly_engine.preprocessor import TelemetryPreprocessor
from anomaly_engine.schema import (
    AnomalyDetectionResult,
    BatchDetectionResponse,
    BatchDetectionSummary,
    TelemetryReading,
)


class AnomalyPipeline:
    """
    End-to-end industrial anomaly detection pipeline.
    Combines leakage-free preprocessing, calibrated Isolation Forest, and explainability.
    """

    def __init__(
        self,
        preprocessor: Optional[TelemetryPreprocessor] = None,
        detector: Optional[AnomalyDetector] = None,
    ):
        self.preprocessor = preprocessor or TelemetryPreprocessor()
        self.detector = detector or AnomalyDetector()
        self.explainer: Optional[AnomalyExplainer] = None
        self.is_fitted = False

        if self.preprocessor.is_fitted:
            self.explainer = AnomalyExplainer(self.preprocessor.baseline_stats)
            self.is_fitted = self.detector.is_fitted

    def fit(self, df_normal: pd.DataFrame) -> "AnomalyPipeline":
        """
        Trains pipeline strictly on baseline normal telemetry data.
        """
        # Fit preprocessor and compute baseline distributions
        X_scaled = self.preprocessor.fit_transform(df_normal)

        # Fit detector on scaled baseline data
        self.detector.fit(X_scaled)

        # Initialize explainer with computed baseline stats
        self.explainer = AnomalyExplainer(self.preprocessor.baseline_stats)
        self.is_fitted = True
        return self

    def predict_single(self, reading: Union[TelemetryReading, Dict]) -> AnomalyDetectionResult:
        """
        Performs inference on an individual telemetry reading.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyPipeline is not fitted or loaded.")

        if isinstance(reading, TelemetryReading):
            data_dict = reading.model_dump()
        else:
            data_dict = reading

        timestamp = data_dict.get("timestamp")
        df_row = pd.DataFrame([{k: data_dict[k] for k in ALL_FEATURES if k in data_dict}])

        # Preprocess
        X_scaled = self.preprocessor.transform(df_row)

        # Predict
        is_anom, scores, severities, confidences = self.detector.predict(X_scaled)
        is_anomaly = bool(is_anom[0])
        score = round(float(scores[0]), 3)
        severity = severities[0]
        confidence = float(confidences[0])

        # Explain root cause
        factors, diagnosis, action = self.explainer.explain(
            raw_values=data_dict,
            is_anomaly=is_anomaly,
            severity=severity,
        )

        return AnomalyDetectionResult(
            is_anomaly=is_anomaly,
            anomaly_score=score,
            severity=severity,
            confidence=confidence,
            timestamp=timestamp,
            primary_factors=factors,
            diagnostic_summary=diagnosis,
            recommended_action=action,
        )

    def predict_batch(
        self, readings: List[Union[TelemetryReading, Dict]]
    ) -> BatchDetectionResponse:
        """
        Performs high-throughput batch inference on a sequence of telemetry readings.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyPipeline is not fitted or loaded.")

        if not readings:
            raise ValueError("Readings list cannot be empty.")

        # Convert to DataFrame
        records = [
            r.model_dump() if isinstance(r, TelemetryReading) else r for r in readings
        ]
        df_batch = pd.DataFrame(records)

        # Preprocess entire batch
        X_scaled = self.preprocessor.transform(df_batch)

        # Predict batch
        is_anom, scores, severities, confidences = self.detector.predict(X_scaled)

        results: List[AnomalyDetectionResult] = []
        for i, rec in enumerate(records):
            is_anomaly = bool(is_anom[i])
            score = round(float(scores[i]), 3)
            severity = severities[i]
            confidence = float(confidences[i])

            factors, diagnosis, action = self.explainer.explain(
                raw_values=rec,
                is_anomaly=is_anomaly,
                severity=severity,
            )

            results.append(
                AnomalyDetectionResult(
                    is_anomaly=is_anomaly,
                    anomaly_score=score,
                    severity=severity,
                    confidence=confidence,
                    timestamp=rec.get("timestamp"),
                    primary_factors=factors,
                    diagnostic_summary=diagnosis,
                    recommended_action=action,
                )
            )

        # Compute summary metrics
        total = len(results)
        anom_count = sum(1 for r in results if r.is_anomaly)
        pct = round((anom_count / total) * 100, 2)
        max_score = max(r.anomaly_score for r in results) if results else 0.0

        # Severity rank
        rank_map = {"NORMAL": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        highest_sev = "NORMAL"
        highest_rank = 0
        for r in results:
            if rank_map.get(r.severity, 0) > highest_rank:
                highest_rank = rank_map[r.severity]
                highest_sev = r.severity

        summary = BatchDetectionSummary(
            total_records=total,
            anomaly_count=anom_count,
            anomaly_percentage=pct,
            max_score=round(max_score, 3),
            highest_severity=highest_sev,
        )

        return BatchDetectionResponse(summary=summary, results=results)

    def save(self, filepath: Optional[Union[str, Path]] = None) -> Path:
        """
        Serializes pipeline state to disk using joblib.
        """
        path = Path(filepath or DEFAULT_MODEL_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, filepath: Optional[Union[str, Path]] = None) -> "AnomalyPipeline":
        """
        Loads serialized pipeline state from disk.
        """
        path = Path(filepath or DEFAULT_MODEL_PATH)
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found at {path}")
        pipeline = joblib.load(path)
        if not isinstance(pipeline, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return pipeline
