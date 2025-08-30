import os
from pathlib import Path
from datetime import datetime
import time

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


st.set_page_config(page_title="AI Risk & Compliance Assessor", layout="wide")
st.title("AI Risk & Compliance Assessor")
st.caption("Enter your own scenario: use case, data use, and region – nothing is hard-coded.")

with st.form("inputs"):
    topic = st.text_input(
        "Use case / System name",
        value="",
        placeholder="e.g., Customer support chatbot for banking"
    )
    data_use = st.text_area(
        "Describe your data use",
        value="",
        placeholder="e.g., Processes chat transcripts with PII; stores logs; fine-tunes on redacted data",
        height=150
    )
    scenario = st.text_area(
        "Risk scenario to analyze",
        value="",
        placeholder="e.g., Prompt injection leading to data exfiltration; membership inference on logs; model hallucination in healthcare",
        height=120
    )
    region_choice = st.selectbox(
        "Target region for regulatory analysis",
        ["EU", "USA", "Canada", "UK", "Global", "Custom..."]
    )
    custom_region = ""
    if region_choice == "Custom...":
        custom_region = st.text_input(
            "Custom region or jurisdiction",
            value="",
            placeholder="e.g., Singapore, Australia (Health), California, Global Finance"
        )
    submitted = st.form_submit_button("Run Assessment")

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
        for msg in errors:
            st.warning(msg)
    else:
        inputs = {
            'topic': topic.strip(),
            'current_year': str(datetime.now().year),
            'region': region,
            'data_use': data_use.strip(),
            'scenario': scenario.strip(),
        }
        # Persist for non-UI runs if needed
        os.environ['REGION'] = region
        os.environ['DATA_USE'] = data_use
        os.environ['SCENARIO'] = scenario

        run_started_at = time.time()
        with st.spinner("Running multi-agent assessment... this can take a few minutes"):
            try:
                result = AiLatestDevelopment().crew().kickoff(inputs=inputs)
            except Exception as e:
                st.error(f"Run failed: {e}")
                result = None

    st.subheader("Output")
    if result is not None:
        # Prefer fresh report.md only if it was updated in this run
        report_path = os.path.join(os.path.dirname(__file__), '..', '..', 'report.md')
        report_path = os.path.normpath(report_path)
        if os.path.exists(report_path):
            try:
                mtime = os.path.getmtime(report_path)
            except Exception:
                mtime = 0
            if mtime >= run_started_at - 1:
                with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Display word count
                    word_count = len(content.split())
                    st.info(f"📊 Report generated: {word_count} words")
                    
                    # Display the formatted report
                    st.markdown("### 📋 Generated Report")
                    st.markdown(content)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Report (Markdown)",
                        data=content,
                        file_name=f"ai_risk_report_{topic.strip().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
            else:
                st.write("### Direct Output")
                st.write(result)
        else:
            st.write("### Direct Output")
            st.write(result)
    else:
        st.info("No output produced. Check logs and configuration.")


# Advanced utilities
with st.expander("Advanced"):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Delete existing report.md"):
            rp = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'report.md'))
            try:
                if os.path.exists(rp):
                    os.remove(rp)
                    st.success("Deleted report.md")
                else:
                    st.info("No report.md found")
            except Exception as e:
                st.error(f"Could not delete report.md: {e}")

