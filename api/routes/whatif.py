from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from api.schemas import WhatIfInput
from api.model_loader import XGB_HEALTH
from api.utils.core import calculate_engineered_features, evaluate_health_status, format_pydantic_errors

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
    health_base = float(XGB_HEALTH.predict(X_base)[0])
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
    health_new = float(XGB_HEALTH.predict(X_new)[0])
    health_new = max(0.0, min(100.0, health_new))
    
    delta = health_new - health_base

    status_data = evaluate_health_status(health_new)

    return jsonify({
        "health_score": round(health_new, 1),
        "delta": round(delta, 1),
        "condition": status_data["condition"],
        "maintenance_action": status_data["maintenance_action"]
    })
