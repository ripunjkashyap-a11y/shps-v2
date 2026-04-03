"""
Shared module — loads all ML models exactly once at import time.
Routes import from here, NOT from app.py. This avoids circular imports.
"""
import os
import pickle
import tensorflow as tf

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

print("[STARTUP] Loading ML models into memory...")

with open(os.path.join(PROJECT_ROOT, 'models', 'xgb_health.pkl'), 'rb') as f:
    XGB_HEALTH = pickle.load(f)
with open(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul.pkl'), 'rb') as f:
    XGB_RUL = pickle.load(f)
with open(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_lower.pkl'), 'rb') as f:
    XGB_RUL_LOWER = pickle.load(f)
with open(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_upper.pkl'), 'rb') as f:
    XGB_RUL_UPPER = pickle.load(f)

LSTM_DETERIORATION = tf.keras.models.load_model(
    os.path.join(PROJECT_ROOT, 'models', 'lstm_deterioration.h5'),
    compile=False, safe_mode=False
)

print("[STARTUP] All models loaded successfully.")
