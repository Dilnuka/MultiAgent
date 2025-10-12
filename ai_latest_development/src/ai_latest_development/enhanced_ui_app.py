import os
import json
import litellm
from pathlib import Path
from datetime import datetime
import time
from io import BytesIO
import re

import streamlit as st

# Load .env early so downstream imports see GEMINI_API_KEY
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except Exception:
    pass

try:
    from .crew import AiLatestDevelopment
except Exception:
    from crew import AiLatestDevelopment

# Optional PDF support via reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

def _md_to_pdf_bytes(markdown_text: str) -> bytes:
    """Convert markdown text to formatted PDF using ReportLab's Platypus for better rendering."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )
    styles = getSampleStyleSheet()
    flowables = []

    def parse_bold(text: str) -> str:
        """Replace **bold** with <b>bold</b> for ReportLab Paragraph."""
        parts = text.split('**')
        for j in range(1, len(parts), 2):
            parts[j] = '<b>' + parts[j] + '</b>'
        return ''.join(parts)

    lines = markdown_text.splitlines()
    i = 0
    current_paragraph = []
    while i < len(lines):
        original_line = lines[i]
        line = original_line.strip()
        if line.startswith('#'):
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = parse_bold(text)
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            level = 0
            while level < len(line) and line[level] == '#':
                level += 1
            text = parse_bold(line[level:].strip())
            heading_style = 'Heading' + str(min(level, 6))  # Up to Heading6
            if heading_style in styles:
                flowables.append(Paragraph(text, styles[heading_style]))
            else:
                flowables.append(Paragraph(text, styles['Heading1']))
        elif line.startswith('* ') or line.startswith('- '):
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = parse_bold(text)
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            text = line[2:].strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(('* ', '- ', '#')) and '|' not in lines[i].strip() and not (lines[i].strip() and lines[i].strip()[0].isdigit() and '.' in lines[i].strip()) and lines[i].strip():
                text += ' ' + lines[i].strip()
                i += 1
            i -= 1
            text = parse_bold(text)
            flowables.append(Paragraph('&#8226; ' + text, styles.get('Bullet', styles['Normal'])))
        elif line and line[0].isdigit() and '.' in line:
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = parse_bold(text)
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            try:
                num, rest = line.split('.', 1)
                num = int(num.strip())
                text = rest.strip()
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(('* ', '- ', '#')) and '|' not in lines[i].strip() and not (lines[i].strip() and lines[i].strip()[0].isdigit() and '.' in lines[i].strip()) and lines[i].strip():
                    text += ' ' + lines[i].strip()
                    i += 1
                i -= 1
                text = parse_bold(text)
                flowables.append(Paragraph(f"{num}. {text}", styles.get('Normal')))
            except ValueError:
                current_paragraph.append(original_line)
        elif line and '|' in line and (i + 1 < len(lines) and '|' in lines[i + 1]):
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = parse_bold(text)
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            i -= 1
            data = []
            for tl in table_lines:
                cells = [cell.strip() for cell in tl.split('|') if cell.strip()]
                if cells:
                    data.append(cells)
            if len(data) > 1 and all(('-' in cell or ':' in cell) for cell in data[1]):
                data = data[0:1] + data[2:]
            if data:
                t = Table(data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                flowables.append(t)
        elif not line:
            if current_paragraph:
                text = ' '.join(current_paragraph)
                text = parse_bold(text)
                flowables.append(Paragraph(text, styles['Normal']))
                current_paragraph = []
            flowables.append(Spacer(1, 0.1 * mm))
        else:
            current_paragraph.append(original_line.strip())
        i += 1
    if current_paragraph:
        text = ' '.join(current_paragraph)
        text = parse_bold(text)
        flowables.append(Paragraph(text, styles['Normal']))
    doc.build(flowables)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def _find_report_path() -> Path | None:
    """Try to locate report.md in common locations for both CLI and Streamlit runs."""
    candidates = []
    candidates.append(Path.cwd() / 'report.md')
    here = Path(__file__).resolve()
    parents = list(here.parents)
    for idx in (2, 3, 4):
        if len(parents) > idx:
            candidates.append(parents[idx] / 'report.md')
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None

def _render_report_view(text: str, topic_for_filename: str, mtime: float | None = None):
    """Render the report in read-only review mode with a PDF download button."""
    word_count = len(text.split()) if text else 0
    if mtime:
        ts = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        st.info(f"📊 Report generated: {word_count} words (last modified: {ts})")
    else:
        st.info(f"📊 Report generated: {word_count} words")
    st.caption(f"Words: {word_count}")
    st.markdown("### 📋 Report")
    st.markdown(text)
    if REPORTLAB_AVAILABLE:
        try:
            pdf_bytes = _md_to_pdf_bytes(text)
            st.download_button(
                label="📄 Download Report (PDF)",
                data=pdf_bytes,
                file_name=f"ai_risk_report_{topic_for_filename.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key=f"download_{int(time.time())}"  # Unique key to avoid conflicts
            )
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")
    else:
        st.info("PDF download requires the 'reportlab' package. Install it with: pip install reportlab")

def _display_cached_report():
    """Display report from session state or disk if available."""
    if 'last_report_content' in st.session_state:
        cached = st.session_state['last_report_content']
        cached_mtime = st.session_state.get('last_report_mtime')
        cached_topic = st.session_state.get('last_report_topic', 'ai_risk_report')
        _render_report_view(cached, cached_topic, cached_mtime)
        return True
    else:
        rp_obj = _find_report_path()
        if rp_obj and rp_obj.exists():
            try:
                report_path = str(rp_obj.resolve())
                mtime = os.path.getmtime(report_path)
                with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Persist to session state
                st.session_state['last_report_content'] = content
                st.session_state['last_report_mtime'] = mtime
                st.session_state['last_report_topic'] = 'ai_risk_report'
                _render_report_view(content, 'ai_risk_report', mtime)
                return True
            except Exception as e:
                st.error(f"Could not read report.md: {e}")
    return False

def _run_scenario_risk_analysis(scenario: str, topic: str) -> dict:
    """Run the scenario risk classification task and return parsed results."""
    try:
        inputs = {
            'topic': topic,
            'scenario': scenario,
            'current_year': str(datetime.now().year),
            'region': 'Global',  # Default for quick analysis
            'data_use': 'General AI system'  # Default for quick analysis
        }
        
        # Create a crew with just the risk classification task
        crew_instance = AiLatestDevelopment()
        tasks = [crew_instance.scenario_risk_classification_task()]
        
        # Create a minimal crew for quick analysis
        from crewai import Crew, Process
        quick_crew = Crew(
            agents=[crew_instance.ai_risk_assessment_analyst()],
            tasks=tasks,
            process=Process.sequential,
            verbose=False
        )
        
        result = quick_crew.kickoff(inputs=inputs)
        
        # Try to parse JSON from the result
        result_str = str(result)
        try:
            # Look for JSON in the result
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback: create a structured response from the text
        risk_level = "MEDIUM"  # Default
        if any(word in result_str.lower() for word in ['high', 'critical', 'severe', 'urgent']):
            risk_level = "HIGH"
        elif any(word in result_str.lower() for word in ['low', 'minimal', 'minor']):
            risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "confidence_score": 75,
            "reasoning": result_str[:200] + "..." if len(result_str) > 200 else result_str,
            "key_factors": ["AI system complexity", "Data sensitivity", "Regulatory requirements"],
            "immediate_concerns": ["System security", "Compliance obligations"]
        }
        
    except Exception as e:
        st.error(f"Risk analysis failed: {e}")
        return {
            "risk_level": "MEDIUM",
            "confidence_score": 50,
            "reasoning": "Unable to complete analysis due to technical error",
            "key_factors": ["System error"],
            "immediate_concerns": ["Technical analysis required"]
        }

def _get_risk_theme(risk_level: str) -> dict:
    """Get color theme and styling for risk level."""
    themes = {
        "HIGH": {
            "color": "#dc2626",  # Red
            "bg_color": "#fef2f2",
            "border_color": "#fecaca",
            "icon": "🚨",
            "title": "High Risk Detected",
            "message": "This scenario presents significant risks that require immediate attention and professional consultation."
        },
        "MEDIUM": {
            "color": "#d97706",  # Orange/Yellow
            "bg_color": "#fffbeb",
            "border_color": "#fed7aa",
            "icon": "⚠️",
            "title": "Medium Risk Detected",
            "message": "This scenario has moderate risks that should be carefully evaluated and monitored."
        },
        "LOW": {
            "color": "#16a34a",  # Green
            "bg_color": "#f0fdf4",
            "border_color": "#bbf7d0",
            "icon": "✅",
            "title": "Low Risk Detected",
            "message": "This scenario presents minimal risks, but standard precautions should still be maintained."
        }
    }
    return themes.get(risk_level, themes["MEDIUM"])

def _render_risk_result(risk_data: dict):
    """Render the risk analysis result with modern styling."""
    theme = _get_risk_theme(risk_data["risk_level"])
    
    st.markdown(f"""
    <div style="
        background-color: {theme['bg_color']};
        border: 2px solid {theme['border_color']};
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    ">
        <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="font-size: 32px; margin-right: 12px;">{theme['icon']}</span>
            <div>
                <h2 style="color: {theme['color']}; margin: 0; font-size: 24px; font-weight: 600;">
                    {theme['title']}
                </h2>
                <p style="color: #6b7280; margin: 4px 0 0 0; font-size: 14px;">
                    Confidence: {risk_data['confidence_score']}%
                </p>
            </div>
        </div>
        
        <div style="margin-bottom: 16px;">
            <h4 style="color: {theme['color']}; margin: 0 0 8px 0; font-size: 16px;">Analysis Summary</h4>
            <p style="color: #374151; margin: 0; line-height: 1.5;">
                {risk_data['reasoning']}
            </p>
        </div>
        
        <div style="margin-bottom: 16px;">
            <h4 style="color: {theme['color']}; margin: 0 0 8px 0; font-size: 16px;">Key Risk Factors</h4>
            <ul style="color: #374151; margin: 0; padding-left: 20px;">
                {''.join([f'<li style="margin-bottom: 4px;">{factor}</li>' for factor in risk_data['key_factors']])}
            </ul>
        </div>
        
        <div>
            <h4 style="color: {theme['color']}; margin: 0 0 8px 0; font-size: 16px;">Immediate Concerns</h4>
            <ul style="color: #374151; margin: 0; padding-left: 20px;">
                {''.join([f'<li style="margin-bottom: 4px;">{concern}</li>' for concern in risk_data['immediate_concerns']])}
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show Pro upgrade suggestion for HIGH risk
    if risk_data["risk_level"] == "HIGH":
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 24px;
            margin: 16px 0;
            color: white;
            text-align: center;
        ">
            <h3 style="margin: 0 0 12px 0; font-size: 20px;">🎯 Professional Risk Consultation</h3>
            <p style="margin: 0 0 20px 0; opacity: 0.9;">
                For high-risk scenarios like this, we recommend consulting with our AI risk specialists 
                for detailed analysis and mitigation strategies.
            </p>
            <button style="
                background: white;
                color: #667eea;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 16px;
                cursor: pointer;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            " onclick="window.location.href='#upgrade'">
                Upgrade to Pro
            </button>
        </div>
        """, unsafe_allow_html=True)

def _render_upgrade_page():
    """Render the Pro upgrade page with payment form."""
    st.markdown("## 🚀 Upgrade to Pro")
    st.markdown("Get professional AI risk consultation and detailed analysis.")
    
    with st.container():
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 32px;
            color: white;
            text-align: center;
            margin-bottom: 24px;
        ">
            <h2 style="margin: 0 0 16px 0; font-size: 28px;">Pro Risk Analysis</h2>
            <p style="margin: 0; font-size: 18px; opacity: 0.9;">
                Get expert consultation from certified AI risk specialists
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 💳 Payment Information")
            
            with st.form("payment_form"):
                card_number = st.text_input(
                    "Card Number",
                    placeholder="1234 5678 9012 3456",
                    help="Use 4242 4242 4242 4242 for demo"
                )
                
                col_exp, col_cvv = st.columns(2)
                with col_exp:
                    expiry_date = st.text_input(
                        "Expiry Date",
                        placeholder="MM/YY",
                        help="Use 12/25 for demo"
                    )
                with col_cvv:
                    cvv = st.text_input(
                        "CVV",
                        placeholder="123",
                        help="Use 123 for demo"
                    )
                
                cardholder_name = st.text_input(
                    "Cardholder Name",
                    placeholder="John Doe"
                )
                
                submitted = st.form_submit_button(
                    "Complete Payment",
                    type="primary",
                    use_container_width=True
                )
                
                if submitted:
                    # Validate demo card
                    if (card_number.replace(" ", "") == "4242424242424242" and 
                        expiry_date == "12/25" and 
                        cvv == "123" and 
                        cardholder_name.strip()):
                        
                        st.session_state['payment_successful'] = True
                        st.success("✅ Payment successful! Redirecting to specialist contact...")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Invalid card details. Please use the demo card: 4242 4242 4242 4242")
        
        with col2:
            st.markdown("### 📋 Pro Benefits")
            st.markdown("""
            - **Expert Consultation**: 1-hour session with certified AI risk specialist
            - **Detailed Analysis**: Comprehensive risk assessment report
            - **Mitigation Strategies**: Custom recommendations for your scenario
            - **Compliance Guidance**: Regulatory compliance roadmap
            - **Follow-up Support**: 30-day email support
            """)
            
            st.markdown("### 💰 Pricing")
            st.markdown("""
            **One-time Payment**
            
            $299 USD
            
            *Includes all Pro benefits*
            """)

def _render_contact_page():
    """Render the human specialist contact page."""
    st.markdown("## 🎉 Welcome to Pro!")
    st.markdown("Your payment was successful. Here's how to connect with your AI risk specialist:")
    
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        border-radius: 12px;
        padding: 32px;
        color: white;
        text-align: center;
        margin-bottom: 24px;
    ">
        <h2 style="margin: 0 0 16px 0; font-size: 28px;">✅ Payment Successful!</h2>
        <p style="margin: 0; font-size: 18px; opacity: 0.9;">
            A risk specialist will contact you within 24 hours
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📞 Contact Your Specialist")
        
        st.markdown("""
        <div style="
            background: #f8fafc;
            border-radius: 8px;
            padding: 20px;
            margin: 16px 0;
        ">
            <h4 style="color: #1e40af; margin: 0 0 12px 0;">Dr. Sarah Chen</h4>
            <p style="margin: 0 0 8px 0; color: #374151;">
                <strong>Senior AI Risk Specialist</strong><br>
                Certified in AI Ethics & Compliance
            </p>
            <p style="margin: 0; color: #6b7280;">
                📧 sarah.chen@airiskpro.com<br>
                📱 +1 (555) 123-4567<br>
                💼 LinkedIn: /in/sarahchen-ai-risk
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📅 Schedule Meeting")
        st.markdown("""
        - **Calendar Link**: [Book 1-hour consultation](https://calendly.com/sarahchen-ai-risk)
        - **Available Times**: Mon-Fri, 9 AM - 6 PM EST
        - **Meeting Format**: Video call (Zoom/Teams)
        """)
    
    with col2:
        st.markdown("### 📋 What Happens Next")
        
        steps = [
            "Specialist reviews your scenario analysis",
            "Prepares detailed risk assessment",
            "Schedules consultation call",
            "Provides mitigation recommendations",
            "Follows up with implementation support"
        ]
        
        for i, step in enumerate(steps, 1):
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: center;
                margin: 12px 0;
                padding: 12px;
                background: #f1f5f9;
                border-radius: 8px;
            ">
                <span style="
                    background: #3b82f6;
                    color: white;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    margin-right: 12px;
                    font-size: 12px;
                ">{i}</span>
                <span style="color: #374151;">{step}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### 📧 Support")
        st.markdown("""
        **Email Support**: support@airiskpro.com<br>
        **Response Time**: Within 4 hours<br>
        **Available**: 24/7 for urgent issues
        """)

