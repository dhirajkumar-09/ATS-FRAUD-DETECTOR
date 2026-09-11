"""
frontend/app.py — ATS Fraud Detector: Premium Forensic Dashboard
=================================================================
Investor-grade SaaS security dashboard with:
  • Glassmorphism card system with layered depth
  • Animated SVG Trust Score gauge (160px, bold KPI focus)
  • Custom stat cards, severity pills, scannable evidence table
  • Themed empty/loading/error states
  • Side-by-Side Span Inspector, Batch Leaderboard, Trust Badge
  • @media (prefers-reduced-motion) accessibility
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

# ═══════════════════════════════════════════════════════════════════════════════
# Design System — Premium Forensic Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary:    #080A0F;
    --bg-secondary:  #0D0F14;
    --bg-card:       #111318;
    --bg-card-hover: #161820;
    --bg-elevated:   #1A1D26;
    --border:        #1E2230;
    --border-bright: #2A3040;
    --border-glow:   rgba(16, 185, 129, 0.15);

    --text-primary:  #F4F5F7;
    --text-secondary:#A0A6B4;
    --text-tertiary: #636A7C;
    --text-disabled: #3D4455;

    --green:         #10B981;
    --green-dim:     rgba(16, 185, 129, 0.12);
    --green-glow:    rgba(16, 185, 129, 0.35);
    --amber:         #F59E0B;
    --amber-dim:     rgba(245, 158, 11, 0.12);
    --amber-glow:    rgba(245, 158, 11, 0.35);
    --red:           #EF4444;
    --red-dim:       rgba(239, 68, 68, 0.12);
    --red-glow:      rgba(239, 68, 68, 0.35);
    --cyan:          #06B6D4;
    --cyan-dim:      rgba(6, 182, 212, 0.10);
    --purple:        #8B5CF6;
    --purple-dim:    rgba(139, 92, 246, 0.10);

    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 18px;
    --shadow-card: 0 4px 16px -2px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3);
    --shadow-hover: 0 8px 28px -4px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.3);
}

/* ─── Animations ──────────────────────────────────────────────────────────── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 6px var(--green-glow); }
    50%      { box-shadow: 0 0 16px var(--green-glow); }
}
@keyframes radarSweep {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes gaugeAppear {
    from { stroke-dashoffset: 339.292; }
}
@keyframes shimmer {
    0%   { background-position: -200px 0; }
    100% { background-position: 200px 0; }
}

@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* ─── Global ──────────────────────────────────────────────────────────────── */
html, body, .stApp {
    background:
        radial-gradient(ellipse 800px 400px at 8% -5%, rgba(16,185,129,0.06) 0%, transparent 55%),
        radial-gradient(ellipse 600px 400px at 92% 105%, rgba(6,182,212,0.04) 0%, transparent 50%),
        var(--bg-primary) !important;
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
.stApp > header { background: transparent !important; }

/* ─── Hero Header ─────────────────────────────────────────────────────────── */
.hero-header {
    background: linear-gradient(135deg, rgba(17,19,24,0.9) 0%, rgba(8,10,15,0.95) 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.6rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: var(--shadow-card);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, var(--green) 50%, transparent 100%);
    opacity: 0.4;
}
.hero-header h1 {
    font-size: 1.7rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.025em;
    color: var(--text-primary);
}
.hero-header .sub {
    color: var(--text-secondary);
    font-size: 0.88rem;
    margin-top: 0.3rem;
    line-height: 1.45;
}
.hero-stamp {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 0.4rem 0.9rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--green);
    background: var(--green-dim);
    color: var(--green);
    white-space: nowrap;
    text-shadow: 0 0 8px var(--green-glow);
}

/* ─── Section Headers ─────────────────────────────────────────────────────── */
.section-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--cyan);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 1.8rem 0 0.3rem 0;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}
.section-label::after {
    content: "";
    flex-grow: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border-bright), transparent 80%);
}
.section-heading {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0 0 1rem 0;
    color: var(--text-primary);
}

/* ─── Glass Cards ─────────────────────────────────────────────────────────── */
.glass-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem;
    box-shadow: var(--shadow-card);
    animation: fadeSlideUp 0.35s ease both;
    position: relative;
    overflow: hidden;
}
.glass-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
}
.glass-card:hover {
    border-color: var(--border-bright);
}

/* ─── Verdict Card ────────────────────────────────────────────────────────── */
.verdict-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    padding: 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2.5rem;
    box-shadow: var(--shadow-card);
    animation: fadeSlideUp 0.4s ease both;
    position: relative;
    overflow: hidden;
}
.verdict-panel::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--green), transparent);
    opacity: 0.35;
}
.verdict-panel.caution::before { background: linear-gradient(90deg, transparent, var(--amber), transparent); }
.verdict-panel.high-risk::before { background: linear-gradient(90deg, transparent, var(--red), transparent); }

.verdict-body { flex: 1; min-width: 280px; }
.verdict-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
    color: var(--text-primary);
}
.verdict-summary {
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
}
.verdict-rec {
    font-size: 0.86rem;
    line-height: 1.5;
    background: var(--bg-elevated);
    border-left: 3px solid var(--green);
    padding: 0.7rem 1rem;
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    color: var(--text-primary);
}
.verdict-panel.caution .verdict-rec { border-left-color: var(--amber); }
.verdict-panel.high-risk .verdict-rec { border-left-color: var(--red); }

/* ─── KPI Stat Cards ──────────────────────────────────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.75rem;
    margin: 1rem 0 1.5rem 0;
}
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem 1.1rem;
    text-align: center;
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    border-color: var(--border-bright);
    box-shadow: var(--shadow-hover);
}
.kpi-card .kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.65rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1.1;
}
.kpi-card .kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.35rem;
}
.kpi-card.green { border-top: 2px solid var(--green); }
.kpi-card.green .kpi-value { color: var(--green); }
.kpi-card.amber { border-top: 2px solid var(--amber); }
.kpi-card.amber .kpi-value { color: var(--amber); }
.kpi-card.red   { border-top: 2px solid var(--red); }
.kpi-card.red .kpi-value { color: var(--red); }
.kpi-card.cyan  { border-top: 2px solid var(--cyan); }
.kpi-card.cyan .kpi-value { color: var(--cyan); }
.kpi-card.purple { border-top: 2px solid var(--purple); }
.kpi-card.purple .kpi-value { color: var(--purple); }

/* ─── Severity Pills ──────────────────────────────────────────────────────── */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    border-radius: 4px;
    padding: 0.18rem 0.5rem;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
    white-space: nowrap;
}
.pill.high   { background: var(--red-dim);   color: #FCA5A5; border-color: rgba(239,68,68,0.35); }
.pill.medium { background: var(--amber-dim); color: #FCD34D; border-color: rgba(245,158,11,0.35); }
.pill.low    { background: var(--green-dim); color: #6EE7B7; border-color: rgba(16,185,129,0.35); }
.pill.match  { background: var(--cyan-dim);  color: #67E8F9; border-color: rgba(6,182,212,0.35); }
.pill.verified { background: var(--green-dim); color: var(--green); border-color: rgba(16,185,129,0.35); }
.pill.caution  { background: var(--amber-dim); color: var(--amber); border-color: rgba(245,158,11,0.35); }
.pill.high-risk { background: var(--red-dim); color: var(--red); border-color: rgba(239,68,68,0.35); }

/* ─── Evidence Table ──────────────────────────────────────────────────────── */
.ev-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.84rem;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--border);
}
.ev-table th {
    background: var(--bg-elevated);
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-tertiary);
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.ev-table td {
    background: var(--bg-card);
    padding: 0.65rem 0.9rem;
    border-bottom: 1px solid var(--border);
    color: var(--text-primary);
    vertical-align: top;
    line-height: 1.4;
}
.ev-table tr:nth-child(even) td { background: var(--bg-secondary); }
.ev-table tr:hover td { background: var(--bg-card-hover); }
.ev-table tr:last-child td { border-bottom: none; }
.ev-table .mono { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--text-secondary); }
.ev-table .desc-text { max-width: 300px; }

/* ─── Empty / Error / Loading States ──────────────────────────────────────── */
.state-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 2.5rem 2rem;
    text-align: center;
    box-shadow: var(--shadow-card);
}
.state-card .state-icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
.state-card .state-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.4rem;
}
.state-card .state-desc {
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.5;
}
.state-card.error { border-color: rgba(239,68,68,0.3); }
.state-card.error .state-title { color: var(--red); }

/* ─── Radar Loading ───────────────────────────────────────────────────────── */
.radar-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem;
}
.radar-ring {
    position: relative;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 2px solid var(--green);
    background: radial-gradient(circle, rgba(16,185,129,0.1) 0%, transparent 65%);
    box-shadow: 0 0 16px var(--green-glow);
    margin-bottom: 1rem;
    overflow: hidden;
}
.radar-arm {
    position: absolute;
    top: 50%; left: 50%;
    width: 40px; height: 40px;
    background: linear-gradient(45deg, rgba(16,185,129,0.5), transparent);
    transform-origin: top left;
    animation: radarSweep 1.6s linear infinite;
}

/* ─── Span Card ───────────────────────────────────────────────────────────── */
.span-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.65rem;
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s;
}
.span-card:hover { border-color: var(--border-bright); }
.span-card .span-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-tertiary);
    margin-top: 0.5rem;
}
.span-card .span-anomaly {
    font-size: 0.82rem;
    color: var(--amber);
    margin-top: 0.4rem;
}

/* ─── Leaderboard Table ───────────────────────────────────────────────────── */
.lb-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.84rem;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--border);
}
.lb-table th {
    background: var(--bg-elevated);
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-tertiary);
    padding: 0.75rem 0.9rem;
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    cursor: pointer;
}
.lb-table th:hover { color: var(--text-secondary); }
.lb-table td {
    background: var(--bg-card);
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid var(--border);
    color: var(--text-primary);
    vertical-align: middle;
}
.lb-table tr:nth-child(even) td { background: var(--bg-secondary); }
.lb-table tr:hover td { background: var(--bg-card-hover); }
.lb-table tr:last-child td { border-bottom: none; }

/* ─── Footer ──────────────────────────────────────────────────────────────── */
.app-footer {
    margin-top: 3rem;
    padding: 1.2rem 0;
    border-top: 1px solid var(--border);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-disabled);
    display: flex;
    justify-content: space-between;
    letter-spacing: 0.04em;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════
def esc(x) -> str:
    return _html.escape(str(x)) if x is not None else ""


def _verdict_class(label: str) -> str:
    if label == "High Risk":
        return "high-risk"
    elif label == "Caution":
        return "caution"
    return "verified"


def _pill_class(label: str) -> str:
    return _verdict_class(label).replace(" ", "-")


def _kpi_color(label: str) -> str:
    return {"Verified": "green", "Caution": "amber", "High Risk": "red"}.get(label, "green")


def render_svg_gauge(score: float, label: str) -> str:
    score_val = max(0.0, min(100.0, float(score or 0)))
    radius = 54
    circumference = 2 * 3.14159265 * radius
    dash_offset = circumference * (1.0 - (score_val / 100.0))

    if label == "Verified":
        color, glow = "#10B981", "rgba(16,185,129,0.4)"
    elif label == "Caution":
        color, glow = "#F59E0B", "rgba(245,158,11,0.4)"
    else:
        color, glow = "#EF4444", "rgba(239,68,68,0.4)"

    pill_cls = _pill_class(label)

    return f"""
    <div style="display:flex; justify-content:center; align-items:center; width:160px; height:160px; position:relative;">
        <svg width="160" height="160" viewBox="0 0 140 140">
            <!-- Outer glow ring -->
            <circle cx="70" cy="70" r="62" fill="none" stroke="{color}" stroke-width="1" opacity="0.15"/>
            <!-- Track -->
            <circle cx="70" cy="70" r="{radius}" fill="none" stroke="#1A1D26" stroke-width="10"/>
            <!-- Progress -->
            <circle cx="70" cy="70" r="{radius}" fill="none" stroke="{color}" stroke-width="10"
                    stroke-linecap="round"
                    stroke-dasharray="{circumference}"
                    stroke-dashoffset="{dash_offset}"
                    transform="rotate(-90 70 70)"
                    style="filter: drop-shadow(0 0 10px {glow}); animation: gaugeAppear 1.2s ease forwards;"/>
        </svg>
        <div style="position:absolute; text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:2.2rem; font-weight:700; color:#FFFFFF; line-height:1;">
                {score_val:.0f}
            </div>
            <div style="margin-top:4px;">
                <span class="pill {pill_cls}" style="font-size:0.62rem;">{esc(label).upper()}</span>
            </div>
        </div>
    </div>
    """


def render_state(icon: str, title: str, desc: str, error: bool = False) -> str:
    cls = "state-card error" if error else "state-card"
    return f"""
    <div class="{cls}">
        <div class="state-icon">{icon}</div>
        <div class="state-title">{esc(title)}</div>
        <div class="state-desc">{esc(desc)}</div>
    </div>
    """


def render_loading() -> str:
    return """
    <div class="radar-container">
        <div class="radar-ring"><div class="radar-arm"></div></div>
        <div style="font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:var(--text-tertiary); letter-spacing:0.06em;">
            ANALYZING DOCUMENT STRUCTURE…
        </div>
    </div>
    """


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar — Configuration & Auth
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="section-label">CONFIGURATION</div>', unsafe_allow_html=True)
    api_base = st.text_input("API Base URL", value=API_BASE)

    # Health check
    try:
        health_check = requests.get(f"{api_base}/health", timeout=3)
        api_online = health_check.status_code == 200
    except Exception:
        api_online = False

    if api_online:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.78rem; color:var(--green); margin-bottom:1rem;">'
            '<span style="width:7px; height:7px; border-radius:50%; background:var(--green); box-shadow:0 0 8px var(--green-glow); animation:pulseGlow 2s ease infinite;"></span>'
            '<span style="font-family:\'JetBrains Mono\',monospace; letter-spacing:0.06em;">API ONLINE</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.78rem; color:var(--red); margin-bottom:1rem;">'
            '<span style="width:7px; height:7px; border-radius:50%; background:var(--red); box-shadow:0 0 8px var(--red-glow);"></span>'
            '<span style="font-family:\'JetBrains Mono\',monospace; letter-spacing:0.06em;">API OFFLINE</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">ACCOUNT</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-label">FORENSIC MODULES</div>', unsafe_allow_html=True)
    modules = [
        "Layer-Order Forensics",
        "Digital Fingerprinting",
        "Homoglyph & Zero-Width",
        "Hidden Text & BBox",
        "AI Authorship Synthesis",
        "True Match Scoring",
    ]
    for name in modules:
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; color:var(--text-secondary); padding:0.15rem 0;">'
            f'<span style="width:5px; height:5px; border-radius:50%; background:var(--green);"></span>{esc(name)}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Main App Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="hero-header">
        <div>
            <h1>🕵️ ATS Fraud Detector</h1>
            <div class="sub">
                Deep document forensics — detects zero-width stuffing, homoglyphs, hidden text,
                layer-order scrambling, and synthetic AI writing to generate a unified Trust Score.
            </div>
        </div>
        <div class="hero-stamp">FORENSIC STATION</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("auth_token"):
    st.markdown(
        render_state(
            "🔐",
            "Authentication Required",
            "Log in or create an account in the sidebar to access the forensic scanner."
        ),
        unsafe_allow_html=True,
    )
    st.stop()

auth_headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Navigation Tabs
# ═══════════════════════════════════════════════════════════════════════════════
tab_scan, tab_inspect, tab_batch, tab_badge, tab_settings = st.tabs([
    "📄 Single Resume Scan",
    "🔬 Span Inspector",
    "📊 Batch Leaderboard",
    "🛡️ Trust Badge",
    "⚙️ Org Settings",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Single Resume Scan
# ─────────────────────────────────────────────────────────────────────────────
with tab_scan:
    col_upload, col_jd = st.columns([1, 1], gap="medium")

    with col_upload:
        with st.container(border=True):
            st.markdown("**📎 Upload Candidate Resume**")
            uploaded_file = st.file_uploader(
                "Choose PDF resume", type=["pdf"], label_visibility="collapsed"
            )

    with col_jd:
        with st.container(border=True):
            st.markdown("**📋 Job Description** *(optional — enables True Match Score)*")
            jd_input = st.text_area(
                "Paste Job Description",
                placeholder="Paste the target job description here to calculate authentic keyword fit…",
                height=130,
                label_visibility="collapsed",
            )

    run_scan_btn = st.button("⚡ Run Forensic Scan", type="primary", use_container_width=True)

    if run_scan_btn:
        if uploaded_file is None:
            st.markdown(
                render_state("📄", "No File Selected", "Please upload a PDF resume before starting the scan."),
                unsafe_allow_html=True,
            )
        elif not api_online:
            st.markdown(
                render_state("🔌", "Backend Unavailable", f"Cannot reach the API at {api_base}. Start the backend with: uvicorn app.main:app --port 8000", error=True),
                unsafe_allow_html=True,
            )
        else:
            loading_placeholder = st.empty()
            loading_placeholder.markdown(render_loading(), unsafe_allow_html=True)
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
                loading_placeholder.empty()
                if resp.status_code == 201:
                    st.session_state["scan_data"] = resp.json()
                    st.session_state.pop("report_pdf_bytes", None)
                    st.session_state.pop("report_scan_id", None)
                    st.success("Forensic analysis complete.")
                elif resp.status_code == 401:
                    st.session_state.pop("auth_token", None)
                    st.markdown(
                        render_state("🔒", "Session Expired", "Your session has expired. Please log in again from the sidebar.", error=True),
                        unsafe_allow_html=True,
                    )
                    st.rerun()
                else:
                    st.markdown(
                        render_state("❌", "Scan Failed", f"Server returned status {resp.status_code}: {resp.text[:200]}", error=True),
                        unsafe_allow_html=True,
                    )
            except requests.ConnectionError:
                loading_placeholder.empty()
                st.markdown(
                    render_state("🔌", "Connection Error", f"Cannot reach backend at {api_base}. Ensure uvicorn is running.", error=True),
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                loading_placeholder.empty()
                st.markdown(
                    render_state("⚠️", "Unexpected Error", str(exc), error=True),
                    unsafe_allow_html=True,
                )

    # ── Results ──
    if "scan_data" in st.session_state:
        data = st.session_state["scan_data"]
        fraud = data["fraud_summary"]
        ai = data.get("ai_content", {})
        match = data.get("true_match")
        trust = data.get("trust_score", {})
        narrative = data.get("narrative", {})

        t_score = trust.get("score", 0.0)
        t_label = trust.get("label", "Unknown")
        panel_class = _verdict_class(t_label)

        st.markdown('<div class="section-label">VERDICT &amp; ANALYSIS</div>', unsafe_allow_html=True)

        # Verdict panel: gauge + narrative
        gauge_html = render_svg_gauge(t_score, t_label)
        st.markdown(
            f"""
            <div class="verdict-panel {panel_class}">
                <div>{gauge_html}</div>
                <div class="verdict-body">
                    <div class="verdict-title">{esc(narrative.get('verdict_title', f'{t_label} Verdict'))}</div>
                    <div class="verdict-summary">{esc(narrative.get('summary', ''))}</div>
                    <div class="verdict-rec"><b>Recommendation:</b> {esc(narrative.get('recommendation', ''))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # KPI stat cards
        ai_score = ai.get("score", 0)
        match_score = match.get("score", 0) if match else None
        high_signals = fraud.get("high", 0)
        total_signals = fraud.get("total", 0)

        kpi_color = _kpi_color(t_label)
        high_color = "red" if high_signals > 0 else "green"
        ai_color = "red" if ai_score >= 70 else ("amber" if ai_score >= 40 else "green")
        match_color = "cyan"

        match_display = f"{match_score:.0f}" if match_score is not None else "—"

        st.markdown(
            f"""
            <div class="kpi-grid">
                <div class="kpi-card {kpi_color}">
                    <div class="kpi-value">{t_score:.0f}</div>
                    <div class="kpi-label">Trust Score</div>
                </div>
                <div class="kpi-card {high_color}">
                    <div class="kpi-value">{high_signals}</div>
                    <div class="kpi-label">High Signals</div>
                </div>
                <div class="kpi-card amber">
                    <div class="kpi-value">{total_signals}</div>
                    <div class="kpi-label">Total Signals</div>
                </div>
                <div class="kpi-card {ai_color}">
                    <div class="kpi-value">{ai_score:.0f}</div>
                    <div class="kpi-label">AI Content</div>
                </div>
                <div class="kpi-card {match_color}">
                    <div class="kpi-value">{match_display}</div>
                    <div class="kpi-label">Job Fit %</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Explainability factors
        if narrative.get("key_factors"):
            with st.expander("🔍 Why This Score? — Forensic Factor Breakdown", expanded=False):
                for f in narrative["key_factors"]:
                    st.markdown(f"- {esc(f)}")
                st.caption(f"ℹ️ {esc(narrative.get('limitations_disclaimer', ''))}")

        # Evidence table
        st.markdown('<div class="section-label">EVIDENCE LOG</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-heading">Detected Manipulation Signals</div>', unsafe_allow_html=True)

        signals = fraud.get("signals", [])
        if signals:
            rows_html = []
            for i, s in enumerate(signals, 1):
                sev = s.get("severity", "low")
                desc = s.get("description", "")
                ev = s.get("evidence_text") or "—"
                sig_type = s.get("signal_type", "").replace("_", " ")
                pill = f'<span class="pill {esc(sev)}">{esc(sev.upper())}</span>'
                rows_html.append(
                    f"<tr>"
                    f"<td style='color:var(--text-tertiary); font-family:JetBrains Mono,monospace; font-size:0.72rem;'>{i}</td>"
                    f"<td>{pill}</td>"
                    f"<td class='mono'>{esc(sig_type)}</td>"
                    f"<td style='text-align:center;'>{s.get('page', 1)}</td>"
                    f"<td class='desc-text'>{esc(desc[:180])}</td>"
                    f"<td class='mono' style='max-width:160px; word-break:break-all;'>{esc(ev[:80])}</td>"
                    f"</tr>"
                )
            st.markdown(
                f"""
                <table class="ev-table">
                    <thead><tr>
                        <th>#</th><th>Severity</th><th>Signal Type</th><th>Pg</th><th>Analysis</th><th>Evidence</th>
                    </tr></thead>
                    <tbody>{''.join(rows_html)}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                render_state("✅", "Clean Document", "Zero ATS evasion or manipulation signals detected in this resume."),
                unsafe_allow_html=True,
            )

        # Hidden Words Detected section
        hidden_words = data.get("hidden_words", []) or []
        if hidden_words:
            st.markdown('<div class="section-label">HIDDEN WORDS</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-heading">Hidden Words Detected</div>', unsafe_allow_html=True)
            hw_rows_html = []
            for hw in hidden_words:
                hidden_text = (
                    hw.get("text") or hw.get("hidden_text") or hw.get("word") or "—"
                )
                sev = (hw.get("severity") or "low").lower()
                sig_type = (hw.get("signal_type") or hw.get("type") or "—").replace("_", " ")
                pill = f'<span class="pill {esc(sev)}">{esc(sev.upper())}</span>'
                hw_rows_html.append(
                    f"<tr>"
                    f"<td class='mono' style='max-width:260px; word-break:break-all;'>{esc(str(hidden_text)[:160])}</td>"
                    f"<td style='text-align:center;'>{hw.get('page', '—')}</td>"
                    f"<td>{pill}</td>"
                    f"<td class='mono'>{esc(sig_type)}</td>"
                    f"</tr>"
                )
            st.markdown(
                f"""
                <table class="ev-table">
                    <thead><tr>
                        <th>Hidden Text</th><th>Page</th><th>Severity</th><th>Signal Type</th>
                    </tr></thead>
                    <tbody>{''.join(hw_rows_html)}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )

        # Report download

        st.markdown('<div class="section-label">FORENSIC REPORT</div>', unsafe_allow_html=True)
        scan_id = data["scan_id"]
        c_rep1, c_rep2 = st.columns([1, 2])
        with c_rep1:
            if st.button("📥 Generate Forensic PDF", key="gen_report_btn"):
                report_loading = st.empty()
                report_loading.markdown(render_loading(), unsafe_allow_html=True)
                try:
                    r = requests.get(f"{api_base}/report/{scan_id}/pdf", headers=auth_headers, timeout=60)
                    report_loading.empty()
                    if r.status_code == 200:
                        st.session_state["report_pdf_bytes"] = r.content
                        st.session_state["report_scan_id"] = scan_id
                    else:
                        st.markdown(
                            render_state("❌", "Report Generation Failed", f"Server error: {r.text[:200]}", error=True),
                            unsafe_allow_html=True,
                        )
                except Exception as exc:
                    report_loading.empty()
                    st.markdown(
                        render_state("⚠️", "Error", str(exc), error=True),
                        unsafe_allow_html=True,
                    )

            if st.session_state.get("report_pdf_bytes") and st.session_state.get("report_scan_id") == scan_id:
                st.download_button(
                    label="⬇ Download Audit Report (PDF)",
                    data=st.session_state["report_pdf_bytes"],
                    file_name=f"ats_fraud_report_scan_{scan_id}.pdf",
                    mime="application/pdf",
                )

        with c_rep2:
            sha_preview = data.get("sha256", "")[:20]
            st.caption(
                f"Forensic report includes SHA-256 fingerprint (`{sha_preview}…`), "
                "color-coded heatmap overlays, itemized signal evidence, and executive briefing."
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: Side-by-Side Span Inspector
# ─────────────────────────────────────────────────────────────────────────────
with tab_inspect:
    st.markdown('<div class="section-heading">Forensic Span Inspector</div>', unsafe_allow_html=True)
    st.caption("Compare clean extracted text against flagged manipulation spans from the document content stream.")

    if "scan_data" not in st.session_state:
        st.markdown(
            render_state("🔬", "No Scan Data", "Run a forensic scan in the Single Resume Scan tab first to populate the inspector."),
            unsafe_allow_html=True,
        )
    else:
        current_scan_id = st.session_state["scan_data"]["scan_id"]
        try:
            inspect_res = requests.get(f"{api_base}/scan/{current_scan_id}/inspect", headers=auth_headers, timeout=15)
            if inspect_res.status_code == 200:
                insp_data = inspect_res.json()
                col_flagged, col_clean = st.columns(2, gap="medium")

                with col_flagged:
                    st.markdown("#### 🚩 Flagged Anomalous Spans")
                    flagged = insp_data.get("flagged_spans", [])
                    if flagged:
                        for sp in flagged:
                            signals_on_span = sp.get("matching_signals", [])
                            sev = signals_on_span[0].get("severity", "high") if signals_on_span else "high"
                            pill_html = f'<span class="pill {sev}">{sev.upper()}</span>'
                            anomaly_lines = "".join(
                                f'<div class="span-anomaly">⚠ {esc(sig.get("signal_type", "").replace("_"," "))} — {esc(sig.get("description", ""))}</div>'
                                for sig in signals_on_span
                            )
                            st.markdown(
                                f"""
                                <div class="span-card">
                                    <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                                        {pill_html}
                                        <span style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:var(--text-tertiary);">Page {sp.get("page")}</span>
                                    </div>
                                    <code style="font-size:0.82rem; color:var(--text-primary); word-break:break-all;">{esc(sp.get("text", ""))}</code>
                                    <div class="span-meta">Font: {esc(sp.get('font_name'))} · Size: {sp.get('font_size')}pt · Color: {esc(sp.get('font_color'))}</div>
                                    {anomaly_lines}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            render_state("✅", "No Flagged Spans", "All extracted spans appear authentic — no anomalous formatting detected."),
                            unsafe_allow_html=True,
                        )

                with col_clean:
                    st.markdown("#### 🛡️ Clean Extracted Text")
                    sample_clean = insp_data.get("sample_clean_spans", [])
                    if sample_clean:
                        clean_text_concat = "\n".join(f"[P{s.get('page')}] {s.get('text')}" for s in sample_clean[:30])
                        st.text_area("Authenticated candidate text", value=clean_text_concat, height=500, label_visibility="collapsed")
                    else:
                        st.markdown(
                            render_state("📄", "No Clean Spans", "No clean text spans available for this document."),
                            unsafe_allow_html=True,
                        )
            elif inspect_res.status_code == 401:
                st.session_state.pop("auth_token", None)
                st.rerun()
            else:
                st.markdown(
                    render_state("❌", "Inspection Failed", f"Server returned status {inspect_res.status_code}.", error=True),
                    unsafe_allow_html=True,
                )
        except requests.ConnectionError:
            st.markdown(
                render_state("🔌", "Backend Unavailable", f"Cannot reach {api_base}.", error=True),
                unsafe_allow_html=True,
            )
        except Exception as exc:
            st.markdown(
                render_state("⚠️", "Error", str(exc), error=True),
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: Batch Leaderboard
# ─────────────────────────────────────────────────────────────────────────────
with tab_batch:
    st.markdown('<div class="section-heading">Batch Scan &amp; Recruiter Leaderboard</div>', unsafe_allow_html=True)
    st.caption("Upload multiple candidate resumes to audit and rank by Trust Score.")

    b_col1, b_col2 = st.columns([1, 1], gap="medium")
    with b_col1:
        with st.container(border=True):
            st.markdown("**📎 Upload Multiple Resumes**")
            batch_files = st.file_uploader(
                "Drop resume PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed"
            )
    with b_col2:
        with st.container(border=True):
            st.markdown("**📋 Job Description** *(for ranking)*")
            batch_jd = st.text_area(
                "Target Job Description",
                placeholder="Paste Job Description to rank candidates by fit…",
                height=100,
                label_visibility="collapsed",
            )

    if st.button("🚀 Process Batch & Rank", type="primary", use_container_width=True):
        if not batch_files:
            st.markdown(
                render_state("📄", "No Files Selected", "Upload at least one PDF resume to start batch processing."),
                unsafe_allow_html=True,
            )
        elif not api_online:
            st.markdown(
                render_state("🔌", "Backend Unavailable", f"Cannot reach the API at {api_base}.", error=True),
                unsafe_allow_html=True,
            )
        else:
            batch_loading = st.empty()
            batch_loading.markdown(render_loading(), unsafe_allow_html=True)
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
                batch_loading.empty()
                if b_resp.status_code == 201:
                    st.session_state["batch_data"] = b_resp.json()
                    st.success("Batch evaluation complete.")
                elif b_resp.status_code == 401:
                    st.session_state.pop("auth_token", None)
                    st.rerun()
                else:
                    st.markdown(
                        render_state("❌", "Batch Failed", f"Server returned {b_resp.status_code}: {b_resp.text[:200]}", error=True),
                        unsafe_allow_html=True,
                    )
            except requests.ConnectionError:
                batch_loading.empty()
                st.markdown(
                    render_state("🔌", "Connection Error", f"Cannot reach {api_base}.", error=True),
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                batch_loading.empty()
                st.markdown(
                    render_state("⚠️", "Error", str(exc), error=True),
                    unsafe_allow_html=True,
                )

    if "batch_data" in st.session_state:
        b_res = st.session_state["batch_data"]
        leaderboard = b_res.get("leaderboard", [])

        st.markdown(f'<div class="section-label">{len(leaderboard)} CANDIDATES AUDITED</div>', unsafe_allow_html=True)

        if leaderboard:
            # Build HTML table
            rows_html = []
            for rank, c in enumerate(leaderboard, 1):
                trust_s = c.get("trust_score", 0)
                trust_l = c.get("trust_label", "Unknown")
                pill_cls = _pill_class(trust_l)
                ts_display = f'<span class="pill {pill_cls}" style="font-size:0.7rem;">{trust_s:.0f} {trust_l.upper()}</span>'
                ai_s = c.get("ai_content_score", 0)
                match_s = c.get("true_match_score")
                match_display = f"{match_s:.0f}" if match_s is not None else "—"
                rows_html.append(
                    f"<tr>"
                    f"<td style='font-family:JetBrains Mono,monospace; font-size:0.78rem; color:var(--text-tertiary); text-align:center;'>{rank}</td>"
                    f"<td>{esc(c.get('filename', ''))}</td>"
                    f"<td>{ts_display}</td>"
                    f"<td style='text-align:center;'>{c.get('high_fraud_signals', 0)}</td>"
                    f"<td style='text-align:center;'>{c.get('total_fraud_signals', 0)}</td>"
                    f"<td style='text-align:center;'>{ai_s:.0f}</td>"
                    f"<td style='text-align:center;'>{match_display}</td>"
                    f"</tr>"
                )
            st.markdown(
                f"""
                <table class="lb-table">
                    <thead><tr>
                        <th>Rank</th><th>Candidate</th><th>Trust Score</th><th>High</th><th>Total</th><th>AI %</th><th>Fit %</th>
                    </tr></thead>
                    <tbody>{''.join(rows_html)}</tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )

            # Drilldown
            selected_file = st.selectbox("Select candidate for details:", [c["filename"] for c in leaderboard])
            cand = next((c for c in leaderboard if c["filename"] == selected_file), None)
            if cand:
                cand_label = cand.get("trust_label", "Unknown")
                cand_class = _verdict_class(cand_label)
                st.markdown(
                    f"""
                    <div class="glass-card" style="margin-top:0.8rem;">
                        <div style="display:flex; align-items:center; gap:1rem; margin-bottom:0.6rem;">
                            <span style="font-size:1.1rem; font-weight:600;">{esc(cand["filename"])}</span>
                            <span class="pill {_pill_class(cand_label)}">{cand.get("trust_score", 0):.0f} {cand_label.upper()}</span>
                        </div>
                        <div style="font-size:0.86rem; color:var(--text-secondary); line-height:1.5;">
                            {esc(cand.get("summary", "No summary available."))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                render_state("📊", "No Results", "Batch processing returned no results."),
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4: Shareable Trust Badge
# ─────────────────────────────────────────────────────────────────────────────
with tab_badge:
    st.markdown('<div class="section-heading">Shareable Trust Badge &amp; Recruiter Export</div>', unsafe_allow_html=True)
    st.caption("Attach verified Trust Badges to recruiter shortlists, ATS notes, or executive summaries.")

    if "scan_data" not in st.session_state:
        st.markdown(
            render_state("🛡️", "No Scan Data", "Run a scan in the Single Resume Scan tab first to generate a candidate badge."),
            unsafe_allow_html=True,
        )
    else:
        sdata = st.session_state["scan_data"]
        curr_id = sdata["scan_id"]
        badge_url = f"{api_base}/scan/{curr_id}/badge.svg"

        b_left, b_right = st.columns([1, 2], gap="medium")
        with b_left:
            st.markdown("#### Live Trust Badge")
            try:
                b_resp = requests.get(badge_url, headers=auth_headers, timeout=10)
                if b_resp.status_code == 200:
                    b64 = base64.b64encode(b_resp.content).decode()
                    st.markdown(
                        f'<div style="display:flex; justify-content:center; padding:1.5rem;">'
                        f'<img src="data:image/svg+xml;base64,{b64}" width="300" alt="Trust Badge"/>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        render_state("❌", "Badge Unavailable", "Could not fetch the trust badge from the server.", error=True),
                        unsafe_allow_html=True,
                    )
            except Exception as exc:
                st.markdown(
                    render_state("⚠️", "Error", str(exc), error=True),
                    unsafe_allow_html=True,
                )

        with b_right:
            st.markdown("#### Embed & Export")
            md_snippet = f"[![ATS Trust Score]({badge_url})]({api_base}/scan/{curr_id})"
            st.text_area("Markdown Embed (GitHub / Jira / Notion)", value=md_snippet, height=70)

            t_info = sdata.get("trust_score", {})
            f_info = sdata.get("fraud_summary", {})
            n_info = sdata.get("narrative", {})
            recruiter_note = (
                f"Candidate: {sdata.get('filename')}\n"
                f"SHA-256: {sdata.get('sha256')}\n"
                f"Trust Score: {t_info.get('score')}/100 ({t_info.get('label')})\n"
                f"Fraud Signals: {f_info.get('total')} ({f_info.get('high')} High)\n"
                f"Verdict: {n_info.get('recommendation')}"
            )
            st.text_area("Recruiter ATS Shortlist Note", value=recruiter_note, height=140)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5: Org Settings
# ─────────────────────────────────────────────────────────────────────────────
with tab_settings:
    acct = st.session_state.get("auth_user", {})
    is_admin = bool(acct.get("is_admin"))
    org_name = acct.get("organization", "")

    st.markdown(f"**Organization:** {esc(org_name)}")
    st.caption(
        "These two thresholds override the app-wide defaults "
        "(`NEAR_WHITE_THRESHOLD`, `HIDDEN_FONT_SIZE_PT`) for every scan run by "
        "anyone in this organization. Leave a field blank to fall back to the "
        "app default."
    )

    if not api_online:
        st.markdown(
            render_state("🔌", "Backend Unavailable", f"Cannot reach the API at {api_base}.", error=True),
            unsafe_allow_html=True,
        )
    else:
        try:
            settings_resp = requests.get(f"{api_base}/auth/org-settings", headers=auth_headers, timeout=10)
        except requests.ConnectionError:
            settings_resp = None

        if settings_resp is None:
            st.markdown(
                render_state("🔌", "Backend Unavailable", f"Cannot reach the API at {api_base}.", error=True),
                unsafe_allow_html=True,
            )
        elif settings_resp.status_code == 401:
            st.markdown(
                render_state("🔒", "Session Expired", "Your session has expired. Please log in again from the sidebar.", error=True),
                unsafe_allow_html=True,
            )
        elif settings_resp.status_code != 200:
            st.markdown(
                render_state("❌", "Could Not Load Settings", "Failed to fetch current org settings from the server.", error=True),
                unsafe_allow_html=True,
            )
        else:
            current = settings_resp.json()
            cur_near_white = current.get("near_white_threshold")
            cur_hidden_font = current.get("hidden_font_size_pt")

            with st.container(border=True):
                st.markdown("**Current Overrides**")
                c1, c2 = st.columns(2)
                c1.metric("Near-White Threshold", cur_near_white if cur_near_white is not None else "App default")
                c2.metric("Hidden Font Size (pt)", cur_hidden_font if cur_hidden_font is not None else "App default")

            if not is_admin:
                st.info("Only org admins can change these settings. Ask your organization's admin to update them.")
            else:
                with st.form("org_settings_form"):
                    use_default_nw = st.checkbox(
                        "Use app default for Near-White Threshold",
                        value=cur_near_white is None,
                        key="use_default_nw",
                    )
                    new_near_white = st.number_input(
                        "Near-White Threshold (RGB Euclidean distance)",
                        min_value=0, max_value=255,
                        value=cur_near_white if cur_near_white is not None else 30,
                        disabled=use_default_nw,
                    )

                    use_default_hf = st.checkbox(
                        "Use app default for Hidden Font Size",
                        value=cur_hidden_font is None,
                        key="use_default_hf",
                    )
                    new_hidden_font = st.number_input(
                        "Hidden Font Size Threshold (pt)",
                        min_value=0.0, max_value=72.0, step=0.5,
                        value=float(cur_hidden_font) if cur_hidden_font is not None else 1.0,
                        disabled=use_default_hf,
                    )

                    save_settings_btn = st.form_submit_button("💾 Save Org Settings", type="primary", use_container_width=True)

                if save_settings_btn:
                    payload = {
                        "near_white_threshold": None if use_default_nw else int(new_near_white),
                        "hidden_font_size_pt": None if use_default_hf else float(new_hidden_font),
                    }
                    try:
                        put_resp = requests.put(
                            f"{api_base}/auth/org-settings", json=payload, headers=auth_headers, timeout=10,
                        )
                        if put_resp.status_code == 200:
                            st.success("Org settings updated. New thresholds apply to all future scans.")
                            st.rerun()
                        elif put_resp.status_code == 403:
                            st.error("Only org admins can update these settings.")
                        else:
                            st.error(put_resp.json().get("detail", "Failed to save settings."))
                    except requests.ConnectionError:
                        st.error(f"Cannot reach backend at {api_base}.")


# ═══════════════════════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="app-footer">
        <span>ATS FRAUD DETECTOR · FORENSIC AUDIT STATION</span>
        <span>VERSION 3.0 · EVIDENCE INTEGRITY VERIFIED</span>
    </div>
    """,
    unsafe_allow_html=True,
)