"""
Shared module — loads all ML models exactly once at import time.
Routes import from here, NOT from app.py. This avoids circular imports.
"""
import os
import xgboost as xgb

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

print("[STARTUP] Loading ML models into memory...")

XGB_HEALTH = xgb.Booster()
XGB_HEALTH.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_health.json'))

XGB_RUL = xgb.Booster()
XGB_RUL.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul.json'))

XGB_RUL_LOWER = xgb.Booster()
XGB_RUL_LOWER.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_lower.json'))

XGB_RUL_UPPER = xgb.Booster()
XGB_RUL_UPPER.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_upper.json'))

print("[STARTUP] XGBoost models loaded.")

lstm_path = os.path.join(PROJECT_ROOT, 'models', 'lstm_deterioration.h5')
if os.path.exists(lstm_path):
    import tensorflow as tf
    LSTM_DETERIORATION = tf.keras.models.load_model(lstm_path, compile=False, safe_mode=False)
    print("[STARTUP] LSTM model loaded.")
else:
    LSTM_DETERIORATION = None
    print("[STARTUP] WARNING: lstm_deterioration.h5 not found — /forecast endpoint will be unavailable.")

print("[STARTUP] All models loaded successfully.")
