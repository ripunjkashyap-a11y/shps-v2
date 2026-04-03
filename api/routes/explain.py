from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from api.schemas import StructureInput
from explainability.shap_explainer import explain
from api.utils.core import format_pydantic_errors

explain_bp = Blueprint('explain', __name__)

@explain_bp.route('/explain', methods=['POST'])
def explain_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        validated = StructureInput(**data)
        raw_dict = validated.model_dump()

    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": format_pydantic_errors(e)}), 422

    # The explain module expects the 9 raw API inputs directly.
    result = explain(raw_dict)
    
    # Ensure they are sorted by absolute impact as requested
    shap_dict = result['shap_values']
    sorted_features = dict(sorted(shap_dict.items(), key=lambda item: abs(item[1]), reverse=True))
    result['shap_values'] = sorted_features
    
    return jsonify(result)
