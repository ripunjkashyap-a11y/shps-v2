from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import xgboost as xgb
from api.schemas import WhatIfInput, StructureInput
from api.model_loader import XGB_HEALTH, XGB_RUL
from api.utils.core import calculate_engineered_features, evaluate_status, format_pydantic_errors, FEATURE_COLUMNS

whatif_bp = Blueprint('whatif', __name__)

@whatif_bp.route('/whatif', methods=['POST'])
def whatif():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        validated = WhatIfInput(**data)
        
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": format_pydantic_errors(e)}), 422

    # Parse baseline
    base_params = validated.base_params.model_dump()
    X_base = calculate_engineered_features(base_params)
    health_base = float(XGB_HEALTH.predict(xgb.DMatrix(X_base, feature_names=FEATURE_COLUMNS))[0])
    health_base = max(0.0, min(100.0, health_base))

    # Apply the single requested change
    new_params = base_params.copy()
    if validated.changed_field in new_params:
        new_params[validated.changed_field] = validated.changed_value
    else:
        return jsonify({"error": f"Invalid field '{validated.changed_field}'"}), 400

    # RE-VALIDATE PHYSICS LOGIC FOR THE NEW STATE
    try:
        StructureInput(**new_params)
    except ValidationError as e:
        return jsonify({"error": "Validation Error (Physics Collision)", "details": format_pydantic_errors(e)}), 422

    # Calculate what-if results
    X_new = calculate_engineered_features(new_params)
    dmat_new = xgb.DMatrix(X_new, feature_names=FEATURE_COLUMNS)
    
    health_new = float(XGB_HEALTH.predict(dmat_new)[0])
    rul_new = float(XGB_RUL.predict(dmat_new)[0])
    
    health_new = max(0.0, min(100.0, health_new))
    rul_new = max(0.0, rul_new)
    
    delta = health_new - health_base

    status_data = evaluate_status(health_new, rul_new)

    return jsonify({
        "health_score": round(health_new, 1),
        "delta": round(delta, 1),
        "condition": status_data["condition"],
        "priority_color": status_data["priority_color"],
        "maintenance_action": status_data["maintenance_action"]
    })
