import streamlit as st

st.set_page_config(page_title="Consultation Packages", layout="wide")

st.title("Consultation Packages")
st.caption("Expert guidance to address high-risk findings and achieve compliance.")

col1, col2 = st.columns(2)

with col1:
        st.markdown(
                """
                <div style="background:#fff;border:1px solid rgba(0,0,0,.06);border-radius:14px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.06)">
                    <h3 style="margin:0 0 8px 0">Basic</h3>
                    <p style="color:#6b7280;margin:0 0 10px 0">Quick start for small teams</p>
                    <ul>
                        <li>1-hour consultation with an AI Ethics Specialist</li>
                        <li>High-level review of your use case and risks</li>
                        <li>Actionable recommendations and next steps</li>
                    </ul>
                    <button style="background:#2563eb;color:#fff;border:none;padding:10px 14px;border-radius:10px;font-weight:700;cursor:pointer">Contact us</button>
                </div>
                """,
                unsafe_allow_html=True,
        )

with col2:
        st.markdown(
                """
                <div style="background:#fff;border:1px solid rgba(0,0,0,.06);border-radius:14px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.06)">
                    <h3 style="margin:0 0 8px 0">Premium</h3>
                    <p style="color:#6b7280;margin:0 0 10px 0">Deep-dive support for complex systems</p>
                    <ul>
                        <li>3 × 1-hour sessions with the specialist</li>
                        <li>Detailed compliance roadmap and risk mitigation plan</li>
                        <li>Policy templates and governance checklist</li>
                    </ul>
                    <button style="background:#111827;color:#fff;border:none;padding:10px 14px;border-radius:10px;font-weight:700;cursor:pointer">Book a discovery call</button>
                </div>
                """,
                unsafe_allow_html=True,
        )

st.divider()

if st.button("Go back"):
        st.experimental_set_query_params()
        st.rerun()
