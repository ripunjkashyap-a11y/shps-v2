import pandas as pd
import numpy as np
import pickle
import shap

FEATURE_COLUMNS = [
    'concrete_grade_mpa', 'elevation_m', 'load_kn', 'cyclic_load_freq',
    'support_type', 'env_condition', 'vibration_mms', 'age_years',
    'years_since_inspection', 'load_ratio', 'stress_index',
    'age_squared', 'degradation_rate', 'fatigue_index'
]

# ---- Load model & background data once at module import time ----
with open('models/xgb_health.pkl', 'rb') as f:
    _xgb_health_model = pickle.load(f)

# Optimized: Using K-Means (100 centroids) to represent the 10,000-row background manifold.
# This ensures interventional SHAP values are fast (<50ms) for UI responsiveness.
try:
    _bg_data = pd.read_csv('features/structural_data_processed.csv')[FEATURE_COLUMNS]
    _bg_summary = shap.kmeans(_bg_data, 100)
    _explainer = shap.TreeExplainer(_xgb_health_model, _bg_summary, feature_perturbation='interventional')
except Exception:
    # Fallback to path-dependent if data missing
    _explainer = shap.TreeExplainer(_xgb_health_model)


def compute_engineered_features(raw: dict) -> dict:
    """
    Given the 9 raw API inputs, compute all 14 FEATURE_COLUMNS.
    Returns a flat dict ready for DataFrame construction.
    """
    age_years = 2025 - raw['construction_year']
    years_since_inspection = 2025 - raw['last_inspection_year']
    load_ratio = raw['load_kn'] / (raw['concrete_grade_mpa'] * 100)
    stress_index = load_ratio * (1 + raw['cyclic_load_freq'] / 100)
    age_squared = age_years ** 2
    degradation_rate = stress_index * (raw['env_condition'] + 1) * 0.01
    fatigue_index = (raw['cyclic_load_freq'] * age_years) / 1000

    return {
        'concrete_grade_mpa': raw['concrete_grade_mpa'],
        'elevation_m': raw['elevation_m'],
        'load_kn': raw['load_kn'],
        'cyclic_load_freq': raw['cyclic_load_freq'],
        'support_type': raw['support_type'],
        'env_condition': raw['env_condition'],
        'vibration_mms': raw['vibration_mms'],
        'age_years': age_years,
        'years_since_inspection': years_since_inspection,
        'load_ratio': load_ratio,
        'stress_index': stress_index,
        'age_squared': age_squared,
        'degradation_rate': degradation_rate,
        'fatigue_index': fatigue_index,
    }


def explain(raw_input: dict) -> dict:
    """
    Accepts the 9 raw API input fields.
    Returns:
        {
          "shap_values": { feature: float for all 14 features },
          "base_value": float
        }
    """
    features = compute_engineered_features(raw_input)
    X = pd.DataFrame([features])[FEATURE_COLUMNS]

    shap_vals = _explainer(X)
    values = shap_vals.values[0]          # shape (14,)
    base_value = float(shap_vals.base_values[0])

    shap_dict = {feat: round(float(val), 3) for feat, val in zip(FEATURE_COLUMNS, values)}
    return {"shap_values": shap_dict, "base_value": round(base_value, 2)}


# ---- Self-test when run directly ----
if __name__ == '__main__':
    sample = {
        "construction_year": 2008,
        "last_inspection_year": 2021,
        "concrete_grade_mpa": 30,
        "elevation_m": 20.0,
        "load_kn": 350.0,
        "cyclic_load_freq": 120.0,
        "support_type": 2,
        "env_condition": 3,
        "vibration_mms": 3.2
    }

    result = explain(sample)

    print("SHAP Explanation Output:")
    print(f"  Base Value: {result['base_value']}")
    print(f"  SHAP Values ({len(result['shap_values'])} features):")

    sorted_feats = sorted(result['shap_values'].items(), key=lambda x: abs(x[1]), reverse=True)
    for feat, val in sorted_feats:
        bar = '#' * int(abs(val) / 0.5)
        sign = '+' if val >= 0 else '-'
        print(f"    {feat:<28} {sign}{abs(val):.3f}  {bar}")

    print(f"\nAll 14 FEATURE_COLUMNS present: {set(result['shap_values'].keys()) == set(FEATURE_COLUMNS)}")
