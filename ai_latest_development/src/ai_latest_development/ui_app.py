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

# Custom CSS for elegant styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        border: none;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .stTextInput>div>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 1px solid #ddd;
        padding: 10px;
    }
    .stExpander {
        border-radius: 8px;
        border: 1px solid #ddd;
    }
    .report-container {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="AI Risk & Compliance Assessor", layout="wide", page_icon="🤖")

# Sidebar for inputs
with st.sidebar:
    st.markdown("## 🔧 Assessment Inputs")
    st.markdown("Configure your AI system details below.")

    topic = st.text_input(
        "📋 Use case / System name",
        value="",
        placeholder="e.g., Customer support chatbot for banking"
    )
    data_use = st.text_area(
        "📊 Describe your data use",
        value="",
        placeholder="e.g., Processes chat transcripts with PII; stores logs; fine-tunes on redacted data",
        height=150
    )
    scenario = st.text_area(
        "⚠️ Risk scenario to analyze",
        value="",
        placeholder="e.g., Prompt injection leading to data exfiltration; membership inference on logs; model hallucination in healthcare",
        height=120
    )
    region_choice = st.selectbox(
        "🌍 Target region for regulatory analysis",
        ["EU", "USA", "Canada", "UK", "Global", "Custom..."]
    )
    custom_region = ""
    if region_choice == "Custom...":
        custom_region = st.text_input(
            "🏛️ Custom region or jurisdiction",
            value="",
            placeholder="e.g., Singapore, Australia (Health), California, Global Finance"
        )

    submitted = st.button("🚀 Run Assessment", type="primary")

# Main content area
st.markdown('<div class="main-header">🤖 AI Risk & Compliance Assessor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Enter your own scenario: use case, data use, and region – nothing is hard-coded.</div>', unsafe_allow_html=True)

# Tabs for organization
tab1, tab2, tab3 = st.tabs(["📊 Assessment", "📋 Results", "⚙️ Advanced"])

with tab1:
    st.markdown("### 📈 Assessment Overview")
    st.info("Configure inputs in the sidebar and click 'Run Assessment' to start.")

with tab2:
    if submitted:
        # Resolve region
        region = custom_region.strip() if region_choice == "Custom..." else region_choice

        # Basic validation
        errors = []
        if not topic.strip():
            errors.append("❌ Please enter a use case / system name.")
        if not data_use.strip():
            errors.append("❌ Please describe your data use.")
        if not region.strip():
            errors.append("❌ Please select or enter a region.")
        if not scenario.strip():
            errors.append("❌ Please enter a risk scenario to analyze.")

        if errors:
            for msg in errors:
                st.error(msg)
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
            progress_bar = st.progress(0)
            status_text = st.empty()

            with st.spinner("🔄 Running multi-agent assessment... this can take a few minutes"):
                try:
                    status_text.text("Initializing agents...")
                    progress_bar.progress(25)
                    time.sleep(1)  # Simulate progress
                    status_text.text("Analyzing risks...")
                    progress_bar.progress(50)
                    time.sleep(1)
                    status_text.text("Generating report...")
                    progress_bar.progress(75)
                    result = AiLatestDevelopment().crew().kickoff(inputs=inputs)
                    progress_bar.progress(100)
                    status_text.text("Assessment complete!")
                    time.sleep(1)
                    progress_bar.empty()
                    status_text.empty()
                except Exception as e:
                    st.error(f"❌ Run failed: {e}")
                    result = None
                    progress_bar.empty()
                    status_text.empty()

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
                            st.success(f"✅ Report generated: {word_count} words")

                            # Display the formatted report
                            st.markdown('<div class="report-container">', unsafe_allow_html=True)
                            st.markdown("### 📋 Generated Report")
                            st.markdown(content)
                            st.markdown('</div>', unsafe_allow_html=True)

                            # Download button
                            st.download_button(
                                label="📥 Download Report (Markdown)",
                                data=content,
                                file_name=f"ai_risk_report_{topic.strip().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                                mime="text/markdown"
                            )
                    else:
                        st.markdown('<div class="report-container">', unsafe_allow_html=True)
                        st.markdown("### 📋 Direct Output")
                        st.write(result)
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="report-container">', unsafe_allow_html=True)
                    st.markdown("### 📋 Direct Output")
                    st.write(result)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("ℹ️ No output produced. Check logs and configuration.")
    else:
        st.info("👈 Configure inputs in the sidebar and run the assessment to see results here.")

with tab3:
    st.markdown("### ⚙️ Advanced Utilities")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Delete existing report.md"):
            rp = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'report.md'))
            try:
                if os.path.exists(rp):
                    os.remove(rp)
                    st.success("✅ Deleted report.md")
                else:
                    st.info("ℹ️ No report.md found")
            except Exception as e:
                st.error(f"❌ Could not delete report.md: {e}")
    with col2:
        st.markdown("**Additional tools coming soon...**")

