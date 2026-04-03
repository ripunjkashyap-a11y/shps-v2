# api/utils/core.py

FEATURE_COLUMNS = [
    'concrete_grade_mpa', 'elevation_m', 'load_kn', 'cyclic_load_freq',
    'support_type', 'env_condition', 'vibration_mms', 'age_years',
    'years_since_inspection', 'load_ratio', 'stress_index',
    'age_squared', 'degradation_rate', 'fatigue_index'
]

def calculate_engineered_features(raw: dict) -> list:
    """Compute the 14 FEATURE_COLUMNS from 9 raw API inputs."""
    age_years = 2025 - raw['construction_year']
    years_since_inspection = 2025 - raw['last_inspection_year']
    load_ratio = raw['load_kn'] / (raw['concrete_grade_mpa'] * 100.0)
    stress_index = load_ratio * (1.0 + raw['cyclic_load_freq'] / 100.0)
    age_squared = age_years ** 2
    degradation_rate = stress_index * (raw['env_condition'] + 1.0) * 0.01
    fatigue_index = (raw['cyclic_load_freq'] * age_years) / 1000.0

    features = {
        'concrete_grade_mpa': raw['concrete_grade_mpa'],
        'elevation_m': raw['elevation_m'],
        'load_kn': raw['load_kn'],
        'cyclic_load_freq': raw['cyclic_load_freq'],
        'support_type': raw['support_type'],
        'env_condition': raw['env_condition'],
        'vibration_mms': raw['vibration_mms'],
        'age_years': float(age_years),
        'years_since_inspection': float(years_since_inspection),
        'load_ratio': load_ratio,
        'stress_index': stress_index,
        'age_squared': float(age_squared),
        'degradation_rate': degradation_rate,
        'fatigue_index': fatigue_index,
    }

    return [[features[col] for col in FEATURE_COLUMNS]]

def format_pydantic_errors(e) -> list:
    """Safely format Pydantic validation errors for JSON serialization."""
    # We strip complex context objects which can cause 'Object of type ValueError is not JSON serializable'
    return [{
        "loc": err["loc"],
        "msg": err["msg"],
        "type": err["type"]
    } for err in e.errors(include_url=False, include_context=False)]

def evaluate_health_status(health_score: float) -> dict:
    # Condition + safety status logic
    if health_score > 80:
        condition, safety_status = "Good", "Safe"
    elif health_score >= 60:
        condition, safety_status = "Fair", "Safe with Monitoring"
    elif health_score >= 40:
        condition, safety_status = "Poor", "Restricted Use"
    else:
        condition, safety_status = "Critical", "Unsafe \u2014 Evacuate"

    # Maintenance action logic
    if health_score > 80:
        priority, label, color = "low", "Routine inspection in 12 months", "green"
    elif health_score >= 50:
        priority, label, color = "medium", "Schedule Ultrasonic Testing within 90 days", "orange"
    else:
        priority, label, color = "critical", "IMMEDIATE STRUCTURAL AUDIT REQUIRED", "red"
        
    return {
        "condition": condition,
        "safety_status": safety_status,
        "maintenance_action": {
            "priority": priority,
            "label": label,
            "color": color
        }
    }