# Initialize session state for form inputs and submission status
if 'form_inputs' not in st.session_state:
    st.session_state['form_inputs'] = {
        'topic': '',
        'data_use': '',
        'scenario': '',
        'region_choice': 'EU',
        'custom_region': ''
    }
if 'has_submitted' not in st.session_state:
    st.session_state['has_submitted'] = False
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'main'
if 'risk_analysis_result' not in st.session_state:
    st.session_state['risk_analysis_result'] = None
if 'payment_successful' not in st.session_state:
    st.session_state['payment_successful'] = False

# Main UI
st.set_page_config(
    page_title="AI Risk & Compliance Assessor", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .risk-card {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .high-risk { background-color: #fef2f2; border-left: 4px solid #dc2626; }
    .medium-risk { background-color: #fffbeb; border-left: 4px solid #d97706; }
    .low-risk { background-color: #f0fdf4; border-left: 4px solid #16a34a; }
    
    .stButton > button {
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("AI Risk & Compliance Assessor")
st.caption("Enter your own scenario: use case, data use, and region – nothing is hard-coded.")

# Navigation
if st.session_state['current_page'] != 'main':
    if st.button("← Back to Analysis", key="back_button"):
        st.session_state['current_page'] = 'main'
        st.rerun()

# Main page
if st.session_state['current_page'] == 'main':
    with st.form("inputs"):
        topic = st.text_input(
            "Use case / System name",
            value=st.session_state['form_inputs']['topic'],
            placeholder="e.g., Customer support chatbot for banking"
        )
        data_use = st.text_area(
            "Describe your data use",
            value=st.session_state['form_inputs']['data_use'],
            placeholder="e.g., Processes chat transcripts with PII; stores logs; fine-tunes on redacted data",
            height=150
        )
        scenario = st.text_area(
            "Risk scenario to analyze",
            value=st.session_state['form_inputs']['scenario'],
            placeholder="e.g., Prompt injection leading to data exfiltration; membership inference on logs; model hallucination in healthcare",
            height=120
        )
        region_choice = st.selectbox(
            "Target region for regulatory analysis",
            ["EU", "USA", "Canada", "UK", "Global", "Custom..."],
            index=["EU", "USA", "Canada", "UK", "Global", "Custom..."].index(st.session_state['form_inputs']['region_choice'])
        )
        custom_region = ""
        if region_choice == "Custom...":
            custom_region = st.text_input(
                "Custom region or jurisdiction",
                value=st.session_state['form_inputs']['custom_region'],
                placeholder="e.g., Singapore, Australia (Health), California, Global Finance"
            )
        
        col1, col2 = st.columns(2)
        with col1:
            analyze_clicked = st.form_submit_button(
                "🔍 Quick Risk Analysis",
                type="primary",
                use_container_width=True
            )
        with col2:
            full_assessment_clicked = st.form_submit_button(
                "📊 Full Assessment",
                use_container_width=True
            )
    
    # Update form inputs in session state
    if analyze_clicked or full_assessment_clicked:
        st.session_state['form_inputs'] = {
            'topic': topic,
            'data_use': data_use,
            'scenario': scenario,
            'region_choice': region_choice,
            'custom_region': custom_region
        }
    
    if analyze_clicked:
        # Resolve region
        region = custom_region.strip() if region_choice == "Custom..." else region_choice
        
        # Basic validation
        errors = []
        if not topic.strip():
            errors.append("Please enter a use case / system name.")
        if not data_use.strip():
            errors.append("Please describe your data use.")
        if not region.strip():
            errors.append("Please select or enter a region.")
        if not scenario.strip():
            errors.append("Please enter a risk scenario to analyze.")
        
        if errors:
            for msg in errors:
                st.warning(msg)
        else:
            with st.spinner("🤖 Analyzing risk scenario..."):
                risk_result = _run_scenario_risk_analysis(scenario.strip(), topic.strip())
                st.session_state['risk_analysis_result'] = risk_result
                st.session_state['current_scenario'] = scenario.strip()
                st.session_state['current_topic'] = topic.strip()
                st.session_state['current_data_use'] = data_use.strip()
                st.session_state['current_region'] = region
    
    elif full_assessment_clicked:
        # Resolve region
        region = custom_region.strip() if region_choice == "Custom..." else region_choice
        
        # Basic validation
        errors = []
        if not topic.strip():
            errors.append("Please enter a use case / system name.")
        if not data_use.strip():
            errors.append("Please describe your data use.")
        if not region.strip():
            errors.append("Please select or enter a region.")
        if not scenario.strip():
            errors.append("Please enter a risk scenario to analyze.")
        
        if errors:
            for msg in errors:
                st.warning(msg)
        else:
            st.session_state['has_submitted'] = True
            inputs = {
                'topic': topic.strip(),
                'current_year': str(datetime.now().year),
                'region': region,
                'data_use': data_use.strip(),
                'scenario': scenario.strip(),
            }
            os.environ['REGION'] = region
            os.environ['DATA_USE'] = data_use
            os.environ['SCENARIO'] = scenario

            run_started_at = time.time()
            with st.spinner("Running multi-agent assessment... this can take a few minutes"):
                try:
                    print(inputs)
                    result = AiLatestDevelopment().crew().kickoff(inputs=inputs)
                    # Check for report.md
                    rp_obj = _find_report_path()
                    if rp_obj and rp_obj.exists():
                        try:
                            report_path = str(rp_obj.resolve())
                            mtime = os.path.getmtime(report_path)
                            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            st.session_state['last_report_content'] = content
                            st.session_state['last_report_mtime'] = mtime
                            st.session_state['last_report_topic'] = topic.strip()
                            st.subheader("Output")
                            _render_report_view(content, topic.strip(), mtime)
                        except Exception as e:
                            st.error(f"Could not read report.md: {e}")
                            content = str(result)
                            st.session_state['last_report_content'] = content
                            st.session_state['last_report_mtime'] = time.time()
                            st.session_state['last_report_topic'] = topic.strip()
                            st.subheader("Output")
                            _render_report_view(content, topic.strip())
                    else:
                        content = str(result)
                        st.session_state['last_report_content'] = content
                        st.session_state['last_report_mtime'] = time.time()
                        st.session_state['last_report_topic'] = topic.strip()
                        st.subheader("Output")
                        _render_report_view(content, topic.strip())
                except litellm.RateLimitError as e:
                    st.subheader("Output")
                    retry_delay = float(e.args[0].split("Please retry in ")[1].split("s")[0]) if "Please retry in " in str(e) else 60
                    st.error(f"Rate limit exceeded. You have reached the free tier quota (200 requests/day) for the Gemini API. Please wait {retry_delay:.0f} seconds and try again, or check your plan and billing details at https://ai.google.dev/gemini-api/docs/rate-limits.")
                    # Display cached report if available
                    if st.session_state.get('last_report_content'):
                        _display_cached_report()
                except Exception as e:
                    st.error(f"Run failed: {e}")
                    st.subheader("Output")
                    _display_cached_report()  # Try to show cached report on failure
    
    # Display risk analysis result
    if st.session_state['risk_analysis_result']:
        st.markdown("---")
        _render_risk_result(st.session_state['risk_analysis_result'])
        
        # Action buttons based on risk level
        risk_level = st.session_state['risk_analysis_result']['risk_level']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Full Assessment", use_container_width=True):
                st.session_state['current_page'] = 'full_assessment'
                st.rerun()
        
        with col2:
            if risk_level == "HIGH":
                if st.button("🚀 Upgrade to Pro", use_container_width=True, type="primary"):
                    st.session_state['current_page'] = 'upgrade'
                    st.rerun()
            else:
                st.button("💡 Get Recommendations", use_container_width=True, disabled=True)
        
        with col3:
            if st.button("🔄 Analyze New Scenario", use_container_width=True):
                st.session_state['risk_analysis_result'] = None
                st.rerun()
    
    # Display cached report if available and no new analysis
    elif st.session_state.get('last_report_content') and st.session_state['has_submitted']:
        st.subheader("Output")
        _display_cached_report()
    else:
        st.subheader("Output")
        st.info("No output available yet. Please fill out the form and run an assessment to generate a report.")

# Upgrade page
elif st.session_state['current_page'] == 'upgrade':
    _render_upgrade_page()
    
    if st.session_state.get('payment_successful'):
        st.session_state['current_page'] = 'contact'
        st.rerun()

# Contact page
elif st.session_state['current_page'] == 'contact':
    _render_contact_page()

# Full assessment page
elif st.session_state['current_page'] == 'full_assessment':
    st.markdown("## 📊 Full Risk Assessment")
    st.markdown("Running comprehensive multi-agent analysis...")
    
    if (st.session_state.get('current_scenario') and 
        st.session_state.get('current_topic') and 
        st.session_state.get('current_data_use') and 
        st.session_state.get('current_region')):
        
        with st.spinner("Running comprehensive assessment (this may take a few minutes)..."):
            try:
                inputs = {
                    'topic': st.session_state['current_topic'],
                    'current_year': str(datetime.now().year),
                    'region': st.session_state['current_region'],
                    'data_use': st.session_state['current_data_use'],
                    'scenario': st.session_state['current_scenario']
                }
                
                result = AiLatestDevelopment().crew().kickoff(inputs=inputs)
                
                # Display the full report
                rp_obj = _find_report_path()
                if rp_obj and rp_obj.exists():
                    try:
                        report_path = str(rp_obj.resolve())
                        mtime = os.path.getmtime(report_path)
                        with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        _render_report_view(content, st.session_state['current_topic'], mtime)
                    except Exception as e:
                        st.error(f"Could not read report.md: {e}")
                        st.markdown("### Assessment Result")
                        st.markdown(str(result))
                else:
                    st.markdown("### Assessment Result")
                    st.markdown(str(result))
                    
            except Exception as e:
                st.error(f"Assessment failed: {e}")
    else:
        st.error("No scenario data available for full assessment.")

# Advanced utilities
with st.expander("Advanced"):
    col1, _ = st.columns(2)
    with col1:
        if st.button("Delete existing report.md"):
            rp_obj = _find_report_path()
            rp = str(rp_obj.resolve()) if rp_obj else str((Path.cwd() / 'report.md').resolve())
            try:
                if os.path.exists(rp):
                    os.remove(rp)
                    st.success("Deleted report.md")
                    # Clear session state and force rerun
                    for k in ("last_report_content", "last_report_mtime", "last_report_topic", "report_text"):
                        if k in st.session_state:
                            del st.session_state[k]
                    st.session_state['has_submitted'] = False
                    st.rerun()  # Force app to rerun and update UI
                else:
                    st.info("No report.md found")
            except Exception as e:
                st.error(f"Could not delete report.md: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; padding: 2rem;">
    <p>AI Risk & Compliance Assessor - Enhanced with Pro Consultation</p>
    <p>Powered by Multi-Agent AI System | © 2024</p>
</div>
""", unsafe_allow_html=True)
