"""
Unit and integration tests for anomaly detector and full pipeline inference.
"""

import pytest
from anomaly_engine.schema import TelemetryReading, BatchTelemetryRequest


def test_normal_data_inference(pipeline, normal_reading):
    """
    Requirement 14: Normal data -> Expected result: normal.
    """
    result = pipeline.predict_single(normal_reading)

    assert result.is_anomaly is False
    assert result.anomaly_score < 0.50
    assert result.severity in ["NORMAL", "LOW"]
    assert "Nominal Operation" in result.diagnostic_summary


def test_obvious_anomaly_detection(pipeline, air_leak_reading):
    """
    Requirement 14: Obvious anomaly -> Expected result: anomaly.
    """
    result = pipeline.predict_single(air_leak_reading)

    assert result.is_anomaly is True
    assert result.anomaly_score >= 0.50
    assert result.severity in ["HIGH", "CRITICAL"]
    assert len(result.primary_factors) > 0

    # Ensure TP2 or H1 or Motor_current is flagged
    factor_sensors = [f.sensor for f in result.primary_factors]
    assert any(s in factor_sensors for s in ["TP2", "H1", "Motor_current", "Oil_temperature"])


def test_borderline_observation(pipeline, borderline_reading_dict):
    """
    Requirement 14: Borderline observation -> Verify threshold behavior.
    """
    reading = TelemetryReading(**borderline_reading_dict)
    result = pipeline.predict_single(reading)

    assert 0.0 <= result.anomaly_score <= 1.0
    if result.anomaly_score >= 0.50:
        assert result.is_anomaly is True
        assert result.severity in ["MEDIUM", "HIGH", "CRITICAL"]
    else:
        assert result.is_anomaly is False
        assert result.severity in ["NORMAL", "LOW"]


def test_extreme_values_stability(pipeline, extreme_reading_dict):
    """
    Requirement 14: Extreme values -> Verify system stability.
    """
    reading = TelemetryReading(**extreme_reading_dict)
    result = pipeline.predict_single(reading)

    assert isinstance(result.anomaly_score, float)
    assert 0.0 <= result.anomaly_score <= 1.0
    assert result.is_anomaly is True
    assert result.severity in ["HIGH", "CRITICAL"]


def test_batch_inference(pipeline, normal_reading, air_leak_reading):
    """
    Requirement 14: Unseen data -> Verify batch inference.
    """
    readings = [normal_reading, air_leak_reading]
    response = pipeline.predict_batch(readings)

    assert response.summary.total_records == 2
    assert response.summary.anomaly_count == 1
    assert response.summary.anomaly_percentage == 50.0
    assert len(response.results) == 2
    assert response.results[0].is_anomaly is False
    assert response.results[1].is_anomaly is True
