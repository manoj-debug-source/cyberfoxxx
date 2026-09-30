"""
Configuration settings, sensor metadata, and thresholds for the Anomaly Detection Engine.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "MetroPT3(AirCompressor).csv"
MODELS_DIR = BASE_DIR / "models" / "artifacts"
DEFAULT_MODEL_PATH = MODELS_DIR / "apu_anomaly_pipeline.joblib"

# Sensor definitions
ANALOG_FEATURES = [
    "TP2",
    "TP3",
    "H1",
    "DV_pressure",
    "Reservoirs",
    "Oil_temperature",
    "Motor_current",
]

DIGITAL_FEATURES = [
    "COMP",
    "DV_eletric",
    "Towers",
    "MPG",
    "LPS",
    "Pressure_switch",
    "Oil_level",
    "Caudal_impulses",
]

ALL_FEATURES = ANALOG_FEATURES + DIGITAL_FEATURES

SENSOR_METADATA = {
    "TP2": {
        "name": "Compressor Pressure",
        "unit": "bar",
        "description": "Pressure generated directly at the compressor outlet",
    },
    "TP3": {
        "name": "Pneumatic Panel Pressure",
        "unit": "bar",
        "description": "Pressure delivered to the main pneumatic control panel",
    },
    "H1": {
        "name": "Separator Filter Pressure",
        "unit": "bar",
        "description": "Pressure drop across the cyclonic separator filter",
    },
    "DV_pressure": {
        "name": "Air Dryer Discharge Pressure",
        "unit": "bar",
        "description": "Pressure drop when towers discharge air dryers",
    },
    "Reservoirs": {
        "name": "Reservoir Downstream Pressure",
        "unit": "bar",
        "description": "Pressure measured inside the downstream air storage reservoirs",
    },
    "Oil_temperature": {
        "name": "Compressor Oil Temperature",
        "unit": "°C",
        "description": "Operating temperature of compressor lubricating oil",
    },
    "Motor_current": {
        "name": "Motor Phase Current",
        "unit": "A",
        "description": "Current drawn by three-phase electric motor",
    },
    "COMP": {
        "name": "Intake Valve State",
        "unit": "binary",
        "description": "1 = Off/Offloaded (no air intake), 0 = Active intake under load",
    },
    "DV_eletric": {
        "name": "Outlet Valve Electrical Signal",
        "unit": "binary",
        "description": "1 = Active under load, 0 = Inactive off/offloaded",
    },
    "Towers": {
        "name": "Active Air Dryer Tower",
        "unit": "binary",
        "description": "0 = Tower 1 active, 1 = Tower 2 active",
    },
    "MPG": {
        "name": "Cut-in Pressure Signal",
        "unit": "binary",
        "description": "Activates when APU pressure falls below 8.2 bar",
    },
    "LPS": {
        "name": "Low Pressure Safety Signal",
        "unit": "binary",
        "description": "Emergency signal when pressure drops below critical 7.0 bar",
    },
    "Pressure_switch": {
        "name": "Dryer Discharge Switch",
        "unit": "binary",
        "description": "Monitors discharge in air-drying towers",
    },
    "Oil_level": {
        "name": "Oil Level Indicator",
        "unit": "binary",
        "description": "Monitors lubricant level inside compressor",
    },
    "Caudal_impulses": {
        "name": "Airflow Caudal Pulses",
        "unit": "binary",
        "description": "Pulse outputs measuring air delivery volume into reservoirs",
    },
}

# Anomaly calibration and thresholds
ANOMALY_SCORE_THRESHOLD = 0.50

SEVERITY_THRESHOLDS = {
    "CRITICAL": 0.80,
    "HIGH": 0.65,
    "MEDIUM": 0.50,
    "LOW": 0.35,
}

# Root-cause explainability threshold (deviations in robust sigma)
EXPLAINER_SIGMA_THRESHOLD = 2.0
MAX_EXPLANATION_FACTORS = 4

# Training hyperparameters
MODEL_PARAMS = {
    "n_estimators": 150,
    "contamination": 0.02,  # Ground truth air leak contamination is ~1.975%
    "max_samples": 50000,
    "random_state": 42,
    "n_jobs": -1,
}
