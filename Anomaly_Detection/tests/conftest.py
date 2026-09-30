"""
Shared pytest fixtures for the Anomaly Detection test suite.
"""

import pytest
from anomaly_engine.pipeline import AnomalyPipeline
from anomaly_engine.schema import TelemetryReading
from anomaly_engine.config import DEFAULT_MODEL_PATH


@pytest.fixture(scope="session")
def pipeline():
    """Provides the trained AnomalyPipeline singleton."""
    return AnomalyPipeline.load(DEFAULT_MODEL_PATH)


@pytest.fixture
def normal_reading_dict():
    """A verified nominal operational reading from baseline data (Row 100)."""
    return {
        "timestamp": "2020-02-01T00:16:31",
        "TP2": -0.016,
        "TP3": 8.398,
        "H1": 8.390,
        "DV_pressure": -0.024,
        "Reservoirs": 8.394,
        "Oil_temperature": 53.6,
        "Motor_current": 0.035,
        "COMP": 1.0,
        "DV_eletric": 0.0,
        "Towers": 1.0,
        "MPG": 1.0,
        "LPS": 0.0,
        "Pressure_switch": 1.0,
        "Oil_level": 1.0,
        "Caudal_impulses": 1.0,
    }


@pytest.fixture
def normal_reading(normal_reading_dict):
    return TelemetryReading(**normal_reading_dict)


@pytest.fixture
def air_leak_reading_dict():
    """An air leak failure observation from the April 18, 2020 failure event."""
    return {
        "timestamp": "2020-04-18T14:30:00",
        "TP2": 9.65,
        "TP3": 8.10,
        "H1": 0.02,
        "DV_pressure": 2.15,
        "Reservoirs": 8.08,
        "Oil_temperature": 78.4,
        "Motor_current": 7.85,
        "COMP": 0.0,
        "DV_eletric": 1.0,
        "Towers": 0.0,
        "MPG": 0.0,
        "LPS": 0.0,
        "Pressure_switch": 1.0,
        "Oil_level": 1.0,
        "Caudal_impulses": 1.0,
    }


@pytest.fixture
def air_leak_reading(air_leak_reading_dict):
    return TelemetryReading(**air_leak_reading_dict)


@pytest.fixture
def borderline_reading_dict():
    """A borderline reading slightly deviating from baseline."""
    return {
        "timestamp": "2020-04-17T23:55:00",
        "TP2": 4.50,
        "TP3": 8.70,
        "H1": 4.20,
        "DV_pressure": 0.50,
        "Reservoirs": 8.68,
        "Oil_temperature": 66.0,
        "Motor_current": 4.10,
        "COMP": 0.0,
        "DV_eletric": 1.0,
        "Towers": 1.0,
        "MPG": 1.0,
        "LPS": 0.0,
        "Pressure_switch": 1.0,
        "Oil_level": 1.0,
        "Caudal_impulses": 1.0,
    }


@pytest.fixture
def extreme_reading_dict():
    """Extreme out-of-distribution values to test numerical stability."""
    return {
        "timestamp": "2020-05-01T00:00:00",
        "TP2": 24.5,
        "TP3": 0.1,
        "H1": -0.5,
        "DV_pressure": 15.0,
        "Reservoirs": 0.2,
        "Oil_temperature": 140.0,
        "Motor_current": 28.0,
        "COMP": 0.0,
        "DV_eletric": 1.0,
        "Towers": 0.0,
        "MPG": 0.0,
        "LPS": 1.0,
        "Pressure_switch": 0.0,
        "Oil_level": 0.0,
        "Caudal_impulses": 0.0,
    }
