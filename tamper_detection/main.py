import io

import numpy as np
import tensorflow as tf
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_PATH = "improved_tamper_detector.keras"

IMAGE_SIZE = (224, 224)

# Based on the model's sigmoid output.
# Change this only if your teammate confirms the
# training labels were reversed.
TAMPER_CLASS_IS_ONE = True

TAMPER_THRESHOLD = 0.50


# =========================================================
# LOAD MODEL
# =========================================================

print("Loading tamper detection model...")

model = tf.keras.models.load_model(MODEL_PATH)

print("Tamper detection model loaded successfully.")
print("Input shape:", model.input_shape)
print("Output shape:", model.output_shape)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="CYBERFOXXX Tamper Detection API",
    description="Document tampering detection service",
    version="1.0.0"
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
async def root():

    return {
        "service": "CYBERFOXXX Tamper Detection API",
        "status": "running"
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "model": "loaded"
    }


# =========================================================
# IMAGE PREPROCESSING
# =========================================================

def preprocess_image(file_bytes: bytes):

    try:

        image = Image.open(
            io.BytesIO(file_bytes)
        ).convert("RGB")

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid image file."
        )

    image = image.resize(IMAGE_SIZE)

    image_array = np.array(
        image,
        dtype=np.float32
    )

    image_array = np.expand_dims(
        image_array,
        axis=0
    )

    return image_array


# =========================================================
# TAMPER PREDICTION
# =========================================================

def predict_tamper(file_bytes: bytes):

    image_array = preprocess_image(
        file_bytes
    )

    prediction = model.predict(
        image_array,
        verbose=0
    )

    raw_output = float(
        prediction[0][0]
    )

    # -----------------------------------------------------
    # Convert sigmoid output into probabilities
    # -----------------------------------------------------

    if TAMPER_CLASS_IS_ONE:

        tamper_probability = raw_output
        genuine_probability = 1.0 - raw_output

    else:

        genuine_probability = raw_output
        tamper_probability = 1.0 - raw_output

    # -----------------------------------------------------
    # Final prediction
    # -----------------------------------------------------

    if tamper_probability >= TAMPER_THRESHOLD:

        label = "tampered"

    else:

        label = "genuine"

    return {
        "prediction": label,
        "tamper_probability": round(
            tamper_probability,
            4
        ),
        "genuine_probability": round(
            genuine_probability,
            4
        ),
        "threshold": TAMPER_THRESHOLD,
        "raw_model_output": round(
            raw_output,
            4
        )
    }


# =========================================================
# API ENDPOINT
# =========================================================

@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):

    allowed_types = [
        "image/jpeg",
        "image/png"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPG and PNG images are allowed."
        )

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    result = predict_tamper(
        file_bytes
    )

    return {
        "success": True,
        "filename": file.filename,
        **result
    }