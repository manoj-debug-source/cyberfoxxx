"""
Pydantic schemas for data validation, serialization, and anomaly output structures.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class TelemetryReading(BaseModel):
    """
    Validation schema for an individual APU sensor observation.
    """
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp string or datetime of observation",
    )
    TP2: float = Field(..., ge=-5.0, le=25.0, description="Compressor Pressure (bar)")
    TP3: float = Field(..., ge=-5.0, le=25.0, description="Pneumatic Panel Pressure (bar)")
    H1: float = Field(..., ge=-5.0, le=25.0, description="Separator Filter Pressure (bar)")
    DV_pressure: float = Field(..., ge=-5.0, le=25.0, description="Air Dryer Discharge Pressure (bar)")
    Reservoirs: float = Field(..., ge=-5.0, le=25.0, description="Reservoir Downstream Pressure (bar)")
    Oil_temperature: float = Field(..., ge=-20.0, le=150.0, description="Compressor Oil Temperature (°C)")
    Motor_current: float = Field(..., ge=-1.0, le=30.0, description="Motor Phase Current (A)")
    COMP: float = Field(..., ge=0.0, le=1.0, description="Intake Valve State (0.0 or 1.0)")
    DV_eletric: float = Field(..., ge=0.0, le=1.0, description="Outlet Valve Electrical Signal (0.0 or 1.0)")
    Towers: float = Field(..., ge=0.0, le=1.0, description="Active Air Dryer Tower (0.0 or 1.0)")
    MPG: float = Field(..., ge=0.0, le=1.0, description="Cut-in Pressure Signal (0.0 or 1.0)")
    LPS: float = Field(..., ge=0.0, le=1.0, description="Low Pressure Safety Signal (0.0 or 1.0)")
    Pressure_switch: float = Field(..., ge=0.0, le=1.0, description="Dryer Discharge Switch (0.0 or 1.0)")
    Oil_level: float = Field(..., ge=0.0, le=1.0, description="Oil Level Indicator (0.0 or 1.0)")
    Caudal_impulses: float = Field(..., ge=0.0, le=1.0, description="Airflow Caudal Pulses (0.0 or 1.0)")

    @field_validator("timestamp", mode="before")
    @classmethod
    def format_timestamp(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return datetime.utcnow().isoformat()
        return str(v)


class BatchTelemetryRequest(BaseModel):
    """
    Request model for batch inference on multiple sensor readings.
    """
    readings: List[TelemetryReading] = Field(
        ..., min_length=1, description="List of telemetry sensor readings"
    )


class PrimaryFactor(BaseModel):
    """
    Physical sensor deviation attribution explaining the anomaly.
    """
    sensor: str = Field(..., description="Sensor code")
    name: str = Field(..., description="Human-readable sensor name")
    observed: float = Field(..., description="Observed sensor value")
    baseline_median: float = Field(..., description="Normal baseline median value")
    deviation_sigma: float = Field(
        ..., description="Standardized deviation in robust sigma units"
    )
    direction: Literal["HIGH", "LOW"] = Field(
        ..., description="Direction of deviation from normal"
    )


class AnomalyDetectionResult(BaseModel):
    """
    Structured enterprise-grade anomaly detection output.
    """
    is_anomaly: bool = Field(..., description="True if observation is classified anomalous")
    anomaly_score: float = Field(
        ..., ge=0.0, le=1.0, description="Calibrated anomaly score between 0.0 (healthy) and 1.0 (severe anomaly)"
    )
    severity: Literal["NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Categorical severity classification"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence in detection result"
    )
    timestamp: Optional[str] = Field(default=None, description="Observation timestamp")
    primary_factors: List[PrimaryFactor] = Field(
        default_factory=list, description="Top contributing physical sensor deviations"
    )
    diagnostic_summary: str = Field(..., description="Physical failure diagnosis explanation")
    recommended_action: str = Field(..., description="Prescriptive engineering maintenance action")


class BatchDetectionSummary(BaseModel):
    total_records: int
    anomaly_count: int
    anomaly_percentage: float
    max_score: float
    highest_severity: str


class BatchDetectionResponse(BaseModel):
    summary: BatchDetectionSummary
    results: List[AnomalyDetectionResult]
