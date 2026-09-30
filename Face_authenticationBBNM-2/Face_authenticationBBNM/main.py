import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from deepface import DeepFace

from Face_match import verify_faces
from liveness import BlinkDetector

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# In-memory session store: { session_id: {"id_face_array": ..., "blink_detector": ..., "live_confirmed": bool} }
sessions = {}

def read_upload_as_cv2(file_bytes: bytes):
    arr = np.frombuffer(file_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


@app.post("/extract-id-face")
async def extract_id_face(file: UploadFile = File(...)):
    file_bytes = await file.read()
    img = read_upload_as_cv2(file_bytes)
    if img is None:
        raise HTTPException(400, "Could not read uploaded image")

    # Confirm a face actually exists before accepting this document
    try:
        DeepFace.extract_faces(img_path=img, detector_backend="retinaface", enforce_detection=True)
    except ValueError:
        raise HTTPException(422, "No face detected in the uploaded document. Please upload a clearer photo.")

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id_face_array": img,
        "blink_detector": BlinkDetector(),
        "live_confirmed": False
    }
    return {"session_id": session_id, "status": "id_face_stored"}


@app.post("/liveness-check")
async def liveness_check(session_id: str, file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(404, "Invalid session_id")

    file_bytes = await file.read()
    frame = read_upload_as_cv2(file_bytes)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    result = sessions[session_id]["blink_detector"].process_frame(gray)

    if result["blinks"] >= 1:
        sessions[session_id]["live_confirmed"] = True

    return {
        "blinks": result["blinks"],
        "face_detected": result["face_detected"],
        "live_confirmed": sessions[session_id]["live_confirmed"]
    }


@app.post("/verify")
async def verify(session_id: str, file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(404, "Invalid session_id")
    if not sessions[session_id]["live_confirmed"]:
        raise HTTPException(400, "Liveness not confirmed yet")

    file_bytes = await file.read()
    frame = read_upload_as_cv2(file_bytes)

    try:
        result = verify_faces(sessions[session_id]["id_face_array"], frame)
    except ValueError:
        raise HTTPException(422, "No face detected in the live capture. Please face the camera clearly.")

    # Clean up session after verification completes
    del sessions[session_id]

    return result