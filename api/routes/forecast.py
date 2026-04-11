from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from api.schemas import StructureInput
from api.model_loader import LSTM_DETERIORATION
from api.utils.core import calculate_engineered_features, format_pydantic_errors
import numpy as np

forecast_bp = Blueprint('forecast', __name__)

@forecast_bp.route('/forecast', methods=['POST'])
def forecast():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        validated = StructureInput(**data)
        raw_dict = validated.model_dump()

    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": format_pydantic_errors(e)}), 422

    if LSTM_DETERIORATION is None:
        years = list(range(1, 26))
        return jsonify({
            "unavailable": True,
            "message": "Forecast model not trained. Run models/train_lstm.py.",
            "years": years,
            "deterioration": [],
            "confidence_upper": [],
            "confidence_lower": []
        })

    X = calculate_engineered_features(raw_dict)

    # Predict with LSTM returning 25 values per sample
    deterioration_pred = LSTM_DETERIORATION.predict(np.array(X), verbose=0)[0]
    
    years = list(range(1, 26))
    
    # Output raw predictions mapped to cumulative natural monotonic bounds
    det_list = []
    upper_list = []
    lower_list = []
    
    curr_max = 0.0
    for val in deterioration_pred:
        val = max(0.0, float(val))
        curr_max = max(curr_max, val)
        curr_max = min(100.0, curr_max)
        det_list.append(round(curr_max, 2))
        
        # Upper and lower bounds defined by instructions: +/- 10%
        upper = min(100.0, curr_max * 1.10)
        lower = max(0.0, curr_max * 0.90)
        
        upper_list.append(round(upper, 2))
        lower_list.append(round(lower, 2))

    return jsonify({
        "years": years,
        "deterioration": det_list,
        "confidence_upper": upper_list,
        "confidence_lower": lower_list
    })
