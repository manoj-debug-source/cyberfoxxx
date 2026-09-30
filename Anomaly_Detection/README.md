# SIH 2026: Anomaly Detection Engine for Railway Air Production Units (APU)

An enterprise-grade, explainable, real-time Anomaly Detection and Predictive Maintenance module built for Urban Railway Transit Systems using the **MetroPT-3 benchmark dataset** (1,516,948 records collected from an operational train's compressor system).

---

## 1. System Architecture

```
                                 Multi-Sensor Telemetry
                       (7 Analogue + 8 Digital Compressor Sensors)
                                           │
                                           ▼
                              Input Validation Layer
                                (Pydantic V2 Schemas)
                                           │
                                           ▼
                           Leakage-Free Preprocessor
                      (RobustScaler & Noise Floor Bound)
                                           │
                                           ▼
                           Calibrated Anomaly Detector
                           (Multi-Tree Isolation Forest)
                                           │
                                           ▼
                                   Calibrated Score
                                 Normalized to [0, 1]
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
          Severity Classification                       Root-Cause Explainer
     (NORMAL / LOW / MED / HIGH / CRITICAL)      (Robust Z-Score Attribution Engine)
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           │
                                           ▼
                              Structured Anomaly Output
                      (Score + Severity + Diagnostic Reasons)
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
             FastAPI REST API                           SIH Live Demo Runner
      (POST /api/v1/anomaly/detect)                  (python demo/sih_demo.py)
```

---

## 2. Monitored Sensors (MetroPT-3)

| Sensor Code | Sensor Name | Type | Unit | Normal Function |
| :--- | :--- | :--- | :--- | :--- |
| **`TP2`** | Compressor Pressure | Analogue | bar | Pressure directly at compressor outlet (spikes under failure) |
| **`TP3`** | Pneumatic Panel Pressure | Analogue | bar | Pressure delivered to the train's pneumatic panel |
| **`H1`** | Separator Filter Pressure | Analogue | bar | Pressure drop across cyclonic filter (collapses during air leak) |
| **`DV_pressure`** | Dryer Discharge Pressure | Analogue | bar | Pressure drop during air dryer tower discharge |
| **`Reservoirs`** | Reservoir Pressure | Analogue | bar | Downstream pressure inside air storage reservoirs |
| **`Oil_temperature`** | Compressor Oil Temp | Analogue | °C | Operating temperature of lubricating oil |
| **`Motor_current`** | Motor Phase Current | Analogue | A | Three-phase electric motor current draw |
| **`COMP`** | Air Intake Valve State | Digital | binary | 1 = Offloaded/Resting, 0 = Active intake under load |
| **`DV_eletric`** | Outlet Valve Signal | Digital | binary | 1 = Active under load, 0 = Offloaded |
| **`Towers`** | Active Dryer Tower | Digital | binary | 0 = Tower 1 active, 1 = Tower 2 active |
| **`MPG`** | Cut-in Pressure Signal | Digital | binary | Activates when APU pressure falls below 8.2 bar |
| **`LPS`** | Low Pressure Signal | Digital | binary | Emergency alarm when pressure drops below 7.0 bar |
| **`Pressure_switch`** | Dryer Discharge Switch | Digital | binary | Monitors discharge cycle in air dryers |
| **`Oil_level`** | Oil Level Indicator | Digital | binary | 1 = Normal, 0 = Low lubricant warning |
| **`Caudal_impulses`**| Airflow Caudal Pulses | Digital | binary | Pulse outputs measuring air volume delivery |

---

## 3. Measured Model Performance

The engine was trained strictly on healthy pre-incident baseline telemetry (Feb 01 – Apr 16, 2020) and evaluated on unseen operational data containing documented failure event #1 (April 18, 2020 high-stress Air Leak):

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Failure Detection Recall (Sensitivity)** | **98.28%** | Detected **8,514 out of 8,663** failure records |
| **Precision** | **53.06%** | High early warning detection prior to total collapse |
| **F1-Score** | **0.6891** | Robust balance of sensitivity and operational safety |
| **False Negative Rate (Missed Failures)** | **1.72%** | Only 149 records missed during failure state |
| **Inference Latency** | **< 3 ms** | Sub-millisecond single-reading processing speed |

---

## 4. Quick Start & Execution

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Model Training & Evaluation
```bash
python -m anomaly_engine.trainer
```

### Run Full Test Suite (26 Unit & Integration Tests)
```bash
python -m pytest tests -v
```

### Run the SIH Live Demonstration
```bash
# Automated streaming demo with colored telemetry UI:
python demo/sih_demo.py

# Interactive step-by-step presentation mode (advances on Enter):
python demo/sih_demo.py --interactive
```

### Start the REST API Service
```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at: `http://127.0.0.1:8000/docs`.

---

## 5. REST API Endpoints

### 1. Health & Model Readiness
`GET /api/v1/anomaly/health`
```json
{
  "status": "HEALTHY",
  "model_path": "models/artifacts/apu_anomaly_pipeline.joblib",
  "model_loaded": true,
  "monitored_sensors_count": 15
}
```

### 2. Streaming Real-Time Detection
`POST /api/v1/anomaly/detect`

**Request Body:**
```json
{
  "timestamp": "2020-04-18T14:30:00",
  "TP2": 9.65,
  "TP3": 8.10,
  "H1": 0.02,
  "DV_pressure": 2.15,
  "Reservoirs": 8.08,
  "Oil_temperature": 78.4,
  "Motor_current": 7.85,
  "COMP": 0.0,
  "DV_eletric": 1.0,
  "Towers": 0.0,
  "MPG": 0.0,
  "LPS": 0.0,
  "Pressure_switch": 1.0,
  "Oil_level": 1.0,
  "Caudal_impulses": 1.0
}
```

**Response Body:**
```json
{
  "is_anomaly": true,
  "anomaly_score": 0.853,
  "severity": "CRITICAL",
  "confidence": 0.853,
  "timestamp": "2020-04-18T14:30:00",
  "primary_factors": [
    {
      "sensor": "TP2",
      "name": "Compressor Pressure",
      "observed": 9.65,
      "baseline_median": -0.012,
      "deviation_sigma": 32.5,
      "direction": "HIGH"
    },
    {
      "sensor": "H1",
      "name": "Separator Filter Pressure",
      "observed": 0.02,
      "baseline_median": 8.828,
      "deviation_sigma": -11.2,
      "direction": "LOW"
    }
  ],
  "diagnostic_summary": "Pneumatic Air Leak / Continuous Overload: Compressor outlet pressure (TP2) is elevated under continuous effort while separator filter pressure (H1) has collapsed.",
  "recommended_action": "Inspect pneumatic circuit, check cyclonic separator valve seals and pipe couplings for active air leaks."
}
```

### 3. Batch Telemetry Ingestion
`POST /api/v1/anomaly/batch`
- Ingests multiple chronological records and returns batch summary metrics (`total_records`, `anomaly_count`, `anomaly_percentage`, `max_score`, `highest_severity`) with individual point diagnoses.
