# SHPS v2.0 — Structural Health Prediction System

**Predictive asset management for civil infrastructure** — turns raw sensor telemetry into maintenance decisions with 95% confidence intervals and explainable AI.

**Live Demo**: https://huggingface.co/spaces/Ripunk/shps-v2

---

## Screenshots

![Dashboard](assets/dashboard.png)
*Health index gauge, RUL estimate with confidence interval, and 25-year LSTM deterioration forecast*

![SHAP & What-If](assets/shap.png)
*SHAP factor breakdown showing age and environmental condition as primary risk drivers, alongside the What-If load stress simulator*

---

## What It Does

An engineer inputs 9 sensor readings and gets back:

- **Health Score** (0–100) with condition grade and safety status
- **Remaining Useful Life** — median estimate with a calibrated 95% confidence interval
- **25-Year Deterioration Forecast** — temporal degradation curve with confidence band (LSTM)
- **SHAP Feature Attribution** — exactly which factors are driving the risk score
- **What-If Simulation** — real-time score response to a single parameter change
- **PDF Audit Report** — server-generated, includes charts, SHAP analysis, and maintenance roadmap

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML Models | XGBoost (health score + RUL quantile regression), Keras/TensorFlow LSTM (25-yr forecast) |
| Explainability | SHAP `TreeExplainer` with KMeans background (interventional, <50ms per request) |
| Feature Engineering | 9 raw inputs → 14 physics-informed features (stress index, fatigue index, degradation rate) |
| Validation | Pydantic v2 with cross-field physics guardrails at the API boundary |
| API | Flask 3.1 + Flask-CORS, Gunicorn production server |
| Report Generation | ReportLab (in-memory PDF, matplotlib charts embedded) |
| Containerization | Multi-stage Docker/Podman build, `tensorflow-cpu`, non-root user, port 7860 |

---

## Model Performance

| Model | Task | R² | MAE | RMSE |
|---|---|---|---|---|
| XGBoost Health | Static integrity score (0–100) | 0.89 | 4.04 | 5.09 |
| XGBoost RUL | Remaining Useful Life (years) | 0.98 | 1.58 | 1.96 |
| LSTM | 25-year deterioration forecast | — | 0.98 | 1.33 |

---

## Key Engineering Decisions

**1. Quantile Regression for Safety-Asymmetric Problems**

Standard MSE minimisation is dangerous for infrastructure — underestimating risk costs lives. Three separate XGBoost models are trained at quantiles `[0.025, 0.5, 0.975]` to produce a calibrated 95% confidence interval. The UI surfaces the lower bound as the "safety buffer" to bias toward earlier maintenance.

**2. Decoupled Model Committee**

The health score (XGBoost) and the long-term forecast (LSTM) operate on the same physics feature manifold but are completely independent pipelines. Feeding the health score into the LSTM would create a single point of failure — a noisy sensor reading would corrupt a 25-year forecast. Decoupling isolates errors to their source.

**3. Physics-Informed Validation Layer**

Pydantic `model_validator` enforces domain rules at the API boundary before any model inference runs — e.g. rejecting payloads where `load_kn > 4000` with `concrete_grade_mpa < 30` (a structural impossibility), or cantilever structures with loads exceeding 2500 kN. Prevents garbage-in/garbage-out predictions without model retraining.

**4. Fast SHAP via KMeans Background**

The SHAP background dataset (10,000-row training manifold) is compressed to 100 KMeans centroids at server startup. This keeps interventional SHAP inference under 50ms per request, making it viable for real-time UI updates without caching.

**5. Weights-Only LSTM Loading**

The LSTM is loaded by reconstructing its architecture in code and calling `load_weights()` rather than deserialising a full `.h5` model file. This sidesteps Keras version incompatibilities in config serialisation across environments and makes the loading deterministic.

---

## Architecture

```
Sensor Inputs (9 fields)
        │
        ▼
Pydantic Physics Guardrails
        │
        ▼
Feature Engineering (14 features)
   ┌────┴────┬──────────────┐
   ▼         ▼              ▼
XGBoost   XGBoost RUL    LSTM
Health    (Q0.025/0.5/   Forecast
Score     0.975)         (25 yr)
   │         │              │
   └────┬────┘              │
        ▼                   ▼
  SHAP Explainer      Deterioration
  (interventional)     Curve + CI
        │
        ▼
  Flask REST API  →  Dashboard UI  →  PDF Report
```

---

## API Reference

