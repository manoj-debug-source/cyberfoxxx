"""
Unit tests for Pydantic schema validation.
"""

import pytest
from pydantic import ValidationError
from anomaly_engine.schema import TelemetryReading, BatchTelemetryRequest


def test_valid_reading(normal_reading_dict):
    reading = TelemetryReading(**normal_reading_dict)
    assert reading.TP2 == normal_reading_dict["TP2"]
    assert reading.Oil_temperature == normal_reading_dict["Oil_temperature"]
    assert reading.timestamp is not None


def test_reading_missing_timestamp_assigns_default(normal_reading_dict):
    data = normal_reading_dict.copy()
    data.pop("timestamp")
    reading = TelemetryReading(**data)
    assert reading.timestamp is not None
    assert len(reading.timestamp) > 0


def test_reading_rejects_missing_required_sensor(normal_reading_dict):
    data = normal_reading_dict.copy()
    data.pop("TP2")
    with pytest.raises(ValidationError):
        TelemetryReading(**data)


def test_reading_rejects_out_of_range_pressure(normal_reading_dict):
    data = normal_reading_dict.copy()
    data["TP2"] = 150.0  # Absurd pressure exceeding maximum 25.0 bar
    with pytest.raises(ValidationError):
        TelemetryReading(**data)


def test_reading_rejects_out_of_range_binary_signal(normal_reading_dict):
    data = normal_reading_dict.copy()
    data["COMP"] = 5.0  # Binary signal must be 0.0 or 1.0
    with pytest.raises(ValidationError):
        TelemetryReading(**data)


def test_batch_request_validation(normal_reading_dict, air_leak_reading_dict):
    batch = BatchTelemetryRequest(
        readings=[TelemetryReading(**normal_reading_dict), TelemetryReading(**air_leak_reading_dict)]
    )
    assert len(batch.readings) == 2


def test_batch_request_rejects_empty_list():
    with pytest.raises(ValidationError):
        BatchTelemetryRequest(readings=[])
