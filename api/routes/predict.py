from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import xgboost as xgb
from api.schemas import StructureInput
from api.model_loader import XGB_HEALTH, XGB_RUL, XGB_RUL_LOWER, XGB_RUL_UPPER
from api.utils.core import calculate_engineered_features, evaluate_status, format_pydantic_errors, FEATURE_COLUMNS

predict_bp = Blueprint('predict', __name__)

@predict_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        validated = StructureInput(**data)
        raw_dict = validated.model_dump()

    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": format_pydantic_errors(e)}), 422

    X = calculate_engineered_features(raw_dict)
    dmat = xgb.DMatrix(X, feature_names=FEATURE_COLUMNS)

    # Models are module-level Booster globals
    health_score = float(XGB_HEALTH.predict(dmat)[0])
    rul_median   = float(XGB_RUL.predict(dmat)[0])
    rul_lower    = float(XGB_RUL_LOWER.predict(dmat)[0])
    rul_upper    = float(XGB_RUL_UPPER.predict(dmat)[0])

    # Boundary clamps
    health_score = max(0.0, min(100.0, health_score))
    rul_median = max(0.0, rul_median)
    rul_lower  = max(0.0, rul_lower)
    rul_upper  = max(0.0, rul_upper)
    status_data = evaluate_status(health_score, rul_median)

    # Calculate unified margin based on confidence interval
    margin = (rul_upper - rul_lower) / 2.0

    return jsonify({
        "health_score": round(health_score, 1),
        "condition": status_data["condition"],
        "safety_status": status_data["safety_status"],
        "status_reason": status_data["status_reason"],
        "priority_color": status_data["priority_color"],
        "margin": round(margin, 1),
        "RUL_years": round(rul_median, 1),
        "RUL_confidence_low": round(rul_lower, 1),
        "RUL_confidence_high": round(rul_upper, 1),
        "RUL_display": f"{round(rul_median, 1)} years (\u00b1{round(margin, 1)} years at 95% confidence)",
        "maintenance_action": status_data["maintenance_action"]
    })