All prediction endpoints accept the same 9-field JSON payload.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Container readiness check |
| GET | `/simulate` | Generate a physics-valid random input |
| GET | `/model-info` | Training metrics for all models |
| POST | `/predict` | Health score + RUL with 95% CI |
| POST | `/forecast` | 25-year LSTM deterioration series |
| POST | `/explain` | SHAP feature attributions |
| POST | `/whatif` | Score delta for a single parameter change |
| POST | `/report` | Generate and stream PDF report |

**Input schema** (`StructureInput`):

| Field | Type | Range | Description |
|---|---|---|---|
| `construction_year` | int | 1960–2025 | Year built |
| `last_inspection_year` | int | 1990–2025 | Last structural inspection |
| `concrete_grade_mpa` | int | 20–50 | Concrete compressive strength (MPa) |
| `elevation_m` | float | 0–150 | Structure height (m) |
| `load_kn` | float | 100–5000 | Applied load (kN) |
| `cyclic_load_freq` | float | 10–500 | Load cycling frequency |
| `support_type` | int | 0–3 | 0=Simply Supported, 1=One Fixed, 2=Both Fixed, 3=Cantilever |
| `env_condition` | int | 0–6 | 0=Mild → 6=Industrial-Chemical |
| `vibration_mms` | float | 0.1–12 | Vibration amplitude (mm/s) |

**Sample request / response (`/predict`):**

```bash
curl -X POST http://127.0.0.1:7860/predict \
  -H "Content-Type: application/json" \
  -d '{
    "construction_year": 2008,
    "last_inspection_year": 2021,
    "concrete_grade_mpa": 30,
    "elevation_m": 20.0,
    "load_kn": 350.0,
    "cyclic_load_freq": 120.0,
    "support_type": 2,
    "env_condition": 3,
    "vibration_mms": 3.2
  }'
```

```json
{
  "health_score": 79.4,
  "condition": "Fair",
  "safety_status": "Safe with Monitoring",
  "RUL_years": 39.4,
  "RUL_confidence_low": 22.0,
  "RUL_confidence_high": 42.7,
  "RUL_display": "39.4 years (±10.4 years at 95% confidence)",
  "maintenance_action": {
    "priority": "medium",
    "label": "Schedule Ultrasonic Testing within 90 days",
    "color": "orange"
  }
}
```

---

## Local Setup

```bash
git clone https://github.com/ripunjkashyap-a11y/shps-v2.git
cd shps-v2
pip install -r requirements.txt
python api/app.py
# → http://localhost:5005
```

**Docker:**
```bash
docker build -t shps-v2 .
docker run -p 127.0.0.1:7860:7860 shps-v2
# → http://127.0.0.1:7860
```

**Podman:**
```bash
podman build -t shps-v2 .
podman run -p 127.0.0.1:7860:7860 shps-v2
# → http://127.0.0.1:7860
# Note: use 127.0.0.1, not localhost — Podman on Windows binds IPv4 only
```

---

## Project Structure

```
shps-v2/
├── api/
│   ├── app.py              # Flask app, blueprint registration
│   ├── model_loader.py     # Singleton model loader (runs once at import)
│   ├── schemas.py          # Pydantic input validation + physics guardrails
│   ├── routes/
│   │   ├── predict.py      # /predict
│   │   ├── forecast.py     # /forecast
│   │   ├── explain.py      # /explain
│   │   ├── whatif.py       # /whatif
│   │   ├── simulate.py     # /simulate, /model-info
│   │   └── report.py       # /report
│   └── utils/
│       ├── core.py         # Feature engineering, shared utilities
│       └── report_engine.py # PDF generation (ReportLab)
├── explainability/
│   └── shap_explainer.py   # SHAP TreeExplainer with KMeans background
├── features/
│   └── structural_data_processed.csv  # SHAP background manifold
├── models/
│   ├── xgb_health.json     # XGBoost health score model
│   ├── xgb_rul.json        # XGBoost RUL median model
│   ├── xgb_rul_lower.json  # XGBoost RUL Q0.025
│   ├── xgb_rul_upper.json  # XGBoost RUL Q0.975
│   ├── lstm_weights.weights.h5  # LSTM weights (version-agnostic)
│   ├── train_xgboost.py    # Training script
│   └── train_lstm.py       # Training script
├── templates/index.html    # Dashboard UI
├── static/                 # CSS + JS
├── Dockerfile
└── requirements.txt
```

---

**Author**: Ripunjay Kashyap
