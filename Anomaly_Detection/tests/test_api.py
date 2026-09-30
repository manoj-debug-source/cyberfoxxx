"""
Integration tests for FastAPI REST API endpoints.
"""

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "SIH 2026" in data["project"]
    assert "/api/v1/anomaly/health" in data["health_check"]


def test_health_endpoint():
    response = client.get("/api/v1/anomaly/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["model_loaded"] is True
    assert data["monitored_sensors_count"] == 15


def test_sensors_endpoint():
    response = client.get("/api/v1/anomaly/sensors")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 15
    assert "TP2" in data["sensors"]
    assert data["sensors"]["TP2"]["unit"] == "bar"


def test_detect_normal_reading(normal_reading_dict):
    response = client.post("/api/v1/anomaly/detect", json=normal_reading_dict)
    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] is False
    assert data["anomaly_score"] < 0.50
    assert data["severity"] in ["NORMAL", "LOW"]


def test_detect_anomaly_reading(air_leak_reading_dict):
    response = client.post("/api/v1/anomaly/detect", json=air_leak_reading_dict)
    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] is True
    assert data["anomaly_score"] >= 0.50
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert len(data["primary_factors"]) > 0


def test_detect_invalid_reading():
    # Missing required sensor fields
    response = client.post("/api/v1/anomaly/detect", json={"TP2": 5.0})
    assert response.status_code == 422


def test_batch_detection_endpoint(normal_reading_dict, air_leak_reading_dict):
    payload = {"readings": [normal_reading_dict, air_leak_reading_dict]}
    response = client.post("/api/v1/anomaly/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_records"] == 2
    assert data["summary"]["anomaly_count"] == 1
    assert len(data["results"]) == 2
