"""Streamlit prototype UI for AI Auto Diag."""

import streamlit as st
import requests
import json

# ── Configuration ──────────────────────────────────────────
API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title="AI Auto Diag",
    page_icon="\U0001f527",
    layout="wide",
)

# ── Sidebar: Vehicle Info & Tools ──────────────────────────
with st.sidebar:
    st.title("\U0001f697 Vehicle Info")
    vehicle_year = st.number_input("Year", min_value=1960, max_value=2027, value=2020)
    vehicle_make = st.text_input("Make", placeholder="e.g., Ford")
    vehicle_model = st.text_input("Model", placeholder="e.g., F-150")
    vehicle_engine = st.text_input("Engine", placeholder="e.g., 5.0L V8")

    st.divider()

    st.title("\U0001f4c4 Service Manuals")
    uploaded_file = st.file_uploader("Upload PDF Manual", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Index Manual"):
            with st.spinner("Indexing PDF..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    resp = requests.post(f"{API_BASE}/documents/upload", files=files)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.success(f"Indexed {data['chunks_created']} chunks from {data['filename']}")
                    else:
                        st.error(f"Upload failed: {resp.text}")
                except requests.ConnectionError:
                    st.error("Cannot connect to API. Is the server running?")

    # Document stats
    try:
        stats_resp = requests.get(f"{API_BASE}/documents/stats", timeout=2)
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            st.info(f"Indexed chunks: {stats.get('total_chunks', 0)}")
    except Exception:
        pass

# ── Main Content ───────────────────────────────────────────
st.title("\U0001f527 AI Auto Diag")
st.caption("AI-powered automotive diagnostic assistant for professional technicians")

# Tabs for different tools
tab_chat, tab_dtc = st.tabs(["\U0001f4ac Diagnostic Chat", "\U0001f50d DTC Lookup"])

# ── Diagnostic Chat Tab ────────────────────────────────────
with tab_chat:
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Describe the symptom or enter DTC codes..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Extract any DTC codes from the message
        import re
        dtc_pattern = r'\b[PCBU][0-9]{4}\b'
        found_dtcs = re.findall(dtc_pattern, prompt.upper())

        # Build request
        request_body = {
            "query": prompt,
            "vehicle_year": vehicle_year,
            "vehicle_make": vehicle_make or None,
            "vehicle_model": vehicle_model or None,
            "vehicle_engine": vehicle_engine or None,
            "dtc_codes": found_dtcs if found_dtcs else None,
            "use_rag": True,
        }

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    resp = requests.post(f"{API_BASE}/diagnose", json=request_body, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        diagnosis = data["diagnosis"]
                        st.markdown(diagnosis)

                        # Show metadata in expandable section
                        with st.expander("Diagnostic Details"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Confidence", data.get("confidence", "N/A"))
                                if data.get("sources"):
                                    st.write("**Sources:**", ", ".join(data["sources"]))
                            with col2:
                                if data.get("possible_causes"):
                                    st.write("**Top Causes:**")
                                    for cause in data["possible_causes"][:5]:
                                        st.write(f"  - {cause}")

                        st.session_state.messages.append({"role": "assistant", "content": diagnosis})
                    else:
                        error = f"API error: {resp.text}"
                        st.error(error)
                        st.session_state.messages.append({"role": "assistant", "content": error})
                except requests.ConnectionError:
                    msg = "Cannot connect to API server. Start it with: `uvicorn app.main:app --reload`"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg})

# ── DTC Lookup Tab ─────────────────────────────────────────
with tab_dtc:
    st.subheader("DTC Code Lookup")
    dtc_input = st.text_input("Enter DTC Code", placeholder="e.g., P0300")

    if dtc_input:
        try:
            resp = requests.get(f"{API_BASE}/dtc/{dtc_input.strip()}", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data["found"] and data.get("info"):
                    info = data["info"]
                    st.success(f"**{info['code']}** — {info['description']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Category:** {info['category'].title()}")
                        st.write(f"**Severity:** {info['severity'].title()}")

                        if info.get("symptoms"):
                            st.write("**Symptoms:**")
                            for s in info["symptoms"]:
                                st.write(f"  - {s}")

                    with col2:
                        if info.get("common_causes"):
                            st.write("**Common Causes:**")
                            for c in info["common_causes"]:
                                st.write(f"  - {c}")

                    if info.get("diagnostic_steps"):
                        st.write("**Diagnostic Steps:**")
                        for i, step in enumerate(info["diagnostic_steps"], 1):
                            st.write(f"  {i}. {step}")
                elif data.get("info"):
                    info = data["info"]
                    st.warning(f"**{info['code']}** — {info['description']}")
                    if info.get("diagnostic_steps"):
                        for step in info["diagnostic_steps"]:
                            st.write(f"  - {step}")
                else:
                    st.warning(f"Code {dtc_input.upper()} not found in database")
            else:
                st.error(f"Lookup failed: {resp.text}")
        except requests.ConnectionError:
            st.error("Cannot connect to API. Is the server running?")
