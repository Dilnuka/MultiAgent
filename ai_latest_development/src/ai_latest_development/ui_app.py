import os
import litellm
from pathlib import Path
from datetime import datetime
import time
from io import BytesIO
import streamlit as st

# --- Environment and Dependencies Setup ---
# Load .env early
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(env_path)
except Exception:
    pass

try:
    from .crew import AiLatestDevelopment
except ImportError:
    from crew import AiLatestDevelopment

# Optional PDF support via reportlab
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --- Core Backend Functions (Unchanged) ---
# Note: All your backend logic for PDF generation and file handling remains the same.
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
            heading_style = 'Heading' + str(min(level, 6))
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
    """Try to locate report.md in common locations."""
    candidates = [Path.cwd() / 'report.md']
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

# --- UI Helper Functions ---
def apply_modern_styles():
    """Injects custom CSS for a modern, dark-themed UI."""
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body {
            font-family: 'Inter', sans-serif;
        }
        
        /* Main app styling */
        .stApp {
            background-color: #1a1a2e;
            color: #e0e0e0;
        }
        
        /* Sidebar styling */
        .st-emotion-cache-16txtl3 {
            background-color: #162447;
            border-right: 1px solid #2c3e50;
        }
        
        /* Card-like containers for output */
        .report-container {
            background-color: #1f4068;
            padding: 2rem;
            border-radius: 10px;
            border: 1px solid #2c3e50;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        /* Button styling */
        .stButton>button {
            border-radius: 8px;
            background-color: #1b98e0;
            color: white;
            border: none;
            font-weight: 600;
        }
        .stButton>button:hover {
            background-color: #157ab3;
            color: white;
            border: none;
        }
        
        /* Expander styling */
        .stExpander {
            background-color: #162447;
            border-radius: 8px;
        }
        
        /* Headings */
        h1, h2, h3 {
            color: #e43f5a;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def _render_report_view(text: str, topic_for_filename: str, mtime: float | None = None):
    """Render the report in a styled container."""
    with st.container(border=False):
        word_count = len(text.split()) if text else 0
        if mtime:
            ts = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            st.info(f"📊 Report generated with {word_count} words (last modified: {ts})")
        else:
            st.info(f"📊 Report generated with {word_count} words")
        
        st.markdown(f"### 📋 Report: {topic_for_filename}")
        st.markdown("---")
        st.markdown(text)
        
        if REPORTLAB_AVAILABLE:
            try:
                pdf_bytes = _md_to_pdf_bytes(text)
                st.download_button(
                    label="📄 Download as PDF",
                    data=pdf_bytes,
                    file_name=f"ai_risk_report_{topic_for_filename.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key=f"download_{int(time.time())}",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")
        else:
            st.warning("PDF download requires 'reportlab'. Install it with: `pip install reportlab`")

def _display_cached_report():
    """Display cached report from session state or disk."""
    if 'last_report_content' in st.session_state:
        cached_content = st.session_state['last_report_content']
        cached_mtime = st.session_state.get('last_report_mtime')
        cached_topic = st.session_state.get('last_report_topic', 'ai_risk_report')
        _render_report_view(cached_content, cached_topic, cached_mtime)
        return True
    
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
            st.session_state['last_report_topic'] = 'ai_risk_report' # Default topic for file-based report
            _render_report_view(content, 'ai_risk_report', mtime)
            return True
        except Exception as e:
            st.error(f"Could not read report.md: {e}")
    return False

# --- Streamlit App UI ---
st.set_page_config(page_title="AI Risk Assessor", layout="wide", page_icon="🤖")
apply_modern_styles()

# Initialize session state
if 'form_inputs' not in st.session_state:
    st.session_state['form_inputs'] = {'topic': '', 'data_use': '', 'scenario': '', 'region_choice': 'EU', 'custom_region': ''}
if 'has_submitted' not in st.session_state:
    st.session_state['has_submitted'] = False

# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("📝 Assessment Inputs")
    st.caption("Enter your scenario details below to generate a risk and compliance report.")

    with st.form("inputs_form"):
        topic = st.text_input(
            "Use Case / System Name",
            value=st.session_state['form_inputs']['topic'],
            placeholder="e.g., Customer support chatbot"
        )
        data_use = st.text_area(
            "Describe Data Use",
            value=st.session_state['form_inputs']['data_use'],
            placeholder="e.g., Processes chat transcripts with PII...",
            height=120
        )
        scenario = st.text_area(
            "Risk Scenario to Analyze",
            value=st.session_state['form_inputs']['scenario'],
            placeholder="e.g., Prompt injection, data exfiltration...",
            height=100
        )
        region_choice = st.selectbox(
            "Target Region",
            ["EU", "USA", "Canada", "UK", "Global", "Custom..."],
            index=["EU", "USA", "Canada", "UK", "Global", "Custom..."].index(st.session_state['form_inputs']['region_choice'])
        )
        custom_region = ""
        if region_choice == "Custom...":
            custom_region = st.text_input(
                "Custom Jurisdiction",
                value=st.session_state['form_inputs']['custom_region'],
                placeholder="e.g., Singapore, California"
            )
        
        submitted = st.form_submit_button("🚀 Run Assessment", use_container_width=True, type="primary")

# --- Main Content Area ---
st.title("🤖 AI Risk & Compliance Assessor")

# Main container for output
output_container = st.container()
output_container.markdown('<div class="report-container">', unsafe_allow_html=True)

if submitted:
    st.session_state['form_inputs'].update({
        'topic': topic, 'data_use': data_use, 'scenario': scenario,
        'region_choice': region_choice, 'custom_region': custom_region
    })
    
    region = custom_region.strip() if region_choice == "Custom..." else region_choice
    errors = [msg for field, msg in [
        (topic, "Please enter a use case / system name."),
        (data_use, "Please describe your data use."),
        (region, "Please select or enter a region."),
        (scenario, "Please enter a risk scenario to analyze.")
    ] if not field.strip()]
    
    if errors:
        with output_container:
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
        os.environ.update({'REGION': region, 'DATA_USE': data_use, 'SCENARIO': scenario})
        
        run_started_at = time.time()
        with st.spinner("🔍 Running multi-agent assessment... this can take a few minutes."):
            try:
                result = AiLatestDevelopment().crew().kickoff(inputs=inputs)
                rp_obj = _find_report_path()
                content = ""
                mtime = time.time()
                
                if rp_obj and rp_obj.exists():
                    report_path = str(rp_obj.resolve())
                    mtime = os.path.getmtime(report_path)
                    with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                else:
                    content = str(result)
                
                st.session_state.update({
                    'last_report_content': content,
                    'last_report_mtime': mtime,
                    'last_report_topic': topic.strip()
                })
                
                with output_container:
                    _render_report_view(content, topic.strip(), mtime)

            except litellm.RateLimitError as e:
                with output_container:
                    retry_delay = float(e.args[0].split("Please retry in ")[1].split("s")[0]) if "Please retry in " in str(e) else 60
                    st.error(f"Rate limit exceeded. Please wait {retry_delay:.0f} seconds and try again.")
                    _display_cached_report()
            except Exception as e:
                with output_container:
                    st.error(f"An unexpected error occurred: {e}")
                    _display_cached_report()
else:
    with output_container:
        if st.session_state.get('last_report_content') and st.session_state['has_submitted']:
            _display_cached_report()
        else:
            st.info("👋 Welcome! Please fill out the form on the left and run an assessment to generate a report.")

output_container.markdown('</div>', unsafe_allow_html=True)

# Advanced utilities in an expander
with st.sidebar.expander("🛠️ Advanced Options"):
    if st.button("Delete Cached Report", use_container_width=True):
        rp_obj = _find_report_path()
        if rp_obj and rp_obj.exists():
            try:
                os.remove(str(rp_obj.resolve()))
                st.success("Deleted report.md file.")
            except Exception as e:
                st.error(f"Could not delete report.md: {e}")
        else:
            st.info("No report.md file found to delete.")
        
        # Clear session state
        for k in list(st.session_state.keys()):
            if k.startswith('last_report') or k == 'has_submitted':
                del st.session_state[k]
        
        st.rerun()