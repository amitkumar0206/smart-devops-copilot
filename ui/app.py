import streamlit as st
import requests
import os

st.set_page_config(page_title="Smart DevOps Copilot", layout="centered")

st.title("🧠 Smart DevOps Copilot — Hackathon Demo")
st.caption("Paste a CloudWatch/log snippet → detect issue → recommend fix → generate Terraform/CLI.")

backend_url = os.environ.get("COPILOT_BACKEND_URL", "http://localhost:8000")

with st.form("analyze_form"):
    text = st.text_area("Paste a log/error snippet", height=200, placeholder="Paste CloudWatch log lines here...")
    uploaded = st.file_uploader("...or upload a small .txt log", type=["txt", "log"])
    submitted = st.form_submit_button("Analyze")
    if submitted:
        if uploaded is not None:
            files = {"file": uploaded.getvalue()}
            resp = requests.post(f"{backend_url}/analyze_file", files={"file": ("log.txt", uploaded.getvalue())}, timeout=20)
        else:
            resp = requests.post(f"{backend_url}/analyze", json={"text": text}, timeout=20)
        if resp.ok:
            data = resp.json()
            st.subheader("Detected Issue")
            st.json(data.get("signal", {}))
            st.subheader("Recommendations (ranked)")
            for i, r in enumerate(data.get("recommendations", []), 1):
                with st.expander(f"{i}. {r.get('title')}"):
                    st.write("**Why**")
                    for w in r.get("why", []):
                        st.write(f"- {w}")
                    st.code(r.get("action", "N/A"), language="text")
            st.subheader("Generated Code")
            tabs = st.tabs(["Terraform", "AWS CLI"])
            with tabs[0]:
                st.code(data.get("code", {}).get("terraform", "# No Terraform"), language="hcl")
            with tabs[1]:
                st.code(data.get("code", {}).get("cli", "# No CLI"), language="bash")
        else:
            st.error(f"Backend error: {resp.status_code}")
st.info("Tip: Try files from the `fixtures/` folder in the repo.")
