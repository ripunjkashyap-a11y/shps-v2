"""
Shared module — loads all ML models exactly once at import time.
Routes import from here, NOT from app.py. This avoids circular imports.
"""
import os
import xgboost as xgb

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

print("[STARTUP] Loading ML models into memory...")

try:
    XGB_HEALTH = xgb.Booster()
    XGB_HEALTH.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_health.json'))
except Exception as e:
    raise RuntimeError(f"[STARTUP] FATAL: Could not load xgb_health.json — {e}")

try:
    XGB_RUL = xgb.Booster()
    XGB_RUL.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul.json'))
except Exception as e:
    raise RuntimeError(f"[STARTUP] FATAL: Could not load xgb_rul.json — {e}")

try:
    XGB_RUL_LOWER = xgb.Booster()
    XGB_RUL_LOWER.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_lower.json'))
except Exception as e:
    raise RuntimeError(f"[STARTUP] FATAL: Could not load xgb_rul_lower.json — {e}")

try:
    XGB_RUL_UPPER = xgb.Booster()
    XGB_RUL_UPPER.load_model(os.path.join(PROJECT_ROOT, 'models', 'xgb_rul_upper.json'))
except Exception as e:
    raise RuntimeError(f"[STARTUP] FATAL: Could not load xgb_rul_upper.json — {e}")

print("[STARTUP] XGBoost models loaded.")

lstm_weights_path = os.path.join(PROJECT_ROOT, 'models', 'lstm_weights.weights.h5')
if os.path.exists(lstm_weights_path):
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Reshape, LSTM as LSTMLayer, Lambda, Normalization

    # Reconstruct the exact architecture from train_lstm.py to avoid
    # Keras version deserialization issues with full .h5 model files.
    LSTM_DETERIORATION = Sequential([
        Normalization(input_shape=(14,)),
        Dense(64, activation='relu'),
        Reshape((1, 64)),
        LSTMLayer(64),
        Dense(25, activation='sigmoid'),
        Lambda(lambda x: x * 100.0)
    ])
    LSTM_DETERIORATION.load_weights(lstm_weights_path)
    print("[STARTUP] LSTM model loaded (weights-only).")
else:
    LSTM_DETERIORATION = None
    print("[STARTUP] WARNING: lstm_weights.weights.h5 not found — /forecast endpoint will be unavailable.")

print("[STARTUP] All models loaded successfully.")
