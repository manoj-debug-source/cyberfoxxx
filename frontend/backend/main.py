from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.identity import router as identity_router
from routes.risk import router as risk_router
from routes.pipeline import router as pipeline_router

from database.mongodb import (
    connect_to_mongodb,
    close_mongodb_connection
)

from routes.auth import router as auth_router
from routes.blockchain import router as blockchain_router
from routes.screening import router as screening_router
from routes.audit import router as audit_router
from routes import scan
from routes.face import router as face_router
from routes.tamper import router as tamper_router
from routes.identity_validation import router as identity_validation_router
from routes.ocr import router as ocr_router
from routes.anomaly import router as anomaly_router
from routes.watchlist import router as watchlist_router


app = FastAPI(
    title="CYBERFOXXX API"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

@app.on_event("startup")
async def startup():
    await connect_to_mongodb()


@app.on_event("shutdown")
async def shutdown():
    await close_mongodb_connection()


# =========================================================
# ROUTES
# =========================================================

app.include_router(auth_router)

app.include_router(blockchain_router)

app.include_router(screening_router)

app.include_router(audit_router)

app.include_router(identity_router)

app.include_router(risk_router)

app.include_router(
    scan.router,
    prefix="/api"
)

app.include_router(watchlist_router)


# Face Authentication
app.include_router(
    face_router,
    prefix="/api/face",
    tags=["Face Authentication"]
)


# Tamper Detection
app.include_router(
    tamper_router,
    prefix="/api/tamper",
    tags=["Tamper Detection"]
)


# Identity Validation
app.include_router(
    identity_validation_router,
    prefix="/api/identity-validation",
    tags=["Identity Validation"]
)


# OCR / MRZ
#
# routes/ocr.py already contains:
# prefix="/api/ocr"
#
# Therefore DO NOT add another prefix here.
app.include_router(
    ocr_router
)


# Anomaly Detection
app.include_router(
    anomaly_router,
    prefix="/api/anomaly",
    tags=["Anomaly Detection"]
)


# Screening Pipeline
app.include_router(
    pipeline_router,
    prefix="/api/pipeline",
    tags=["Screening Pipeline"]
)


# =========================================================
# DEBUG MONGODB
# =========================================================

@app.get("/debug-mongodb")
async def debug_mongodb():

    from database.mongodb import db

    screening = await db.screenings.find_one(
        {
            "screening_id": "SCR-98F39196"
        },
        {
            "_id": 0,
            "screening_id": 1,
            "filename": 1,
            "status": 1,
        },
    )

    return {
        "database": db.name,
        "screening_found": screening is not None,
        "screening": screening,
    }


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "message": "CYBERFOXXX API is running"
    }