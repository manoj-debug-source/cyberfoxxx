"""
End-to-end integration tests for the DocumentScreener anomaly engine across all 4 modules.
"""

from document_engine.sample_generator import (
    generate_face_mismatch_sample,
    generate_genuine_sample,
    generate_photo_replacement_sample,
    generate_stamp_forgery_sample,
    generate_tampered_expiry_sample,
    generate_watchlist_hit_sample,
)
from document_engine.schema import DocumentScreeningFieldsRequest
from document_engine.screener import DocumentScreener


def test_screener_genuine_passport():
    screener = DocumentScreener()
    img, passport, visa, live_face = generate_genuine_sample()

    result = screener.screen(
        image_input=img,
        live_face_input=live_face,
        passport=passport,
        visa=visa,
        document_type="PASSPORT",
    )

    assert result.is_anomaly is False
    assert result.anomaly_score < 0.30
    assert result.severity in ["NORMAL", "LOW"]
    assert "CLEAR" in result.decision
    assert result.tampering_detected is False
    assert result.validation_failed is False
    assert result.face_verified is True
    assert result.impersonation_detected is False
    assert len(result.evidence) == 0


def test_screener_tampered_expiry():
    screener = DocumentScreener()
    img, passport, visa, live_face = generate_tampered_expiry_sample()

    result = screener.screen(
        image_input=img,
        live_face_input=live_face,
        passport=passport,
        visa=visa,
        document_type="PASSPORT",
    )

    assert result.is_anomaly is True
    assert result.anomaly_score >= 0.85
    assert result.severity == "CRITICAL"
    assert "REJECT" in result.decision
    assert result.validation_failed is True
    assert len(result.evidence) > 0


def test_screener_photo_replacement():
    screener = DocumentScreener()
    img, passport, visa, metadata, live_face = generate_photo_replacement_sample()

    result = screener.screen(
        image_input=img,
        live_face_input=live_face,
        passport=passport,
        visa=visa,
        document_type="PASSPORT",
        metadata=metadata,
    )

    assert result.is_anomaly is True
    assert result.anomaly_score >= 0.85
    assert result.severity == "CRITICAL"
    assert result.tampering_detected is True
    assert result.ela_heatmap_base64 is not None
    assert any("Photo Replacement" in f or "Software" in f for f in result.detected_fraud_types)


def test_screener_face_impersonation():
    screener = DocumentScreener()
    img, passport, visa, imposter_face = generate_face_mismatch_sample()

    result = screener.screen(
        image_input=img,
        live_face_input=imposter_face,
        passport=passport,
        visa=visa,
        document_type="PASSPORT",
    )

    assert result.is_anomaly is True
    assert result.impersonation_detected is True
    assert result.face_verified is False
    assert result.anomaly_score >= 0.88
    assert "REJECT" in result.decision
    assert any("Impersonation" in f for f in result.detected_fraud_types)


def test_screener_watchlist_detection():
    screener = DocumentScreener()
    img, passport, visa, live_face = generate_watchlist_hit_sample()

    result = screener.screen(
        image_input=img,
        live_face_input=live_face,
        passport=passport,
        visa=visa,
        document_type="PASSPORT",
    )

    assert result.is_anomaly is True
    assert result.watchlist_hit is not None
    assert "INTERPOL RED NOTICE" in result.watchlist_hit.category
    assert result.anomaly_score >= 0.95
    assert "REJECT" in result.decision or "CODE RED" in result.recommended_action


def test_screener_field_only():
    screener = DocumentScreener()
    img, passport, visa, live_face = generate_genuine_sample()

    req = DocumentScreeningFieldsRequest(
        document_type="PASSPORT",
        passport=passport,
        visa=visa,
    )
    result = screener.screen_fields_only(req)

    assert result.is_anomaly is False
    assert result.anomaly_score < 0.30
    assert "CLEAR" in result.decision
