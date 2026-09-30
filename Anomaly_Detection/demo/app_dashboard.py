"""
Streamlit Web Dashboard: AI-Based Fake Identity & Document Screening System.
Built for Ministry of Home Affairs (MHA) & Sashastra Seema Bal (SSB) Border Control.
Implements interactive checkpoint screening across Modules 1-4 with ELA heatmaps and live face verification.
"""

import base64
import io
import json
import sys
from pathlib import Path
from PIL import Image

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import numpy as np

from document_engine.config import BORDER_WATCHLIST
from document_engine.mrz_validator import generate_mrz_lines
from document_engine.sample_generator import (
    generate_face_mismatch_sample,
    generate_genuine_sample,
    generate_photo_replacement_sample,
    generate_stamp_forgery_sample,
    generate_tampered_expiry_sample,
    generate_watchlist_hit_sample,
)
from document_engine.schema import DocumentScreeningResult, PassportData, VisaData
from document_engine.screener import DocumentScreener

# Page configuration
st.set_page_config(
    page_title="SSB Border Document Screening Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Tech Border Security CSS
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-clear { background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
    .badge-warning { background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
    .badge-danger { background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
col_logo, col_header = st.columns([1, 7])
with col_logo:
    st.markdown("<h1 style='font-size: 4rem; text-align: center; margin: 0;'>🛡️</h1>", unsafe_allow_html=True)
with col_header:
    st.markdown("<div class='main-title'>AI-BASED FAKE IDENTITY & DOCUMENT SCREENING SYSTEM</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-title'>Ministry of Home Affairs (MHA) • Sashastra Seema Bal (SSB) Police II Division • Problem ID #26188</div>",
        unsafe_allow_html=True,
    )

# Sidebar System Health & Readiness
with st.sidebar:
    st.subheader("System Status")
    st.success("🟢 Module 1: OCR Preprocessor & MRZ [ACTIVE]")
    st.success("🟢 Module 2: ICAO 9303 & Watchlist [ACTIVE]")
    st.success("🟢 Module 3: ELA & Tamper Forensics [ACTIVE]")
    st.success("🟢 Module 4: 1:1 Face & Anti-Spoofing [ACTIVE]")
    st.divider()
    st.caption("Border Checkpoint: ICP Raxaul / SSB Sector HQ")
    st.caption("Engine: Antigravity Multi-Factor Forensic Screener")


@st.cache_resource
def get_screener():
    return DocumentScreener()


screener = get_screener()

tabs = st.tabs([
    "🛃 Live Checkpoint Screener",
    "🔬 Forensic ELA & Tamper Inspector",
    "⚡ 1-Click Simulated Scenarios",
    "🚨 Watchlist & Audit Log",
])


# Helper function to display screening report card
def render_screening_report(res: DocumentScreeningResult):
    st.divider()
    # Big Decision Banner
    if "REJECT" in res.decision:
        st.error(f"### 🛑 CRITICAL ALERT: {res.decision}")
    elif "SECONDARY" in res.decision:
        st.warning(f"### ⚠️ WARNING: {res.decision}")
    else:
        st.success(f"### ✅ VERIFIED: {res.decision}")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Fraud Probability", f"{res.anomaly_score * 100:.1f}%", delta=None)
    with m2:
        st.metric("Risk Severity", res.severity)
    with m3:
        st.metric("AI Confidence", f"{res.confidence * 100:.1f}%")
    with m4:
        st.metric("Audit Record", res.audit_id)

    # 4-Module Evidence Grid
    st.markdown("#### 🔍 Multi-Layer Forensic Evidence Breakdown")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Module 1 & 2: Document Integrity & Checksums**")
        if res.validation_failed:
            st.error("❌ ICAO 9303 Checksum / Rule Validation: FAILED")
        else:
            st.success("✅ ICAO 9303 Checksum & Temporal Validity: PASSED")

        if res.watchlist_hit:
            st.error(f"🚨 **WATCHLIST HIT**: {res.watchlist_hit.category} ({res.watchlist_hit.reason})")

        st.markdown("**Module 3: Image Tampering & Pixel Forensics**")
        if res.tampering_detected:
            st.error("❌ Image Tampering / Splicing / ELA Disparity: DETECTED")
        else:
            st.success("✅ Image Compression & Pixel Uniformity: VERIFIED")

    with c2:
        st.markdown("**Module 4: Biometric Face Verification**")
        if res.face_verification:
            fv = res.face_verification
            st.write(f"• 1:1 Match Similarity: **{fv.similarity_score * 100:.1f}%**")
            if fv.is_match:
                st.success("✅ Face Biometric Match: CONFIRMED")
            elif fv.is_impersonation:
                st.error("❌ Face Biometric Match: IMPERSONATION DETECTED")
            else:
                st.warning("⚠️ Borderline Biometric Match")

            if fv.liveness_passed:
                st.success("✅ Liveness / Anti-Spoofing: 3D Live Human Skin Verified")
            else:
                st.error(f"❌ Presentation Attack Detected: {fv.anti_spoof_detail}")
        else:
            st.info("ℹ️ Live camera face was not provided for this scan.")

    # Forensic Evidence Items
    if res.evidence:
        st.markdown("##### Detailed Forensic Findings:")
        for item in res.evidence:
            badge_color = "red" if item.severity == "CRITICAL" else ("orange" if item.severity == "HIGH" else "blue")
            st.markdown(
                f"- **[{item.layer}]** :{badge_color}[{item.anomaly}] ({item.severity}): {item.detail}"
            )

    # Officer Prescriptive Action Box
    st.info(f"**👮 IMMIGRATION OFFICER INSTRUCTION:**\n\n{res.recommended_action}")


# ==========================================
# TAB 1: LIVE CHECKPOINT SCREENER
# ==========================================
with tabs[0]:
    st.markdown("### Primary Passenger Document & Face Screening")
    st.write("Upload passenger travel document and live checkpoint webcam capture for instant AI verification.")

    col_doc_input, col_face_input = st.columns(2)

    with col_doc_input:
        st.markdown("#### 1. Travel Document (Passport / Visa / ID)")
        doc_file = st.file_uploader("Upload Document Scan (JPG / PNG)", type=["jpg", "jpeg", "png"], key="doc_upload")
        doc_type = st.selectbox("Document Category", ["PASSPORT", "VISA", "NATIONAL_ID"], key="doc_type_select")

    with col_face_input:
        st.markdown("#### 2. Live Passenger Camera Feed")
        face_file = st.file_uploader("Upload Live Camera Capture / Selfie", type=["jpg", "jpeg", "png"], key="face_upload")

    col_act, _ = st.columns([1, 4])
    with col_act:
        scan_button = st.button("🚀 SCREEN TRAVELER NOW", type="primary", use_container_width=True)

    if scan_button:
        if doc_file is not None:
            doc_img = Image.open(doc_file).convert("RGB")
            live_img = Image.open(face_file).convert("RGB") if face_file else None

            with st.spinner("Processing multi-layer AI inspection..."):
                res = screener.screen(
                    image_input=doc_img,
                    live_face_input=live_img,
                    document_type=doc_type,
                )
                render_screening_report(res)

                if res.ela_heatmap_base64:
                    st.markdown("#### 🔬 Generated Error Level Analysis (ELA) Heatmap")
                    heatmap_bytes = base64.b64decode(res.ela_heatmap_base64)
                    heatmap_img = Image.open(io.BytesIO(heatmap_bytes))
                    hc1, hc2 = st.columns(2)
                    with hc1:
                        st.image(doc_img, caption="Original Document Image", use_container_width=True)
                    with hc2:
                        st.image(heatmap_img, caption="Forensic ELA Heatmap (Tampered Regions Highlighted)", use_container_width=True)
        else:
            st.error("Please upload at least a document image or select a scenario from Tab 3.")


# ==========================================
# TAB 2: FORENSIC ELA & TAMPER INSPECTOR
# ==========================================
with tabs[1]:
    st.markdown("### Deep Forensic Image Inspection & Error Level Analysis (ELA)")
    st.write("Examine pixel-level compression anomalies, sensor noise variance, and digital stamp overlays.")

    sample_choice = st.selectbox(
        "Choose an example image for forensic decomposition:",
        [
            "Scenario 3: Marcus Vance (Spliced Photo Replacement)",
            "Scenario 2: Tariq Al-Mansoor (Tampered Expiry Date)",
            "Scenario 5: Elena Rostova (Synthetic Visa Stamp)",
            "Scenario 1: Dr. Ananya Sharma (Genuine Baseline)",
        ],
    )

    if "Marcus Vance" in sample_choice:
        test_img, p, _, meta, _ = generate_photo_replacement_sample()
    elif "Tariq" in sample_choice:
        test_img, p, _, _ = generate_tampered_expiry_sample()
        meta = None
    elif "Elena" in sample_choice:
        test_img, p, _, _ = generate_stamp_forgery_sample()
        meta = None
    else:
        test_img, p, _, _ = generate_genuine_sample()
        meta = None

    tampered, score, evidence, frauds = screener.image_analyzer.analyze_image(test_img, meta)
    b64_map = screener.image_analyzer.last_ela_heatmap_base64

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.image(test_img, caption="Document Biodata Page", use_container_width=True)
    with f_col2:
        if b64_map:
            h_img = Image.open(io.BytesIO(base64.b64decode(b64_map)))
            st.image(h_img, caption="Error Level Analysis (ELA) False-Color Heatmap", use_container_width=True)

    st.markdown(f"**Image Forensic Anomaly Score:** `{score * 100:.1f}%` | **Tampering Detected:** `{tampered}`")
    if evidence:
        st.markdown("**Identified Forensic Anomalies:**")
        for ev in evidence:
            st.markdown(f"- **{ev.anomaly}** ({ev.severity}): {ev.detail}")


# ==========================================
# TAB 3: 1-CLICK SIMULATED SCENARIOS
# ==========================================
with tabs[2]:
    st.markdown("### Simulated Real-World Border Checkpoint Cases")
    st.write("Click any scenario below to immediately run an end-to-end evaluation through all 4 modules.")

    s_col1, s_col2, s_col3 = st.columns(3)
    s_col4, s_col5, s_col6 = st.columns(3)

    selected_scenario = None

    with s_col1:
        st.markdown("#### Case 1: Genuine Passport")
        st.caption("Dr. Ananya Sharma (IND) • Valid Expiry • Matching Live Face")
        if st.button("RUN CASE 1", key="btn_case1", use_container_width=True):
            selected_scenario = "CASE_1"

    with s_col2:
        st.markdown("#### Case 2: Tampered Expiry")
        st.caption("Tariq Al-Mansoor (ARE) • Visual 2034 vs MRZ 2032 • ELA Anomaly")
        if st.button("RUN CASE 2", key="btn_case2", use_container_width=True):
            selected_scenario = "CASE_2"

    with s_col3:
        st.markdown("#### Case 3: Spliced Photo")
        st.caption("Marcus Vance (GBR) • Sensor Noise Disparity • Photoshop EXIF")
        if st.button("RUN CASE 3", key="btn_case3", use_container_width=True):
            selected_scenario = "CASE_3"

    with s_col4:
        st.markdown("#### Case 4: Face Mismatch")
        st.caption("David Miller (USA) • Genuine Passport • Imposter Face")
        if st.button("RUN CASE 4", key="btn_case4", use_container_width=True):
            selected_scenario = "CASE_4"

    with s_col5:
        st.markdown("#### Case 5: Forged Stamp")
        st.caption("Elena Rostova (RUS) • Digital Stamp Ink • 60d on 14d Visa")
        if st.button("RUN CASE 5", key="btn_case5", use_container_width=True):
            selected_scenario = "CASE_5"

    with s_col6:
        st.markdown("#### Case 6: Watchlist Hit")
        st.caption("Vikram Malhotra (IND) • Interpol Red Notice • Stolen Passport")
        if st.button("RUN CASE 6", key="btn_case6", use_container_width=True):
            selected_scenario = "CASE_6"

    # Execution of selected scenario
    if selected_scenario:
        if selected_scenario == "CASE_1":
            doc_img, p, v, live_img = generate_genuine_sample()
            meta = None
        elif selected_scenario == "CASE_2":
            doc_img, p, v, live_img = generate_tampered_expiry_sample()
            meta = None
        elif selected_scenario == "CASE_3":
            doc_img, p, v, meta, live_img = generate_photo_replacement_sample()
        elif selected_scenario == "CASE_4":
            doc_img, p, v, live_img = generate_face_mismatch_sample()
            meta = None
        elif selected_scenario == "CASE_5":
            doc_img, p, v, live_img = generate_stamp_forgery_sample()
            meta = None
        else:
            doc_img, p, v, live_img = generate_watchlist_hit_sample()
            meta = None

        with st.spinner("Executing 4-module border screening..."):
            res = screener.screen(
                image_input=doc_img,
                live_face_input=live_img,
                passport=p,
                visa=v,
                metadata=meta,
            )

            # Display visual inputs
            v1, v2 = st.columns([2, 1])
            with v1:
                st.image(doc_img, caption=f"Document Scan ({p.passport_number})", use_container_width=True)
            with v2:
                st.image(live_img, caption="Live Checkpoint Camera Feed", use_container_width=True)

            render_screening_report(res)


# ==========================================
# TAB 4: WATCHLIST & AUDIT LOG
# ==========================================
with tabs[3]:
    st.markdown("### SSB & Interpol Border Security Watchlist")
    st.write("Active Interpol Red Notices, Stolen and Lost Travel Documents (SLTD), and Border Lookout Circulars (LOC).")

    st.table(BORDER_WATCHLIST)

    st.markdown("### Export Inspection Report")
    st.write("Download an official, legally defensible border screening report for immigration records.")

    # Sample export JSON
    sample_audit = {
        "agency": "Sashastra Seema Bal (SSB) / Ministry of Home Affairs",
        "station": "Integrated Checkpoint (ICP) Raxaul",
        "system": "AI-Based Fake Identity & Document Screening System",
        "compliance": "ICAO Doc 9303 Part 3 / ISO 19794-5",
        "total_rules_evaluated": 18,
        "tampering_checks": ["Error Level Analysis", "Laplacian Sensor Noise Disparity", "EXIF Metadata Signature"],
    }
    st.download_button(
        label="📥 DOWNLOAD SSB FORENSIC AUDIT TEMPLATE (JSON)",
        data=json.dumps(sample_audit, indent=2),
        file_name="SSB_Border_Audit_Report.json",
        mime="application/json",
    )

