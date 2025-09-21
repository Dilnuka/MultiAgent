import os
import litellm  # Added to handle RateLimitError
from pathlib import Path
from datetime import datetime
import time
from io import BytesIO

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

# UI header and input form
st.set_page_config(page_title="AI Risk & Compliance Assessor", layout="wide")
st.title("AI Risk & Compliance Assessor")
st.caption("Enter your own scenario: use case, data use, and region – nothing is hard-coded.")

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
    submitted = st.form_submit_button("Run Assessment")

# Update form inputs in session state
if submitted:
    st.session_state['form_inputs'] = {
        'topic': topic,
        'data_use': data_use,
        'scenario': scenario,
        'region_choice': region_choice,
        'custom_region': custom_region
    }

# Form submission
if submitted:
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
        st.subheader("Output")
        for msg in errors:
            st.warning(msg)
        # Still display cached report if it exists
        if st.session_state['has_submitted']:
            _display_cached_report()
    else:
        st.session_state['has_submitted'] = True  # Mark as submitted
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
else:
    # No submission; try to display cached report only if previously submitted and content exists
    if st.session_state.get('last_report_content') and st.session_state['has_submitted']:
        st.subheader("Output")
        _display_cached_report()
    else:
        st.subheader("Output")
        st.info("No output available yet. Please fill out the form and run an assessment to generate a report.")

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