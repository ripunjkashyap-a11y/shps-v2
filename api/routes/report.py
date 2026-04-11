from flask import Blueprint, request, jsonify, send_file
import io
from api.utils.report_engine import StructuralReportEngine

report_bp = Blueprint('report', __name__)

@report_bp.route('/report', methods=['POST'])
def generate_report():
    try:
        # Support both JSON fetch and traditional Form submission for direct downloads
        if request.is_json:
            data = request.get_json()
        elif 'report_data' in request.form:
            import json
            data = json.loads(request.form.get('report_data'))
        else:
            return jsonify({"error": "No report data provided"}), 400
        
        if not data:
            return jsonify({"error": "Empty data provided"}), 400
            
        # Data contains nested results from the UI
        required_keys = ['inputs', 'results', 'explanation', 'forecast']
        for k in required_keys:
            if k not in data:
                return jsonify({"error": f"Missing required nested data: {k}"}), 400
                
        # Generate the PDF in-memory
        engine = StructuralReportEngine(data)
        pdf_bytes = engine.generate_pdf()
        
        # Send as file download
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='SHPSv2_Structural_Report.pdf'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
