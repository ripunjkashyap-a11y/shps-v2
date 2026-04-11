from flask import Blueprint, jsonify
import random
import os
import json

simulate_bp = Blueprint('simulate', __name__)

@simulate_bp.route('/simulate', methods=['GET'])
def simulate():
    # Generate randomized values that are guaranteed to satisfy all physics constraints.

    # 1. Temporal integrity
    construction_year    = random.randint(1960, 2020)
    last_inspection_year = random.randint(max(1990, construction_year), 2025)

    # 2. Support type — determines maximum allowable load
    support_type = random.randint(0, 3)
    load_max = {
        0: 3500.0,   # Simply Supported — no moment fixity
        1: 5000.0,   # One Side Fixed
        2: 5000.0,   # Both Sides Fixed
        3: 2500.0,   # Cantilever — most vulnerable
    }[support_type]

    # 3. Environment — determines minimum concrete grade
    env_condition = random.randint(0, 6)
    if env_condition >= 5:          # Hot-Arid / Industrial-Chemical
        concrete_pool = [30, 35, 40, 45, 50]
    elif env_condition >= 3:        # Coastal / Freeze-Thaw
        concrete_pool = [25, 30, 35, 40, 45, 50]
    else:
        concrete_pool = [20, 25, 30, 35, 40, 45, 50]
    concrete_grade_mpa = random.choice(concrete_pool)

    # 4. Load — must respect both support-type cap and concrete-grade cap
    if concrete_grade_mpa < 25:
        concrete_load_cap = 3000.0
    elif concrete_grade_mpa < 30:
        concrete_load_cap = 4000.0
    else:
        concrete_load_cap = 5000.0
    load_max = min(load_max, concrete_load_cap)
    load_kn = round(random.uniform(100.0, load_max), 1)

    return jsonify({
        "construction_year":   construction_year,
        "last_inspection_year": last_inspection_year,
        "concrete_grade_mpa":  concrete_grade_mpa,
        "elevation_m":         round(random.uniform(0.0, 150.0), 1),
        "load_kn":             load_kn,
        "cyclic_load_freq":    round(random.uniform(10.0, 500.0), 1),
        "support_type":        support_type,
        "env_condition":       env_condition,
        "vibration_mms":       round(random.uniform(0.1, 12.0), 1),
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
