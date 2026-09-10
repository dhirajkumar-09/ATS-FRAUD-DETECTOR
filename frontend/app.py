"""
frontend/app.py — Modernized Streamlit Frontend for ATS Fraud Detector
======================================================================
Digital Forensics & Recruiter Audit Station with:
  • Real-time Radar Scan & Animated Trust Score Gauge
  • Side-by-Side Clean vs Flagged Span Forensic Inspector
  • "Why This Score" AI Explainability & Recommendation Brief
  • Multi-Resume Batch Scan & Sortable Leaderboard
  • Exportable SVG Trust Badges & ATS Shortlist Cards
  • Resilient, styled error boundaries & accessible indicators
"""
import base64
import html as _html
from io import BytesIO

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="ATS Fraud Detector — Forensic Station",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
# Design system — Cyber-Forensic Evidence Room & Case File Dossier
# ═════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --ink-950: #080A0F;
    --ink-900: #0D0F14;
    --ink-850: #12141B;
    --ink-800: #171A22;
    --ink-750: #1D2029;
    --ink-700: #262A35;
    --line:    #2A2F3B;
    --line-bright: #3D4455;
    --text:      #F1F3F9;
    --text-dim:  #9BA0AF;
    --text-faint:#666B7A;
    --crimson:      #EF4444;
    --crimson-glow: rgba(239, 68, 68, 0.25);
    --amber:        #F59E0B;
    --amber-glow:   rgba(245, 158, 11, 0.25);
    --teal:         #10B981;
    --teal-glow:    rgba(16, 185, 129, 0.25);
    --cyber-blue:   #06B6D4;
}

@keyframes bgDrift {
    0%   { background-position: 0% 0%, 100% 100%; }
    50%  { background-position: 10% 5%, 90% 95%; }
    100% { background-position: 0% 0%, 100% 100%; }
}
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.4); }
    50%      { box-shadow: 0 0 22px rgba(16, 185, 129, 0.1); }
}
@keyframes radarSweep {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

html, body, .stApp {
    background:
        radial-gradient(ellipse 900px 500px at 10% -10%, rgba(16,185,129,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 700px 500px at 90% 105%, rgba(6,182,212,0.06) 0%, transparent 55%),
        radial-gradient(ellipse 1200px 600px at 50% 0%, #131722 0%, var(--ink-950) 65%) !important;
    background-size: 200% 200%, 200% 200%, 100% 100%;
    animation: bgDrift 24s ease-in-out infinite;
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Hero Header */
.case-hero {
    background: linear-gradient(135deg, rgba(23,26,34,0.85) 0%, rgba(13,15,20,0.95) 100%);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 8px 24px -8px rgba(0,0,0,0.5);
    backdrop-filter: blur(10px);
}
.case-hero h1 {
    font-size: 1.85rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #FFFFFF 0%, #D1D5DB 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.case-hero .sub {
    color: var(--text-dim);
    font-size: 0.92rem;
    margin-top: 0.35rem;
}
.case-stamp {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    padding: 0.4rem 0.85rem;
    border-radius: 6px;
    border: 1px solid var(--teal);
    background: rgba(16, 185, 129, 0.12);
    color: var(--teal);
    text-shadow: 0 0 8px rgba(16,185,129,0.5);
    box-shadow: 0 0 14px rgba(16,185,129,0.2);
}

/* Forensic Section Headers */
.section-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--cyber-blue);
    letter-spacing: 0.08em;
    margin: 1.4rem 0 0.25rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-eyebrow::after {
    content: "";
    flex-grow: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--line-bright), transparent);
}
.section-title {
    font-size: 1.35rem;
    font-weight: 600;
    margin-bottom: 0.85rem;
    color: var(--text);
}

/* Verdict & Trust Score Card */
.verdict-card {
    background: var(--ink-850);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2rem;
    box-shadow: 0 6px 20px -4px rgba(0,0,0,0.4);
    animation: fadeSlideUp 0.4s ease both;
}
.verdict-info { flex: 1; min-width: 260px; }
.verdict-title {
    font-size: 1.35rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}
.verdict-rec {
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text);
    background: var(--ink-750);
    border-left: 3px solid var(--teal);
    padding: 0.65rem 0.9rem;
    border-radius: 4px;
    margin: 0.8rem 0;
}

