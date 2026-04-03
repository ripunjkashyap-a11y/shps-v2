from flask import Blueprint, jsonify
import random
import os
import json

simulate_bp = Blueprint('simulate', __name__)

@simulate_bp.route('/simulate', methods=['GET'])
def simulate():
    # Helper route retrieving randomized realistic values aligned with Pydantic boundaries
    return jsonify({
        "construction_year": random.randint(1960, 2025),
        "last_inspection_year": random.randint(1990, 2025),
        "concrete_grade_mpa": random.choice([20, 25, 30, 35, 40, 45, 50]),
        "elevation_m": round(random.uniform(0.0, 150.0), 1),
        "load_kn": round(random.uniform(100.0, 5000.0), 1),
        "cyclic_load_freq": round(random.uniform(10.0, 500.0), 1),
        "support_type": random.randint(0, 3),
        "env_condition": random.randint(0, 6),
        "vibration_mms": round(random.uniform(0.1, 12.0), 1)
    })

@simulate_bp.route('/model-info', methods=['GET'])
def model_info():
    # Reads the model_metrics JSON artifact generated from training loops
    metrics_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'model_metrics.json'))
    
    try:
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": "Failed loading metrics", "details": str(e)}), 500
