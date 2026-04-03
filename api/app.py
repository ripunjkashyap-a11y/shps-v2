import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, jsonify
from flask_cors import CORS

# Import model_loader first — this triggers the one-time global load
import api.model_loader  # noqa: F401

from api.routes.predict import predict_bp
from api.routes.forecast import forecast_bp
from api.routes.explain import explain_bp
from api.routes.whatif import whatif_bp
from api.routes.simulate import simulate_bp
from api.routes.report import report_bp

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, 'templates'),
    static_folder=os.path.join(PROJECT_ROOT, 'static')
)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.errorhandler(500)
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the traceback to console for diagnostics
    import traceback
    print("[SERVER CRASH] Detailed Traceback:")
    traceback.print_exc()
    
    # Return a JSON error for the frontend to catch
    return jsonify({
        "error": "Internal Server Error",
        "message": str(e),
        "type": type(e).__name__
    }), 500


app.register_blueprint(predict_bp)
app.register_blueprint(forecast_bp)
app.register_blueprint(explain_bp)
app.register_blueprint(whatif_bp)
app.register_blueprint(simulate_bp)
app.register_blueprint(report_bp)

if __name__ == '__main__':
    print(f"DEBUG: Starting server on 127.0.0.1:5005")
    app.run(host='0.0.0.0', port=5005, debug=True)
