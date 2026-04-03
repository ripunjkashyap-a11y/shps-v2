import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

print("Loading preprocessed dataset...")
# Load processed data
df = pd.read_csv('features/structural_data_processed.csv')

FEATURE_COLUMNS = [
    'concrete_grade_mpa', 'elevation_m', 'load_kn', 'cyclic_load_freq',
    'support_type', 'env_condition', 'vibration_mms', 'age_years',
    'years_since_inspection', 'load_ratio', 'stress_index',
    'age_squared', 'degradation_rate', 'fatigue_index'
]
TARGET_HEALTH = 'health_score'
TARGET_RUL = 'RUL_years'

X = df[FEATURE_COLUMNS]
y_health = df[TARGET_HEALTH]
y_rul = df[TARGET_RUL]

X_train, X_test, y_health_train, y_health_test, y_rul_train, y_rul_test = train_test_split(
    X, y_health, y_rul, test_size=0.2, random_state=42
)

metrics_dict = {}
os.makedirs('models', exist_ok=True)

def evaluate_model(model, X_test, y_test, name):
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    metrics_dict[name] = {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "R2": round(r2, 2)
    }
    print(f"[{name}] R2: {r2:.3f} | MAE: {mae:.3f} | RMSE: {rmse:.3f}")

# ---------------------------------------------------------
print("\n--- Training Model 1: XGBoost Health Score ---")
xgb_health = xgb.XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42)
xgb_health.fit(X_train, y_health_train)
evaluate_model(xgb_health, X_test, y_health_test, "xgb_health")

with open('models/xgb_health.pkl', 'wb') as f:
    pickle.dump(xgb_health, f)


# ---------------------------------------------------------
print("\n--- Training Model 2: XGBoost RUL (Median) ---")
xgb_rul = xgb.XGBRegressor(n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42)
xgb_rul.fit(X_train, y_rul_train)
evaluate_model(xgb_rul, X_test, y_rul_test, "xgb_rul")

with open('models/xgb_rul.pkl', 'wb') as f:
    pickle.dump(xgb_rul, f)


# ---------------------------------------------------------
print("\n--- Training Model 2: XGBoost RUL (Quantile 0.025) ---")
xgb_rul_lower = xgb.XGBRegressor(
    objective='reg:quantileerror', 
    quantile_alpha=0.025,
    n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42
)
xgb_rul_lower.fit(X_train, y_rul_train)
with open('models/xgb_rul_lower.pkl', 'wb') as f:
    pickle.dump(xgb_rul_lower, f)


# ---------------------------------------------------------
print("\n--- Training Model 2: XGBoost RUL (Quantile 0.975) ---")
xgb_rul_upper = xgb.XGBRegressor(
    objective='reg:quantileerror', 
    quantile_alpha=0.975,
    n_estimators=150, max_depth=6, learning_rate=0.05, random_state=42
)
xgb_rul_upper.fit(X_train, y_rul_train)
with open('models/xgb_rul_upper.pkl', 'wb') as f:
    pickle.dump(xgb_rul_upper, f)


# Validation of Quantile Spread
preds_lower = xgb_rul_lower.predict(X_test[:5])
preds_upper = xgb_rul_upper.predict(X_test[:5])
spreads = preds_upper - preds_lower
print(f"\nSample Quantile Spreads (Upper - Lower) for RUL:")
print(spreads.round(2))

# Save metrics
metrics_path = 'models/model_metrics.json'
if os.path.exists(metrics_path):
    with open(metrics_path, 'r') as f:
        try:
            existing = json.load(f)
            existing.update(metrics_dict)
            metrics_dict = existing
        except Exception:
            pass

with open(metrics_path, 'w') as f:
    json.dump(metrics_dict, f, indent=4)

print("\nXGBoost models and metrics successfully saved in models/ directory.")
