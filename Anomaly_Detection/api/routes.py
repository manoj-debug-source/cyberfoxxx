"""
API route definitions for real-time and batch anomaly detection.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from anomaly_engine.config import SENSOR_METADATA
from anomaly_engine.schema import (
    AnomalyDetectionResult,
    BatchDetectionResponse,
    BatchTelemetryRequest,
    TelemetryReading,
)
from anomaly_engine.service import AnomalyInferenceService

router = APIRouter(prefix="/api/v1/anomaly", tags=["Anomaly Detection"])


def get_service() -> AnomalyInferenceService:
    service = AnomalyInferenceService.get_instance()
    if not service.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anomaly detection model is not loaded or training is incomplete.",
        )
    return service


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Returns engine health status and model readiness.
    """
    service = AnomalyInferenceService.get_instance()
    return service.get_status()


@router.get("/sensors")
def get_sensor_metadata() -> Dict[str, Any]:
    """
    Returns definitions, units, and descriptions of all 15 monitored APU sensors.
    """
    return {
        "count": len(SENSOR_METADATA),
        "sensors": SENSOR_METADATA,
    }


@router.post("/detect", response_model=AnomalyDetectionResult)
def detect_single(reading: TelemetryReading) -> AnomalyDetectionResult:
    """
    Real-time streaming inference for an individual APU sensor observation.
    Returns anomaly score, severity classification, and root-cause explanations.
    """
    service = get_service()
    try:
        return service.detect(reading)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {str(e)}",
        )


@router.post("/batch", response_model=BatchDetectionResponse)
def detect_batch(request: BatchTelemetryRequest) -> BatchDetectionResponse:
    """
    High-throughput batch inference for sequential telemetry readings.
    """
    service = get_service()
    try:
        return service.detect_batch(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch inference execution failed: {str(e)}",
        )
