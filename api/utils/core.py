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

def evaluate_status(health_score: float, rul_years: float) -> dict:
    # Default status based on ML Health Score
    status_reason = "Nominal Analysis"
    if health_score > 85:
        condition = "Good"
        safety_status = "Safe"
        priority = "low"
        label = "Routine inspection in 12 months"
        color = "green"
    elif health_score > 60:
        condition = "Fair"
        safety_status = "Safe with Monitoring"
        priority = "medium"
        label = "Schedule Ultrasonic Testing within 90 days"
        color = "orange"
    else:
        condition = "Poor"
        safety_status = "Restricted Use"
        priority = "high"
        label = "Urgent Support Reinforcement Required"
        color = "orange"

    # FAIL-SAFE OVERRIDE: RUL takes precedence over Health Score for safety
    if rul_years < 3.0:
        condition = "Critical"
        safety_status = "Unsafe \u2014 Evacuate"
        priority = "critical"
        label = "IMMEDIATE STRUCTURAL AUDIT REQUIRED"
        color = "red"
        status_reason = "Imminent Failure Risk (Low RUL)"
    elif rul_years < 5.0 and condition == "Good":
        condition = "Fair"
        safety_status = "Safe with Monitoring"
        priority = "medium"
        label = "Schedule Ultrasonic Testing within 90 days"
        color = "orange"
        status_reason = "Maintenance Required (RUL Threshold)"
        
    return {
        "condition": condition,
        "safety_status": safety_status,
        "status_reason": status_reason,
        "priority_color": color, 
        "maintenance_action": {
            "priority": priority,
            "label": label,
            "color": color
        }
    }
