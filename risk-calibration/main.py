from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.risk import router as risk_router


app = FastAPI(
    title="CYBERFOXXX Risk Calibration API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(risk_router)


@app.get("/")
async def root():
    return {
        "message": "CYBERFOXXX Risk Calibration API is running"
    }