"""
Unit tests for Computer Vision image forensics, ELA, and metadata inspection.
"""

from document_engine.image_forensics import ImageForensicAnalyzer
from document_engine.sample_generator import (
    generate_genuine_sample,
    generate_photo_replacement_sample,
    generate_tampered_expiry_sample,
)


def test_genuine_image_forensics():
    analyzer = ImageForensicAnalyzer()
    img, *_ = generate_genuine_sample()

    is_tampered, score, evidence, fraud_types = analyzer.analyze_image(img)

    # Clean genuine document should have low anomaly score and no tampering flags
    assert is_tampered is False
    assert score < 0.30
    assert len(evidence) == 0
    assert analyzer.last_ela_heatmap_base64 is not None


def test_photo_replacement_forensics():
    analyzer = ImageForensicAnalyzer()
    img, _, _, metadata, *_ = generate_photo_replacement_sample()

    is_tampered, score, evidence, fraud_types = analyzer.analyze_image(img, metadata_dict=metadata)

    assert is_tampered is True
    assert score >= 0.70
    assert analyzer.last_ela_heatmap_base64 is not None
    # Must flag noise inconsistency or software metadata
    anomaly_names = [e.anomaly for e in evidence]
    assert any(
        "Photo Sensor Noise Inconsistency" in a
        or "Image Editing Software Fingerprint" in a
        for a in anomaly_names
    )


def test_metadata_photoshop_detection():
    analyzer = ImageForensicAnalyzer()
    img, *_ = generate_genuine_sample()

    fake_metadata = {"Software": "Adobe Photoshop CC 2024", "Artist": "Immigration Scanner"}
    is_tampered, score, evidence, fraud_types = analyzer.analyze_image(img, metadata_dict=fake_metadata)

    assert is_tampered is True
    assert any("Image Editing Software Fingerprint" in e.anomaly for e in evidence)

