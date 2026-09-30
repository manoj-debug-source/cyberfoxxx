"""
Integration tests for Document Screening REST API endpoints across all 4 modules.
"""

import io
import json
from fastapi.testclient import TestClient
from api.app import app
from document_engine.sample_generator import (
    create_avatar_face,
    generate_genuine_sample,
    generate_tampered_expiry_sample,
)

client = TestClient(app)


def test_doc_health_endpoint():
    response = client.get("/api/v1/document/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["module_1_ocr_extraction"] == "ACTIVE"
    assert data["module_2_document_validation"] == "ACTIVE"
    assert data["module_3_tampering_detection"] == "ACTIVE"
    assert data["module_4_face_verification"] == "ACTIVE"


def test_screen_fields_endpoint_genuine():
    _, passport, visa, _ = generate_genuine_sample()
    payload = {
        "document_type": "PASSPORT",
        "passport": passport.model_dump(),
        "visa": visa.model_dump(),
    }
    response = client.post("/api/v1/document/screen-fields", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] is False
    assert data["anomaly_score"] < 0.30
    assert data["severity"] in ["NORMAL", "LOW"]
    assert "CLEAR" in data["decision"]


def test_screen_fields_endpoint_tampered_mrz():
    _, passport, visa, _ = generate_tampered_expiry_sample()
    payload = {
        "document_type": "PASSPORT",
        "passport": passport.model_dump(),
        "visa": visa.model_dump() if visa else None,
    }
    response = client.post("/api/v1/document/screen-fields", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_anomaly"] is True
    assert data["anomaly_score"] >= 0.85
    assert data["severity"] == "CRITICAL"
    assert "REJECT" in data["decision"]
    assert len(data["evidence"]) > 0


def test_screen_full_document_endpoint_multipart():
    img, passport, visa, live_face = generate_genuine_sample()

    img_buf = io.BytesIO()
    img.save(img_buf, format="JPEG")
    img_bytes = img_buf.getvalue()

    face_buf = io.BytesIO()
    live_face.save(face_buf, format="JPEG")
    face_bytes = face_buf.getvalue()

    files = {
        "image": ("passport.jpg", img_bytes, "image/jpeg"),
        "live_face": ("live.jpg", face_bytes, "image/jpeg"),
    }
    data = {
        "document_type": "PASSPORT",
        "passport_json": json.dumps(passport.model_dump()),
        "visa_json": json.dumps(visa.model_dump()),
    }

    response = client.post("/api/v1/document/screen", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["document_id"] == passport.passport_number
    assert res["is_anomaly"] is False
    assert res["face_verified"] is True
    assert res["anomaly_score"] < 0.30
    assert "CLEAR" in res["decision"]


def test_watchlist_endpoint():
    response = client.get("/api/v1/document/watchlist")
    assert response.status_code == 200
    records = response.json()
    assert len(records) >= 3
    assert any(r["passport_number"] == "M1983021" for r in records)


def test_ocr_endpoint():
    mrz = "P<INDSHARMA<<ANANYA<<<<<<<<<<<<<<<<<<<<<<<<<\nZ8942105<8IND9605140F3205130<<<<<<<<<<<<<<<0"
    response = client.post("/api/v1/document/ocr", data={"raw_text": mrz, "document_type": "PASSPORT"})
    assert response.status_code == 200
    data = response.json()
    assert data["passport"]["name"] == "ANANYA SHARMA"
    assert data["mrz_detected"] is True


def test_face_verify_endpoint():
    face1 = create_avatar_face(seed_id=5, is_female=True)
    face2 = create_avatar_face(seed_id=5, is_female=True)

    buf1, buf2 = io.BytesIO(), io.BytesIO()
    face1.save(buf1, format="JPEG")
    face2.save(buf2, format="JPEG")

    files = {
        "doc_image": ("doc.jpg", buf1.getvalue(), "image/jpeg"),
        "live_face": ("live.jpg", buf2.getvalue(), "image/jpeg"),
    }

    response = client.post("/api/v1/document/face-verify", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["is_match"] is True
    assert data["similarity_score"] > 0.80

