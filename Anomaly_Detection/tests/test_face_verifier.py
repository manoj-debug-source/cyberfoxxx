"""
Unit tests for Module 4: FaceVerifier & Presentation Attack Detection.
"""

from document_engine.face_verifier import FaceVerifier
from document_engine.sample_generator import create_avatar_face


def test_face_verifier_genuine_match():
    verifier = FaceVerifier()
    # Identical seed produces matching face
    face1 = create_avatar_face(seed_id=10, is_female=True)
    face2 = create_avatar_face(seed_id=10, is_female=True)

    res, evidence = verifier.verify_faces(face1, face2, doc_already_cropped=True)

    assert res.face_detected_doc is True
    assert res.face_detected_live is True
    assert res.is_match is True
    assert res.is_impersonation is False
    assert res.similarity_score > 0.85
    assert res.liveness_passed is True


def test_face_verifier_impersonation_mismatch():
    verifier = FaceVerifier()
    # Different seeds produce different face shapes & demographics
    face1 = create_avatar_face(seed_id=10, is_female=True, skin_tone=(240, 200, 170), hair_color=(40, 20, 10))
    face2 = create_avatar_face(seed_id=99, is_female=False, skin_tone=(190, 150, 120), hair_color=(180, 100, 30))

    res, evidence = verifier.verify_faces(face1, face2, doc_already_cropped=True)

    assert res.face_detected_doc is True
    assert res.face_detected_live is True
    assert res.is_match is False
    assert res.is_impersonation is True
    assert res.similarity_score < 0.55
    assert evidence is not None
    assert "Impersonation" in evidence.anomaly

