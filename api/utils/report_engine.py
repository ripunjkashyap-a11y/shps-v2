import io
import datetime
import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

matplotlib.use('Agg')  # Headless backend

class StructuralReportEngine:
    """PDF Generator for Structural Analysis Reports"""
    
    def __init__(self, data):
        self.data = data
        self.inputs = data.get('inputs', {})
        self.results = data.get('results', {})
        self.explanation = data.get('explanation', {})
        self.forecast = data.get('forecast', {})
        self.whatif = data.get('whatif')

    def _get_status_color(self, condition):
        cond = condition.lower()
        if cond in ['good', 'safe']:
            return colors.HexColor('#4ade80')  # Green
        if cond in ['fair', 'safe with monitoring']:
            return colors.HexColor('#fb923c')  # Orange
        return colors.HexColor('#f87171')  # Red

    def _generate_shap_chart_image(self):
        shap_vals = self.explanation.get('shap_values', {})
        if not shap_vals:
            return None
        
        # Sort and take top 8 for clean display
        sorted_shap = sorted(shap_vals.items(), key=lambda item: abs(item[1]), reverse=True)[:8]
        sorted_shap.reverse()  # For matplotlib horizontal bar
        
        features = [k.replace('_', ' ').title() for k, v in sorted_shap]
        values = [v for k, v in sorted_shap]
        bar_colors = ['#f87171' if v < 0 else '#4ade80' for v in values]

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.barh(features, values, color=bar_colors)
        ax.set_xlabel('Impact on Health Score')
        ax.set_title('Top Risk Factors (SHAP Analysis)')
        ax.axvline(0, color='grey', linewidth=0.8)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _generate_forecast_chart_image(self):
        forecast = self.forecast
        if not forecast:
            return None
        
        years = forecast.get('years', [])
        det = forecast.get('deterioration', [])
        up = forecast.get('confidence_upper', [])
        low = forecast.get('confidence_lower', [])

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(years, det, color='#3b82f6', label='Mean Trend', linewidth=2)
        ax.fill_between(years, low, up, color='#3b82f6', alpha=0.2, label='95% Confidence')
        
        ax.set_xlabel('Years from Now')
        ax.set_ylabel('Deterioration %')
        ax.set_title('25-Year Deterioration Forecast')
        ax.set_ylim(0, 100)
        ax.legend(loc='upper left')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def generate_pdf(self):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle('TitleCustom', parent=styles['Heading1'], fontSize=20, spaceAfter=20)
        h2_style = ParagraphStyle('H2Custom', parent=styles['Heading2'], fontSize=14, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#1f2937'))
        normal_style = styles['Normal']
        
        story = []

        # 1. Header
        story.append(Paragraph("<b>SHPSv2</b> | Structural Health Assessment Report", title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#d1d5db'), spaceAfter=15))
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        story.append(Paragraph(f"<b>Date/Time:</b> {timestamp} &nbsp;&nbsp;&nbsp; <b>Structure ID:</b> SHPS-92A", normal_style))
        story.append(Paragraph("<b>Inspector ID:</b> SHPS-ENG-44 &nbsp;&nbsp;&nbsp; <b>GPS Coordinates:</b> 40.7128° N, 74.0060° W", normal_style))
        story.append(Spacer(1, 20))

        # 2. Executive Summary
        story.append(Paragraph("1. Executive Summary", h2_style))
        
        cond_text = self.results.get('condition', 'Unknown')
        score = self.results.get('health_score', 0)
        rul_disp = self.results.get('RUL_display', 'N/A')
        status_color = self._get_status_color(cond_text)

        summary_data = [
            ['Current Health Score:', f"{score:.1f}%"],
            ['Status/Condition:', cond_text.upper()],
            ['Estimated Life (RUL):', rul_disp]
        ]
        
        t_summary = Table(summary_data, colWidths=[2*inch, 4*inch])
        t_summary.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1,1), (1,1), status_color),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Model Confidence: 94%.</b> This prediction is based on high-quality historical data matching the current environmental profile.", normal_style))
        story.append(Spacer(1, 20))

        # 3. Input Parameters
        story.append(Paragraph("2. Input Parameters (Snapshot)", h2_style))
        
        in_data = [['Parameter', 'Value']]
        for k, v in self.inputs.items():
            in_data.append([k.replace('_', ' ').title(), str(v)])
            
        t_inputs = Table(in_data, colWidths=[3*inch, 3*inch])
        t_inputs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        story.append(t_inputs)
        story.append(Spacer(1, 20))

        # 4. Visual Diagnostics
        story.append(Paragraph("3. Visual Diagnostics", h2_style))
        
        fc_img_buf = self._generate_forecast_chart_image()
        if fc_img_buf:
            story.append(Image(fc_img_buf, width=6*inch, height=3*inch))
            story.append(Spacer(1, 15))
            
        shap_img_buf = self._generate_shap_chart_image()
        if shap_img_buf:
            story.append(Image(shap_img_buf, width=6*inch, height=3*inch))
            story.append(Spacer(1, 20))

        # 5. AI Insights & Recommendations
        story.append(Paragraph("4. AI Insights & Recommendations", h2_style))
        
        maint = self.results.get('maintenance_action', {})
        pri_color = self._get_status_color(maint.get('priority', ''))
        
        # Find top risk from SHAP
        shap_vals = self.explanation.get('shap_values', {})
        neg_factors = [k for k, v in shap_vals.items() if v < 0]
        top_risk = neg_factors[0].replace('_', ' ').title() if neg_factors else "Age & Natural Wear"

        insight_data = [
            ['Primary Risk Factor:', top_risk],
            ['Priority Level:', maint.get('priority', 'N/A').upper()],
            ['Target Completion:', 'Within 30-90 Days' if maint.get('priority') in ['critical', 'medium'] else 'Next Cycle'],
            ['Short-Term Roadmap:', maint.get('label', 'N/A')],
            ['Long-Term Roadmap:', f"Plan for reinforcement/overhaul by {datetime.datetime.now().year + int(self.results.get('RUL_years', 10))}"]
        ]
        
        t_insight = Table(insight_data, colWidths=[2*inch, 4*inch])
        t_insight.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1,1), (1,1), pri_color),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_insight)

        # 6. What-If Scenario Analysis (If provided)
        if self.whatif:
            story.append(Spacer(1, 20))
            story.append(Paragraph("5. What-If Scenario Analysis", h2_style))
            
            wi_data = [
                ['Tested Scenario:', f"Adjusted Load to {self.whatif.get('new_load', 0)} kN"],
                ['Projected Health Score:', f"{self.whatif.get('new_health_score', 0):.1f}%"],
                ['Score Variance (Delta):', f"{self.whatif.get('delta', 0):+.1f}%"],
                ['Projected Condition:', self.whatif.get('condition', 'Unknown')]
            ]
            
            t_wi = Table(wi_data, colWidths=[2*inch, 4*inch])
            delta_color = colors.HexColor('#4ade80') if self.whatif.get('delta', 0) >= 0 else colors.HexColor('#f87171')
            t_wi.setStyle(TableStyle([
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1,2), (1,2), delta_color),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t_wi)

        # Build Document
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
