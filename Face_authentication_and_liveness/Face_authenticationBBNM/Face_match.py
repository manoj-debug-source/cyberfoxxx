from deepface import DeepFace

def verify_faces(id_face_array, live_face_array):
    """
    Compares two face images held in memory (numpy arrays) — no disk I/O.
    """
    result = DeepFace.verify(
        img1_path=id_face_array,
        img2_path=live_face_array,
        model_name="ArcFace",
        detector_backend="retinaface",
        distance_metric="cosine",
        enforce_detection=True
    )
    return {
        "match": result["verified"],
        "distance": result["distance"],
        "threshold": result["threshold"],
        "model": result["model"]
    }