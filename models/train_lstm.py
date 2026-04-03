import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Reshape, LSTM, Lambda, Normalization
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)
tf.random.set_seed(42)

print("Loading preprocessed dataset...")
df = pd.read_csv('features/structural_data_processed.csv')

FEATURE_COLUMNS = [
    'concrete_grade_mpa', 'elevation_m', 'load_kn', 'cyclic_load_freq',
    'support_type', 'env_condition', 'vibration_mms', 'age_years',
    'years_since_inspection', 'load_ratio', 'stress_index',
    'age_squared', 'degradation_rate', 'fatigue_index'
]

X = df[FEATURE_COLUMNS].values

print("Synthesizing 25-year non-linear proxy target curves...")
N = len(df)
y_lstm = np.zeros((N, 25))
rates = df['degradation_rate'].values

# Simulate monotonic deterioration curves scaling exponentially with extracted base rates
for t in range(25):
    year = t + 1
    val = (rates * 10.0) * (year ** 1.2)
    y_lstm[:, t] = np.clip(val, 0, 100)
    
# Introduce environmental noise/variance
jitter = np.random.normal(0, 1.0, (N, 25))
y_lstm = np.clip(y_lstm + jitter, 0, 100)

# Secure strict monotonic boundaries ensuring a structure doesn't "repair" magically over time
for t in range(1, 25):
    y_lstm[:, t] = np.maximum(y_lstm[:, t], y_lstm[:, t-1])

X_train, X_test, y_train, y_test = train_test_split(X, y_lstm, test_size=0.2, random_state=42)

print("Constructing Deep Learning LSTM Architecture...")
# Standard Scaler logic directly embedded into model serialization binary using Normalization layer
norm_layer = Normalization(input_shape=(len(FEATURE_COLUMNS),))
norm_layer.adapt(X_train)

# Requested Architecture: Dense(64, relu) -> Reshape(1, 64) -> LSTM(64) -> Dense(25, sigmoid scaled to 0-100)
model = Sequential([
    norm_layer,
    Dense(64, activation='relu'),
    Reshape((1, 64)),
    LSTM(64),
    Dense(25, activation='sigmoid'),
    Lambda(lambda x: x * 100.0)
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])

print("\n--- Training Model 3: LSTM Deterioration Forecast ---")
history = model.fit(
    X_train, y_train,
    epochs=15,
    batch_size=32,
    validation_split=0.1,
    verbose=1
)

print("\nEvaluating Sequence Outputs...")
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print(f"\n[lstm] Test Set MAE: {mae:.3f} | RMSE: {rmse:.3f}")

print("\nValidating 25-Year Prediction Output format (Sample #1):")
print(np.round(y_pred[0], 2))

os.makedirs('models', exist_ok=True)

print("\nPersisting Binary .h5...")
model.save('models/lstm_deterioration.h5')

metrics_path = 'models/model_metrics.json'
try:
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
except FileNotFoundError:
    metrics = {}

metrics['lstm'] = {
    "MAE": round(float(mae), 2),
    "RMSE": round(float(rmse), 2)
}

with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=4)
print("Updated models/model_metrics.json with validation metrics successfully.")