/* Chips & Badges */
.chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    font-weight: 600;
    border-radius: 5px;
    padding: 0.2rem 0.55rem;
    margin: 0.15rem 0.25rem 0.15rem 0;
    border: 1px solid transparent;
}
.chip.high   { background: rgba(239,68,68,0.15); color: #FCA5A5; border-color: rgba(239,68,68,0.4); }
.chip.medium { background: rgba(245,158,11,0.15); color: #FCD34D; border-color: rgba(245,158,11,0.4); }
.chip.low    { background: rgba(16,185,129,0.15); color: #6EE7B7; border-color: rgba(16,185,129,0.4); }
.chip.match  { background: rgba(6,182,212,0.15); color: #67E8F9; border-color: rgba(6,182,212,0.4); }
.chip.missing{ background: rgba(239,68,68,0.12); color: #F87171; border-color: rgba(239,68,68,0.3); }
.chip.extra  { background: var(--ink-700); color: var(--text-dim); border-color: var(--line); }

/* Evidence Data Table */
.evidence-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
    margin-top: 0.5rem;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--line);
}
.evidence-table th {
    background: var(--ink-800);
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: var(--text-dim);
    padding: 0.65rem 0.85rem;
    border-bottom: 1px solid var(--line);
    text-transform: uppercase;
}
.evidence-table td {
    background: var(--ink-850);
    padding: 0.7rem 0.85rem;
    border-bottom: 1px solid var(--ink-750);
    color: var(--text);
    vertical-align: top;
}
.evidence-table tr:hover td { background: var(--ink-750); }

/* Radar Scanner Animation */
.radar-box {
    position: relative;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    border: 2px solid var(--teal);
    background: radial-gradient(circle, rgba(16,185,129,0.15) 0%, transparent 70%);
    box-shadow: 0 0 20px rgba(16,185,129,0.25);
    margin: 1.5rem auto;
    overflow: hidden;
}
.radar-sweep {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 50px;
    height: 50px;
    background: linear-gradient(45deg, rgba(16,185,129,0.6), transparent);
    transform-origin: top left;
    animation: radarSweep 1.8s linear infinite;
}

/* Footer */
.case-footer {
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--line);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: var(--text-faint);
    display: flex;
    justify-content: space-between;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════
def esc(x) -> str:
    return _html.escape(str(x)) if x is not None else ""


def render_svg_gauge(score: float, label: str) -> str:
    score_val = max(0.0, min(100.0, float(score or 0)))
    radius = 54
    circumference = 2 * 3.14159265 * radius
    dash_offset = circumference * (1.0 - (score_val / 100.0))

    if label == "Verified":
        color = "#10B981"
        glow = "rgba(16, 185, 129, 0.45)"
    elif label == "Caution":
        color = "#F59E0B"
        glow = "rgba(245, 158, 11, 0.45)"
    else:
        color = "#EF4444"
        glow = "rgba(239, 68, 68, 0.45)"

    return f"""
    <div style="display:flex; justify-content:center; align-items:center; width:130px; height:130px; position:relative;">
        <svg width="130" height="130" viewBox="0 0 130 130">
            <circle cx="65" cy="65" r="{radius}" fill="none" stroke="#1D2029" stroke-width="11"/>
            <circle cx="65" cy="65" r="{radius}" fill="none" stroke="{color}" stroke-width="11"
                    stroke-linecap="round"
                    stroke-dasharray="{circumference}"
                    stroke-dashoffset="{dash_offset}"
                    transform="rotate(-90 65 65)"
                    style="filter: drop-shadow(0 0 8px {glow}); transition: stroke-dashoffset 1s ease;"/>
        </svg>
        <div style="position:absolute; text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:700; color:#FFFFFF;">
                {score_val:.0f}
            </div>
            <div style="font-size:0.68rem; font-weight:600; color:{color}; text-transform:uppercase; letter-spacing:0.04em;">
                {esc(label)}
            </div>
        </div>
    </div>
    """


# ═════════════════════════════════════════════════════════════════════════════
# Sidebar & Authentication
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="section-eyebrow">CONFIGURATION</div>', unsafe_allow_html=True)
    api_base = st.text_input("API Base URL", value=API_BASE)

    # Health Check Indicator
    try:
        health_check = requests.get(f"{api_base}/health", timeout=3)
        api_online = health_check.status_code == 200
    except Exception:
        api_online = False

    if api_online:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.82rem; color:var(--teal); margin-bottom:1rem;">'
            '<span style="width:8px; height:8px; border-radius:50%; background:var(--teal); box-shadow:0 0 8px var(--teal);"></span>'
            'API ONLINE & READY</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.82rem; color:var(--crimson); margin-bottom:1rem;">'
            '<span style="width:8px; height:8px; border-radius:50%; background:var(--crimson); box-shadow:0 0 8px var(--crimson);"></span>'
            'API OFFLINE</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-eyebrow">ACCOUNT & AUTH</div>', unsafe_allow_html=True)
    if st.session_state.get("auth_token"):
        acct = st.session_state.get("auth_user", {})
        st.markdown(f"**{esc(acct.get('email', ''))}**")
        st.caption(f"{esc(acct.get('organization', ''))} · {'Admin' if acct.get('is_admin') else 'Member'}")
        if st.button("Log out", use_container_width=True):
            for k in ("auth_token", "auth_user", "scan_data", "report_pdf_bytes", "report_scan_id", "batch_data"):
                st.session_state.pop(k, None)
            st.rerun()
    else:
        tab_login, tab_register = st.tabs(["Log in", "Register"])
        with tab_login:
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log in", key="login_btn", use_container_width=True):
                try:
                    r = requests.post(
                        f"{api_base}/auth/login",
                        data={"username": login_email, "password": login_password},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.session_state["auth_token"] = r.json()["access_token"]
                        st.session_state["auth_user"] = r.json()
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Login failed."))
                except requests.ConnectionError:
                    st.error(f"Cannot reach backend at {api_base}.")

        with tab_register:
            reg_name = st.text_input("Full name", key="reg_name")
            reg_org = st.text_input("Organization", key="reg_org")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password (min 8 chars)", type="password", key="reg_password")
            if st.button("Create Account", key="register_btn", use_container_width=True):
                try:
                    r = requests.post(
                        f"{api_base}/auth/register",
                        json={
                            "email": reg_email,
                            "password": reg_password,
                            "full_name": reg_name or None,
                            "organization": reg_org,
                        },
                        timeout=10,
                    )
                    if r.status_code == 201:
                        st.session_state["auth_token"] = r.json()["access_token"]
                        st.session_state["auth_user"] = r.json()
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Registration failed."))
                except requests.ConnectionError:
                    st.error(f"Cannot reach backend at {api_base}.")

    st.markdown('<div class="section-eyebrow">FORENSIC ENGINE</div>', unsafe_allow_html=True)
    modules = [
        ("Layer-Order Forensics", True),
        ("Digital Fingerprinting", True),
        ("Homoglyph & Zero-Width", True),
        ("Hidden Text & BBox", True),
        ("AI Authorship Synthesis", True),
        ("True Match Scoring", True),
    ]
    for name, done in modules:
        dot_color = "var(--teal)" if done else "var(--text-faint)"
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.84rem; color:var(--text-dim); padding:0.2rem 0;">'
            f'<span style="width:6px; height:6px; border-radius:50%; background:{dot_color};"></span>{esc(name)}</div>',
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# Main App Header
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="case-hero">
        <div>
            <h1>🕵️ ATS Fraud Detector — Forensic Station</h1>
            <div class="sub">
                Deep document analysis: detects zero-width stuffing, homoglyphs, white-on-white text,
                layer-order scrambling, and synthetic AI writing to generate a unified Trust Score.
            </div>
        </div>
        <div class="case-stamp">AUDIT VERIFIED</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("auth_token"):
    st.info("👋 Welcome to ATS Fraud Detector! Log in or create an account in the sidebar to run forensic scans.")
    st.stop()

auth_headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}


# ═════════════════════════════════════════════════════════════════════════════
# Navigation Tabs
# ═════════════════════════════════════════════════════════════════════════════
tab_scan, tab_inspect, tab_batch, tab_badge = st.tabs([
    "📄 Single Resume Scan",
    "🔬 Side-by-Side Span Inspector",
    "📊 Batch Leaderboard",
    "🛡️ Shareable Trust Badge",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Single Resume Scan
# ─────────────────────────────────────────────────────────────────────────────
with tab_scan:
    col_upload, col_jd = st.columns([1, 1])

    with col_upload:
        with st.container(border=True):
            st.markdown("**1. Upload Candidate Resume (PDF)**")
            uploaded_file = st.file_uploader(
                "Choose PDF resume", type=["pdf"], label_visibility="collapsed"
            )

    with col_jd:
        with st.container(border=True):
            st.markdown("**2. Job Description (Optional — for True Match Score)**")
            jd_input = st.text_area(
                "Paste Job Description",
                placeholder="Paste the target job description or requirements here to calculate clean keyword fit…",
                height=130,
                label_visibility="collapsed",
            )

    run_scan_btn = st.button("⚡ Run Forensic Scan", type="primary", use_container_width=True)

    if run_scan_btn:
        if uploaded_file is None:
            st.warning("Please select a PDF file before starting the scan.")
        else:
            with st.spinner("Analyzing document structure, Unicode codepoints, and content streams…"):
                try:
                    form_data = {}
                    if jd_input.strip():
                        form_data["job_description"] = jd_input.strip()

                    resp = requests.post(
                        f"{api_base}/scan",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data=form_data,
                        headers=auth_headers,
                        timeout=60,
                    )
                    if resp.status_code == 201:
                        st.session_state["scan_data"] = resp.json()
                        st.session_state.pop("report_pdf_bytes", None)
                        st.session_state.pop("report_scan_id", None)
                        st.success("Audit complete!")
                    elif resp.status_code == 401:
                        st.session_state.pop("auth_token", None)
                        st.error("Session expired. Please log in again from the sidebar.")
                        st.rerun()
                    else:
                        st.error(f"Scan failed ({resp.status_code}): {resp.text}")
                except requests.ConnectionError:
                    st.error(f"Cannot reach backend API at {api_base}. Ensure uvicorn is running.")

    if "scan_data" in st.session_state:
        data = st.session_state["scan_data"]
        fraud = data["fraud_summary"]
        ai = data.get("ai_content", {})
        match = data.get("true_match")
        trust = data.get("trust_score", {})
        narrative = data.get("narrative", {})

        st.markdown('<div class="section-eyebrow">VERDICT &amp; EXPLAINABILITY</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Composite Trust Score</div>', unsafe_allow_html=True)

        # Verdict Card with SVG Gauge & Explainability
        t_score = trust.get("score", 0.0)
        t_label = trust.get("label", "Unknown")
        badge_svg = render_svg_gauge(t_score, t_label)

        st.markdown(
            f"""
            <div class="verdict-card">
                <div>{badge_svg}</div>
                <div class="verdict-info">
                    <div class="verdict-title">{esc(narrative.get('verdict_title', f'{t_label} Verdict'))}</div>
                    <div style="font-size:0.88rem; color:var(--text-dim);">{esc(narrative.get('summary', ''))}</div>
                    <div class="verdict-rec"><b>Recommendation:</b> {esc(narrative.get('recommendation', ''))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Forensic Explainability Factors
        if narrative.get("key_factors"):
            with st.expander("🔍 Why This Score? — Detailed Forensic Factors", expanded=True):
                for f in narrative["key_factors"]:
                    st.markdown(f"• {esc(f)}")
                st.caption(f"ℹ️ {esc(narrative.get('limitations_disclaimer', ''))}")

        # Metrics overview
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Trust Score", f"{t_score:.0f}/100", delta=t_label)
        m2.metric("High Fraud Signals", fraud.get("high", 0))
        m3.metric("Total Anomaly Signals", fraud.get("total", 0))
        m4.metric("AI Content Score", f"{ai.get('score', 0):.0f}/100")
        m5.metric("True Match Score", f"{match.get('score', 0):.0f}/100" if match else "N/A")

        # Fraud Signals Table
        st.markdown('<div class="section-eyebrow">EVIDENCE LOG</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Detected Manipulation Signals</div>', unsafe_allow_html=True)

        signals = fraud.get("signals", [])
        if signals:
            rows_html = []
            for s in signals:
                sev = s.get("severity", "low")
                desc = s.get("description", "")
                ev = s.get("evidence_text") or "—"
                chip = f'<span class="chip {esc(sev)}">{esc(sev.upper())}</span>'
                rows_html.append(
                    f"<tr><td>{chip}</td><td><code>{esc(s.get('signal_type', ''))}</code></td>"
                    f"<td>{s.get('page', 1)}</td><td>{esc(desc)}</td><td><code>{esc(ev[:70])}</code></td></tr>"
                )
            table_markup = f"""
            <table class="evidence-table">
                <thead><tr><th>Severity</th><th>Signal Type</th><th>Page</th><th>Forensic Analysis</th><th>Offending Evidence</th></tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
            """
            st.markdown(table_markup, unsafe_allow_html=True)
        else:
            st.success("✅ Clean document — zero ATS evasion or manipulation signals detected.")

        # Heatmap & Report Download
        st.markdown('<div class="section-eyebrow">FORENSIC PDF EVIDENCE</div>', unsafe_allow_html=True)
        scan_id = data["scan_id"]
        c_rep1, c_rep2 = st.columns([1, 2])
        with c_rep1:
            if st.button("📥 Generate Forensic PDF Dossier", key="gen_report_btn"):
                with st.spinner("Compiling annotated PDF heatmap and chain-of-custody evidence..."):
                    try:
                        r = requests.get(f"{api_base}/report/{scan_id}/pdf", headers=auth_headers, timeout=60)
                        if r.status_code == 200:
                            st.session_state["report_pdf_bytes"] = r.content
                            st.session_state["report_scan_id"] = scan_id
                        else:
                            st.error(f"Report generation error: {r.text}")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

            if st.session_state.get("report_pdf_bytes") and st.session_state.get("report_scan_id") == scan_id:
                st.download_button(
                    label="⬇ Download Audit Dossier (PDF)",
                    data=st.session_state["report_pdf_bytes"],
                    file_name=f"ats_fraud_report_scan_{scan_id}.pdf",
                    mime="application/pdf",
                )

        with c_rep2:
            st.caption(
                f"Certified Forensic Report includes SHA-256 fingerprint (`{data.get('sha256', '')[:16]}...`), "
                "color-coded visual bounding boxes burned directly onto document pages, and itemized evidence tables."
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Side-by-Side Span Inspector
# ─────────────────────────────────────────────────────────────────────────────
with tab_inspect:
    st.markdown('<div class="section-title">Forensic Span Inspector</div>', unsafe_allow_html=True)
    st.caption("Inspects the underlying document content stream, separating clean text from flagged manipulation spans.")

    if "scan_data" not in st.session_state:
        st.info("Run a scan in the 'Single Resume Scan' tab first to populate the forensic inspector.")
    else:
        current_scan_id = st.session_state["scan_data"]["scan_id"]
        try:
            inspect_res = requests.get(f"{api_base}/scan/{current_scan_id}/inspect", headers=auth_headers, timeout=15)
            if inspect_res.status_code == 200:
                insp_data = inspect_res.json()
                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("### 🔍 Flagged Anomalous Spans")
                    flagged = insp_data.get("flagged_spans", [])
                    if flagged:
                        for sp in flagged:
                            signals_on_span = sp.get("matching_signals", [])
                            sev = signals_on_span[0].get("severity", "high") if signals_on_span else "high"
                            with st.container(border=True):
                                st.markdown(f'<span class="chip {sev}">{sev.upper()}</span> **Page {sp.get("page")}**', unsafe_allow_html=True)
                                st.code(sp.get("text", ""), language=None)
                                st.caption(f"Font: `{sp.get('font_name')}` | Size: `{sp.get('font_size')}pt` | Color: `{sp.get('font_color')}`")
                                for sig in signals_on_span:
                                    st.markdown(f"**Anomaly:** {sig.get('signal_type')} — *{sig.get('description')}*")
                    else:
                        st.success("No flagged spans found in this document.")

                with col_right:
                    st.markdown("### 🛡️ Clean Extracted Text Sample")
                    sample_clean = insp_data.get("sample_clean_spans", [])
                    if sample_clean:
                        clean_text_concat = "\n".join(f"[P{s.get('page')}] {s.get('text')}" for s in sample_clean[:25])
                        st.text_area("Authentic Candidate Text", value=clean_text_concat, height=450)
                    else:
                        st.info("No clean spans available.")
            else:
                st.error("Failed to load span inspection details.")
        except Exception as exc:
            st.error(f"Inspection error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Batch Leaderboard
# ─────────────────────────────────────────────────────────────────────────────
with tab_batch:
    st.markdown('<div class="section-title">Batch Scan &amp; Recruiter Leaderboard</div>', unsafe_allow_html=True)
    st.caption("Upload multiple candidate resumes simultaneously to audit and rank candidates by Trust Score.")

    b_col1, b_col2 = st.columns([1, 1])
    with b_col1:
        batch_files = st.file_uploader(
            "Drop multiple resume PDFs", type=["pdf"], accept_multiple_files=True
        )
    with b_col2:
        batch_jd = st.text_area(
            "Target Job Description for Batch Ranking",
            placeholder="Paste Job Description to rank candidates by True Match Score...",
            height=100,
        )

    if st.button("🚀 Process Batch & Rank Candidates", type="primary"):
        if not batch_files:
            st.warning("Please upload at least one PDF file.")
        else:
            with st.spinner(f"Batch auditing {len(batch_files)} resumes..."):
                try:
                    multipart = [("files", (f.name, f.getvalue(), "application/pdf")) for f in batch_files]
                    b_form = {}
                    if batch_jd.strip():
                        b_form["job_description"] = batch_jd.strip()

                    b_resp = requests.post(
                        f"{api_base}/scan/batch",
                        files=multipart,
                        data=b_form,
                        headers=auth_headers,
                        timeout=180,
                    )
                    if b_resp.status_code == 201:
                        st.session_state["batch_data"] = b_resp.json()
                        st.success("Batch evaluation complete!")
                    else:
                        st.error(f"Batch failed: {b_resp.text}")
                except Exception as exc:
                    st.error(f"Batch request error: {exc}")

    if "batch_data" in st.session_state:
        b_res = st.session_state["batch_data"]
        leaderboard = b_res.get("leaderboard", [])

        st.markdown(f"### Candidate Leaderboard ({len(leaderboard)} Resumes Audited)")
        if leaderboard:
            df = pd.DataFrame(leaderboard)[[
                "filename", "trust_score", "trust_label", "high_fraud_signals",
                "total_fraud_signals", "ai_content_score", "true_match_score", "summary"
            ]]
            df.columns = [
                "Filename", "Trust Score", "Verdict", "High Signals",
                "Total Signals", "AI Score", "Job Fit %", "Forensic Summary"
            ]
            st.dataframe(df, use_container_width=True)

            # Quick drilldown selector
            selected_file = st.selectbox("Select Candidate to view dossier:", [c["filename"] for c in leaderboard])
            cand = next((c for c in leaderboard if c["filename"] == selected_file), None)
            if cand:
                st.markdown(
                    f'<div class="verdict-card">'
                    f'<div class="verdict-title">{esc(cand["filename"])} — Trust Score {cand["trust_score"]:.0f}/100 ({cand["trust_label"]})</div>'
                    f'<div style="color:var(--text-dim);">{esc(cand.get("summary", ""))}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Shareable Trust Badge & Recruiter Export
# ─────────────────────────────────────────────────────────────────────────────
with tab_badge:
    st.markdown('<div class="section-title">Shareable Trust Badge &amp; Recruiter Export</div>', unsafe_allow_html=True)
    st.caption("Attach verified Trust Badges directly to recruiter shortlists, ATS notes, or executive summaries.")

    if "scan_data" not in st.session_state:
        st.info("Run a scan in the 'Single Resume Scan' tab first to generate candidate badges.")
    else:
        sdata = st.session_state["scan_data"]
        curr_id = sdata["scan_id"]
        badge_url = f"{api_base}/scan/{curr_id}/badge.svg"

        b_left, b_right = st.columns([1, 2])
        with b_left:
            st.markdown("### Live Trust Badge")
            try:
                b_resp = requests.get(badge_url, headers=auth_headers, timeout=10)
                if b_resp.status_code == 200:
                    st.image(b_resp.content, width=280)
                else:
                    st.error("Could not fetch badge.")
            except Exception as exc:
                st.error(f"Error fetching badge: {exc}")

        with b_right:
            st.markdown("### Embed Snippets")
            md_snippet = f"[![ATS Trust Score]({badge_url})]({api_base}/scan/{curr_id})"
            st.text_area("Markdown Embed (for GitHub / Jira / Notion)", value=md_snippet, height=70)

            recruiter_note = (
                f"Candidate: {sdata.get('filename')}\n"
                f"SHA-256: {sdata.get('sha256')}\n"
                f"Trust Score: {sdata.get('trust_score', {}).get('score')}/100 ({sdata.get('trust_score', {}).get('label')})\n"
                f"Fraud Signals: {sdata.get('fraud_summary', {}).get('total')} ({sdata.get('fraud_summary', {}).get('high')} High)\n"
                f"Verdict: {sdata.get('narrative', {}).get('recommendation')}"
            )
            st.text_area("Recruiter ATS Shortlist Note", value=recruiter_note, height=130)


# ═════════════════════════════════════════════════════════════════════════════
# Footer
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"""
    <div class="case-footer">
        <span>ATS FRAUD DETECTOR · FORENSIC AUDIT STATION</span>
        <span>VERSION 2.0 · EVIDENCE VERIFIED</span>
    </div>
    """,
    unsafe_allow_html=True,
)