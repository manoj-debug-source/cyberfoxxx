"""
Singleton Inference Service for Anomaly Detection.
Provides high-performance, thread-safe inference for real-time and batch requests.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from anomaly_engine.config import DEFAULT_MODEL_PATH
from anomaly_engine.pipeline import AnomalyPipeline
from anomaly_engine.schema import (
    AnomalyDetectionResult,
    BatchDetectionResponse,
    BatchTelemetryRequest,
    TelemetryReading,
)

logger = logging.getLogger("anomaly_service")


class AnomalyInferenceService:
    """
    Inference service managing the loaded AnomalyPipeline lifecycle.
    """

    _instance: Optional["AnomalyInferenceService"] = None

    def __init__(self, model_path: Optional[Union[str, Path]] = None):
        self.model_path = Path(model_path or DEFAULT_MODEL_PATH)
        self.pipeline: Optional[AnomalyPipeline] = None
        self._load_pipeline()

    @classmethod
    def get_instance(
        cls, model_path: Optional[Union[str, Path]] = None
    ) -> "AnomalyInferenceService":
        """
        Retrieves or creates the singleton service instance.
        """
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance

    def _load_pipeline(self) -> None:
        """
        Loads pipeline artifact from disk.
        """
        try:
            if self.model_path.exists():
                logger.info("Loading anomaly detection pipeline from %s", self.model_path)
                self.pipeline = AnomalyPipeline.load(self.model_path)
                logger.info("Pipeline loaded successfully.")
            else:
                logger.warning(
                    "Model artifact not found at %s. Service pending model training.",
                    self.model_path,
                )
                self.pipeline = None
        except Exception as e:
            logger.error("Failed to load pipeline: %s", e)
            self.pipeline = None

    @property
    def is_ready(self) -> bool:
        return self.pipeline is not None and self.pipeline.is_fitted

    def detect(self, reading: TelemetryReading) -> AnomalyDetectionResult:
        """
        Performs anomaly detection on a single telemetry reading.
        """
        if not self.is_ready:
            raise RuntimeError("Anomaly Detection Service is not ready (model not loaded).")

        return self.pipeline.predict_single(reading)

    def detect_batch(self, request: BatchTelemetryRequest) -> BatchDetectionResponse:
        """
        Performs batch anomaly detection across multiple readings.
        """
        if not self.is_ready:
            raise RuntimeError("Anomaly Detection Service is not ready (model not loaded).")

        return self.pipeline.predict_batch(request.readings)

    def get_status(self) -> Dict:
        """
        Returns runtime health and model metadata.
        """
        return {
            "status": "HEALTHY" if self.is_ready else "INITIALIZING",
            "model_path": str(self.model_path),
            "model_loaded": self.is_ready,
            "monitored_sensors_count": (
                len(self.pipeline.preprocessor.feature_names) if self.is_ready else 0
            ),
        }
