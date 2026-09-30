"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as anomaly_router
from api.doc_routes import router as doc_router

app = FastAPI(
    title="SIH 2026 - AI-Based Fake Identity & Document Screening System",
    description="Multi-layer Anomaly Detection, Image Forensics, and ICAO Document Validation Engine for Border Checkpoints.",
    version="2.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route handlers
app.include_router(anomaly_router)
app.include_router(doc_router)


@app.get("/")
def root():
    return {
        "project": "SIH 2026 AI-Based Fake Identity & Document Screening System",
        "modules": {
            "module_2": "Document Validation & ICAO 9303 Checksums",
            "module_3": "Tampering & Forgery Detection (Image Forensics & ELA)",
        },
        "api_docs": "/docs",
        "health_check": "/api/v1/anomaly/health",
        "screening_endpoints": {
            "screen_full_document": "POST /api/v1/document/screen",
            "screen_fields_only": "POST /api/v1/document/screen-fields",
            "health": "GET /api/v1/document/health",
        },
    }
