"""
frontend/app.py — Streamlit frontend for ATS Fraud Detector (Phase 1-4)
=============================================================================
Run with:
    streamlit run frontend/app.py
"""
import base64
import html as _html

import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="ATS Fraud Detector",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
# Design system — "case file" / evidence-room visual language
# ═════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --ink-900: #0D0F14;
    --ink-850: #12141B;
    --ink-800: #171A22;
    --ink-750: #1D2029;
    --ink-700: #262A35;
    --line:    #2A2F3B;
    --paper:      #F1ECDD;
    --paper-line: #DAD2B9;
    --paper-text: #22201A;
    --text:      #E8E6DF;
    --text-dim:  #9BA0AF;
    --text-faint:#666B7A;
    --crimson:      #E15550;
    --crimson-soft: rgba(225, 85, 80, 0.14);
    --amber:        #DE9F2E;
    --amber-soft:   rgba(222, 159, 46, 0.14);
    --straw:        #C7B24F;
    --straw-soft:   rgba(199, 178, 79, 0.14);
    --teal:         #3CB697;
    --teal-soft:    rgba(60, 182, 151, 0.14);
}

html, body, .stApp {
    background: radial-gradient(ellipse 1200px 600px at 15% -10%, #171B26 0%, var(--ink-900) 55%) !important;
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

/* ── Typography ─────────────────────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'Fraunces', serif !important;
    color: var(--text) !important;
    letter-spacing: -0.01em;
}
p, span, label, div { font-family: 'Inter', sans-serif; }
code, .mono { font-family: 'IBM Plex Mono', monospace !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--ink-850) !important;
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] input {
    background: var(--ink-800) !important;
    color: var(--text) !important;
    border: 1px solid var(--line) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
}

/* ── Cards (st.container(border=True)) ─────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--ink-800);
    border: 1px solid var(--line) !important;
    border-radius: 10px;
    padding: 0.4rem 0.2rem;
}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(180deg, #46C6A5 0%, var(--teal) 100%) !important;
    color: #0B1512 !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(60, 182, 151, 0.25);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(60, 182, 151, 0.35);
}
.stButton > button:active { transform: translateY(0); }
.stDownloadButton > button {
    background: var(--ink-750) !important;
    color: var(--text) !important;
    border: 1px solid var(--teal) !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
}

/* ── File uploader — dropzone look ─────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    background: var(--ink-750) !important;
    border: 1.5px dashed var(--line) !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--text-dim) !important; }

/* ── Text areas / inputs ────────────────────────────────────────────────── */
.stTextArea textarea, .stTextInput input {
    background: var(--ink-750) !important;
    color: var(--text) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
}

/* ── Metrics ────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--ink-750);
    border: 1px solid var(--line);
    border-radius: 9px;
    padding: 0.7rem 0.9rem;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: var(--text) !important;
}
[data-testid="stMetricLabel"] { color: var(--text-dim) !important; }

/* ── Progress bars ──────────────────────────────────────────────────────── */
.stProgress > div > div > div { background: var(--ink-700) !important; }
.stProgress > div > div > div > div { background: var(--teal) !important; }

/* ── Expanders ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--ink-800);
    border: 1px solid var(--line) !important;
    border-radius: 9px;
}
[data-testid="stExpander"] summary { color: var(--text) !important; font-weight: 500; }

/* ── Dataframes ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }

/* ── Dividers ───────────────────────────────────────────────────────────── */
hr { border-color: var(--line) !important; }

/* ── Alerts (info/success/error) ───────────────────────────────────────── */
[data-testid="stAlert"] {
    background: var(--ink-750) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
}

/* ── Custom components ─────────────────────────────────────────────────── */
.case-hero {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 1.6rem 1.8rem; margin-bottom: 1.2rem;
    background: linear-gradient(135deg, var(--ink-800) 0%, var(--ink-850) 100%);
    border: 1px solid var(--line); border-radius: 14px;
}
.case-hero h1 { font-size: 2.1rem; margin: 0 0 0.3rem 0; font-weight: 600; }
.case-hero .sub { color: var(--text-dim); font-size: 0.98rem; max-width: 640px; line-height: 1.5; }
.case-hero .tags { margin-top: 0.9rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tag {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
    color: var(--text-dim); border: 1px solid var(--line);
    border-radius: 5px; padding: 0.22rem 0.55rem; background: var(--ink-750);
}
.case-stamp {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
    color: var(--teal); border: 1px solid var(--teal); border-radius: 6px;
    padding: 0.35rem 0.7rem; white-space: nowrap; transform: rotate(2deg);
}

.section-eyebrow {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem;
    color: var(--text-faint); margin: 1.6rem 0 0.3rem 0;
}
.section-title { font-size: 1.35rem; font-weight: 600; margin: 0 0 0.8rem 0; }

.module-row {
    display: flex; align-items: center; gap: 0.55rem;
    padding: 0.32rem 0; font-size: 0.86rem; color: var(--text-dim);
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--teal); flex-shrink: 0; }
.dot.pending { background: var(--text-faint); }

.chip {
    display: inline-block; font-family: 'IBM Plex Mono', monospace;
    font-size: 0.74rem; border-radius: 5px; padding: 0.18rem 0.5rem;
    margin: 0.12rem 0.28rem 0.12rem 0; border: 1px solid transparent;
}
.chip.high   { background: var(--crimson-soft); color: var(--crimson); border-color: rgba(225,85,80,0.35); }
.chip.medium { background: var(--amber-soft);   color: var(--amber);   border-color: rgba(222,159,46,0.35); }
.chip.low    { background: var(--straw-soft);   color: var(--straw);   border-color: rgba(199,178,79,0.35); }
.chip.match  { background: var(--teal-soft);    color: var(--teal);    border-color: rgba(60,182,151,0.35); }
.chip.missing{ background: var(--crimson-soft); color: var(--crimson); border-color: rgba(225,85,80,0.35); }
.chip.extra  { background: var(--ink-700);      color: var(--text-dim); border-color: var(--line); }

.evidence-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.evidence-table th {
    text-align: left; font-family: 'IBM Plex Mono', monospace; font-weight: 500;
    font-size: 0.72rem; color: var(--text-faint); padding: 0.5rem 0.7rem;
    border-bottom: 1px solid var(--line);
}
.evidence-table td {
    padding: 0.6rem 0.7rem; border-bottom: 1px solid var(--ink-700);
    color: var(--text); vertical-align: top;
}
.evidence-table tr:hover td { background: var(--ink-750); }
.evidence-table .ev-text { font-family: 'IBM Plex Mono', monospace; color: var(--text-dim); font-size: 0.8rem; }

.gauge-wrap { display: flex; align-items: center; gap: 1.1rem; }
.gauge {
    position: relative; width: 120px; height: 120px; border-radius: 50%;
    background: conic-gradient(var(--gauge-color) calc(var(--pct) * 1%), var(--ink-700) 0);
    flex-shrink: 0;
}
.gauge::after {
    content: ""; position: absolute; inset: 10px; border-radius: 50%;
    background: var(--ink-800);
}
.gauge-value {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; z-index: 1;
}
.gauge-value .num { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem; font-weight: 600; color: var(--text); }
.gauge-value .lbl { font-size: 0.65rem; color: var(--text-faint); letter-spacing: 0.03em; }
.gauge-verdict { font-size: 1rem; font-weight: 600; margin-bottom: 0.2rem; }
.gauge-note { font-size: 0.82rem; color: var(--text-dim); line-height: 1.4; }

.case-footer {
    margin-top: 2.2rem; padding-top: 1rem; border-top: 1px solid var(--line);
    font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--text-faint);
    display: flex; justify-content: space-between;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# Small render helpers
# ═════════════════════════════════════════════════════════════════════════════
def esc(x) -> str:
    return _html.escape(str(x)) if x is not None else ""


def severity_chip(severity: str) -> str:
    sev = (severity or "low").lower()
    return f'<span class="chip {esc(sev)}">{esc(sev.upper())}</span>'


def skill_chips(skills: list[str], kind: str) -> str:
    if not skills:
        return '<span style="color:var(--text-faint); font-size:0.85rem;">None</span>'
    return "".join(f'<span class="chip {kind}">{esc(s)}</span>' for s in skills)


def gauge_html(score: float, color_var: str) -> str:
    pct = max(0.0, min(100.0, float(score or 0)))
    return f"""
    <div class="gauge" style="--pct:{pct}; --gauge-color:var({color_var});">
        <div class="gauge-value">
            <div class="num">{pct:.0f}</div>
            <div class="lbl">/ 100</div>
        </div>
    </div>
    """


# ═════════════════════════════════════════════════════════════════════════════
# Hero
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="case-hero">
        <div>
            <h1>🕵️ ATS Fraud Detector</h1>
            <div class="sub">
                Scans resume PDFs for ATS manipulation — hidden text, zero-width characters,
                homoglyph swaps, off-page content, and timeline gaps — then scores AI-written
                content and true job-description fit.
            </div>
            <div class="tags">
                <span class="tag">zero-width scan</span>
                <span class="tag">homoglyph scan</span>
                <span class="tag">hidden-text scan</span>
                <span class="tag">timeline check</span>
                <span class="tag">ai content score</span>
                <span class="tag">true match score</span>
                <span class="tag">forensic pdf export</span>
            </div>
        </div>
        <div class="case-stamp">SYSTEM READY</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-eyebrow">CONFIGURATION</div>', unsafe_allow_html=True)
    api_base = st.text_input("API base URL", value=API_BASE)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-eyebrow">SYSTEM MODULES</div>', unsafe_allow_html=True)
    modules = [
        ("Extraction", True),
        ("Fraud Detectors", True),
        ("AI Score + Match", True),
        ("Heatmap + Report", True),
    ]
    for name, done in modules:
        dot_cls = "dot" if done else "dot pending"
        st.markdown(
            f'<div class="module-row"><span class="{dot_cls}"></span>{esc(name)}</div>',
            unsafe_allow_html=True,
        )

# ── Upload + JD ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-eyebrow">STEP 1</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Submit the case file</div>', unsafe_allow_html=True)

col_upload, col_jd = st.columns([1, 1])

with col_upload:
    with st.container(border=True):
        st.markdown("**Resume PDF**")
        uploaded = st.file_uploader(
            "Choose a PDF file", type=["pdf"], label_visibility="collapsed"
        )

with col_jd:
    with st.container(border=True):
        st.markdown("**Job description** · optional, enables True Match Score")
        jd_text = st.text_area(
            "Job description",
            placeholder="Paste the full job description here…",
            height=170,
            label_visibility="collapsed",
        )

if uploaded is None:
    st.info("Upload a PDF to begin scanning.")
    st.stop()

# ── Scan ──────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
_, mid, _ = st.columns([2, 1, 2])
with mid:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

if run_clicked:
    with st.spinner("Scanning…"):
        try:
            form_data: dict = {}
            if jd_text.strip():
                form_data["job_description"] = jd_text.strip()

            resp = requests.post(
                f"{api_base}/scan",
                files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                data=form_data,
                timeout=60,
            )
        except requests.ConnectionError:
            st.error(
                f"Cannot reach API at `{api_base}`. Start the backend:\n\n"
                "```bash\ncd backend && uvicorn app.main:app --reload\n```"
            )
            st.stop()

    if resp.status_code == 201:
        data = resp.json()
        st.success(f"Scan complete — scan ID **{data['scan_id']}**")
        st.session_state["scan_data"] = data
        st.session_state.pop("report_pdf_bytes", None)
        st.session_state.pop("report_scan_id", None)
    else:
        st.error(f"API error {resp.status_code}: {resp.text}")
        st.stop()

if "scan_data" not in st.session_state:
    st.stop()

data = st.session_state["scan_data"]
fraud = data["fraud_summary"]
ai    = data.get("ai_content", {})
match = data.get("true_match")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# Section A — Extraction summary
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">EVIDENCE SHEET 01</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Extraction summary</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Pages",         data["page_count"])
c2.metric("Total Spans",   data["span_count"])
c3.metric("Clean Words",   ai.get("clean_word_count", "—"))
c4.metric("Flagged Words", ai.get("flagged_word_count", "—"))

# ═════════════════════════════════════════════════════════════════════════════
# Section B — Fraud signals
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">EVIDENCE SHEET 02</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Fraud signals</div>', unsafe_allow_html=True)

bh, bm, bl, bt = st.columns(4)
bh.metric("High",   fraud["high"])
bm.metric("Medium", fraud["medium"])
bl.metric("Low",    fraud["low"])
bt.metric("Total",  fraud["total"])

signals = fraud.get("signals", [])
if signals:
    rows_html = []
    for s in signals:
        desc = s["description"][:120] + ("…" if len(s["description"]) > 120 else "")
        evidence = (s.get("evidence_text") or "")[:60]
        rows_html.append(
            f"""<tr>
                <td>{severity_chip(s['severity'])}</td>
                <td class="ev-text">{esc(s['signal_type'])}</td>
                <td>{s['page']}</td>
                <td>{esc(desc)}</td>
                <td class="ev-text">{esc(evidence)}</td>
            </tr>"""
        )
    table_html = f"""
    <table class="evidence-table">
        <thead><tr>
            <th>Severity</th><th>Type</th><th>Page</th><th>Description</th><th>Evidence</th>
        </tr></thead>
        <tbody>{''.join(rows_html)}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.success("No fraud signals detected.")

# ═════════════════════════════════════════════════════════════════════════════
# Section C — AI Content Score & True Match Score (side by side gauges)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">EVIDENCE SHEET 03</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">AI content &amp; job-fit scoring</div>', unsafe_allow_html=True)

score_col1, score_col2 = st.columns(2)

with score_col1:
    with st.container(border=True):
        ai_score = ai.get("score", 0.0)
        backend  = ai.get("backend", "heuristic")
        breakdown = ai.get("breakdown", {})

        if ai_score >= 70:
            verdict, color = "Likely AI-written", "--crimson"
        elif ai_score >= 40:
            verdict, color = "Possibly AI-assisted", "--amber"
        else:
            verdict, color = "Likely human-written", "--teal"

        st.markdown(
            f"""
            <div class="gauge-wrap">
                {gauge_html(ai_score, color)}
                <div>
                    <div class="gauge-verdict">{esc(verdict)}</div>
                    <div class="gauge-note">AI Content Score · backend: <span class="mono">{esc(backend)}</span></div>
                    {f'<div class="gauge-note">{esc(ai.get("note",""))}</div>' if ai.get("note") else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if breakdown:
            st.markdown("<br>", unsafe_allow_html=True)
            for signal_name, val in breakdown.items():
                if isinstance(val, (int, float)):
                    pct = float(val)
                    st.progress(min(int(pct), 100), text=f"{signal_name.replace('_', ' ').title()}: {pct:.1f}")

with score_col2:
    with st.container(border=True):
        if match is None:
            st.markdown("**True Match Score**")
            st.info("Paste a job description above and re-run the scan to see this score.")
        else:
            ms = match.get("score", 0.0)
            if ms >= 70:
                verdict, color = "Strong match", "--teal"
            elif ms >= 40:
                verdict, color = "Partial match", "--amber"
            else:
                verdict, color = "Weak match", "--crimson"

            st.markdown(
                f"""
                <div class="gauge-wrap">
                    {gauge_html(ms, color)}
                    <div>
                        <div class="gauge-verdict">{esc(verdict)}</div>
                        <div class="gauge-note">True Match Score</div>
                        <div class="gauge-note">TF cosine {match.get('tfidf_cosine', 0):.1f} · skill overlap {match.get('skill_overlap', 0):.1f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            matched = match.get("matched_skills", [])
            missing = match.get("missing_skills", [])
            extra   = match.get("extra_skills", [])
            st.markdown(f"**Matched** ({len(matched)})", unsafe_allow_html=True)
            st.markdown(skill_chips(matched, "match"), unsafe_allow_html=True)
            st.markdown(f"**Missing from resume** ({len(missing)})", unsafe_allow_html=True)
            st.markdown(skill_chips(missing, "missing"), unsafe_allow_html=True)
            st.markdown(f"**Extra — resume only** ({len(extra)})", unsafe_allow_html=True)
            st.markdown(skill_chips(extra, "extra"), unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# Section D — Heatmap Viewer + Forensic Report
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-eyebrow">EVIDENCE SHEET 04</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Heatmap &amp; forensic report</div>', unsafe_allow_html=True)
st.caption(
    "Fetches the backend's annotated forensic report — heatmap pages and evidence log "
    "baked into one PDF, including the SHA-256 chain-of-custody stamp."
)

scan_id = data["scan_id"]

if st.button("Generate / Fetch Forensic Report", key="fetch_report_btn"):
    with st.spinner("Building forensic report (baking the heatmap onto the PDF)…"):
        report_resp = None
        try:
            report_resp = requests.get(f"{api_base}/report/{scan_id}/pdf", timeout=120)
        except requests.ConnectionError:
            st.error(f"Cannot reach API at `{api_base}`.")

    if report_resp is not None:
        if report_resp.status_code == 200:
            st.session_state["report_pdf_bytes"] = report_resp.content
            st.session_state["report_scan_id"] = scan_id
        else:
            st.error(f"Report generation failed ({report_resp.status_code}): {report_resp.text}")

if (
    st.session_state.get("report_pdf_bytes")
    and st.session_state.get("report_scan_id") == scan_id
):
    pdf_bytes = st.session_state["report_pdf_bytes"]

    dl_col, info_col = st.columns([1, 3])
    with dl_col:
        st.download_button(
            label="⬇ Download Forensic Report (PDF)",
            data=pdf_bytes,
            file_name=f"ats_fraud_report_scan_{scan_id}.pdf",
            mime="application/pdf",
        )
    with info_col:
        st.caption(
            f"Report size: {len(pdf_bytes) / 1024:.1f} KB — color-coded heatmap pages with "
            "every flagged region boxed directly on the resume."
        )

    st.markdown("**Heatmap preview** — same pages as the download")
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_iframe = f"""
        <iframe
            src="data:application/pdf;base64,{b64_pdf}"
            width="100%"
            height="800"
            style="border: 1px solid #2A2F3B; border-radius: 10px;"
            type="application/pdf">
        </iframe>
    """
    st.components.v1.html(pdf_iframe, height=820, scrolling=True)
else:
    st.info("Click **Generate / Fetch Forensic Report** above to build and preview the heatmap PDF.")

# ═════════════════════════════════════════════════════════════════════════════
# Section E — Span preview & metadata
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("Page dimensions"):
    st.table(data["page_dims"])

with st.expander("PDF metadata"):
    meta = data.get("metadata", {})
    if meta:
        st.table([{"key": k, "value": v} for k, v in meta.items()])
    else:
        st.caption("No metadata found.")

with st.expander("Raw span preview (first 10)"):
    spans = data.get("sample_spans", [])
    if spans:
        rows = []
        for sp in spans:
            rows.append({
                "page":       sp["page"],
                "text":       sp["text"][:60] + ("…" if len(sp["text"]) > 60 else ""),
                "font":       sp["font_name"],
                "size (pt)":  sp["font_size"],
                "color (RGB)": str(tuple(sp["font_color"])),
                "bbox":       str([round(v, 1) for v in sp["bbox"]]),
                "origin":     sp["origin"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.warning("No spans returned.")

with st.expander("Full JSON response"):
    st.json(data)

st.markdown(
    f"""
    <div class="case-footer">
        <span>SHA-256 · {esc(data.get('sha256', '—'))}</span>
        <span>SCAN ID · {esc(scan_id)}</span>
    </div>
    """,
    unsafe_allow_html=True,
)