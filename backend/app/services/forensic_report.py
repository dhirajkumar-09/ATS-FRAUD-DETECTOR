"""
forensic_report.py — Improved Forensic PDF
============================================
Generates a professional, print-ready forensic evidence PDF.

Layout
------
  Page 1  — Forensic Summary (light background, readable fonts, proper margins).
             Contains: header, metadata, trust gauge, KPI stat boxes,
             severity summary table, fraud signals table (auto-scaled to fit),
             hidden words table (if present), footer with page numbers.

  Page 2+ — Heatmap-annotated original resume (all original pages preserved).
             Each page carries a repeating header with scan ID + filename.

Design Goals
------------
- Light background (white/near-white) for professional printing
- Minimum 8pt body text, 9pt section headers
- Clear visual hierarchy with coloured accent lines
- No text truncated mid-word — wrapped instead
- Consistent header/footer on every page with page numbers
- Margins: 0.62 inch (LM/RM), 0.50 inch (TM/BM)

Uses ReportLab (canvas) + PyMuPDF (fitz).
"""
from __future__ import annotations

import io
import textwrap
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

from app.services.heatmap_generator import generate_heatmap

# ── Colour palette (light / print-friendly) ──────────────────────────────────
# Backgrounds
BG_PAGE  = (1.0,   1.0,   1.0)       # #FFFFFF — page background
BG_HDR   = (0.094, 0.094, 0.133)     # #181821 — top header banner
BG_META  = (0.961, 0.965, 0.973)     # #F5F6F8 — metadata strip
BG_CARD  = (0.976, 0.980, 0.988)     # #F9FAFE — alternating card rows
BG_ELEV  = (0.929, 0.937, 0.953)     # #EDF0F3 — elevated / stat boxes

# Accent colours
TEAL    = (0.235, 0.714, 0.592)      # #3CB697
GREEN   = (0.094, 0.729, 0.506)      # #18BA81
AMBER   = (0.878, 0.612, 0.184)      # #E09C2F
RED_C   = (0.878, 0.322, 0.322)      # #E05252
CYAN_C  = (0.024, 0.714, 0.831)      # #06B6D4
PURPLE  = (0.659, 0.333, 0.969)      # #A855F7

TRUST_COLORS = {
    "Verified":  GREEN,
    "Caution":   AMBER,
    "High Risk": RED_C,
}
SEV_COLORS = {
    "high":   RED_C,
    "medium": AMBER,
    "low":    GREEN,
}

# Text colours
T_DARK  = (0.078, 0.082, 0.098)      # #141519 — primary text
T_MED   = (0.329, 0.353, 0.412)      # #545A69 — secondary text
T_LIGHT = (0.592, 0.616, 0.675)      # #979CAC — muted / labels
WHITE   = (1.0, 1.0, 1.0)

BORDER  = (0.816, 0.831, 0.867)      # #D0D4DD — divider lines

# Page dimensions (US Letter: 612 × 792 pt)
PAGE_W, PAGE_H = letter

# Margins
LM = 0.62 * inch   # left
RM = 0.62 * inch   # right
TM = 0.50 * inch   # top (below banner)
BM = 0.50 * inch   # bottom (above footer)
CONTENT_W = PAGE_W - LM - RM   # ≈ 7.26 inch


# ── Low-level canvas helpers ──────────────────────────────────────────────────

def _rgb(c: rl_canvas.Canvas, color: tuple) -> None:
    c.setFillColorRGB(*color)

def _stroke(c: rl_canvas.Canvas, color: tuple) -> None:
    c.setStrokeColorRGB(*color)

def _fill_stroke(c, fill, stroke=None):
    c.setFillColorRGB(*fill)
    if stroke:
        c.setStrokeColorRGB(*stroke)

def _rect_fill(c, x, y, w, h, color, radius=0):
    _rgb(c, color)
    if radius:
        c.roundRect(x, y, w, h, radius, fill=1, stroke=0)
    else:
        c.rect(x, y, w, h, fill=1, stroke=0)

def _divider(c, y: float, color=BORDER):
    _stroke(c, color)
    c.setLineWidth(0.35)
    c.line(LM, y, PAGE_W - RM, y)


# ── Gauge (semi-circle) ───────────────────────────────────────────────────────

def _draw_gauge(c, cx: float, cy: float, r: float, score: float, label: str) -> None:
    badge_color = TRUST_COLORS.get(label, T_MED)
    # Track
    _stroke(c, BORDER)
    c.setLineWidth(8)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    # Progress
    if score > 0:
        extent = 180.0 * (score / 100.0)
        _stroke(c, badge_color)
        c.setLineWidth(8)
        c.arc(cx - r, cy - r, cx + r, cy + r, startAng=180 - extent, extent=extent)
    # Score
    _rgb(c, badge_color)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(cx, cy + 2, f"{score:.0f}")
    _rgb(c, T_LIGHT)
    c.setFont("Helvetica", 8)
    c.drawCentredString(cx, cy - 10, "/100")
    _rgb(c, badge_color)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx, cy - 22, label.upper())


# ── Stat box ──────────────────────────────────────────────────────────────────

def _stat_box(c, x, y, w, h, value, label, color):
    _rect_fill(c, x, y, w, h, BG_ELEV, radius=4)
    # Top accent line
    _rect_fill(c, x, y + h - 2, w, 2, color)
    # Value
    _rgb(c, color)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(x + w / 2, y + h - 22, value)
    # Label
    _rgb(c, T_LIGHT)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + w / 2, y + 5, label)


# ── Section label ─────────────────────────────────────────────────────────────

def _section_label(c, label: str, y: float) -> float:
    """Draw a section heading. Returns y coordinate below the label."""
    _rgb(c, TEAL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(LM, y, label)
    label_w = c.stringWidth(label, "Helvetica-Bold", 8)
    _stroke(c, TEAL)
    c.setLineWidth(0.5)
    c.line(LM + label_w + 6, y + 3, PAGE_W - RM, y + 3)
    return y - 0.14 * inch


# ── Word-wrap helper ──────────────────────────────────────────────────────────

def _wrap_text(c, text: str, font: str, size: float, max_w: float, max_lines: int = 3) -> list[str]:
    """Wrap `text` to fit within `max_w` points at the given font/size."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if c.stringWidth(test, font, size) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            # Truncate with ellipsis
            if lines:
                last = lines[-1]
                while last and c.stringWidth(last + "…", font, size) > max_w:
                    last = last[:-1]
                lines[-1] = last + "…"
            return lines
    if current:
        lines.append(current)
    return lines[:max_lines]


# ── Mini table ────────────────────────────────────────────────────────────────

def _draw_mini_table(
    c,
    x: float, y_top: float,
    col_widths: list[float],
    headers: list[str],
    rows: list[list[str]],
    row_h: float = 15.0,
    font_size: float = 7.5,
    max_rows: int | None = None,
    col_colors: dict[int, dict] | None = None,
) -> float:
    """
    Draw a compact table via canvas calls.
    Returns the y coordinate of the table bottom.
    """
    if col_colors is None:
        col_colors = {}

    display_rows = rows if max_rows is None else rows[:max_rows]
    truncated    = max_rows is not None and len(rows) > max_rows
    total_w      = sum(col_widths)
    header_h     = row_h + 3

    # Header background
    _rect_fill(c, x, y_top - header_h, total_w, header_h, BG_ELEV)

    # Header text
    cx_pos = x
    for ci, (hdr, cw) in enumerate(zip(headers, col_widths)):
        color = col_colors.get(ci, {}).get("header", T_MED)
        _rgb(c, color)
        c.setFont("Helvetica-Bold", font_size)
        # Truncate header to fit
        max_ch = max(1, int(cw / (font_size * 0.54)))
        c.drawString(cx_pos + 4, y_top - header_h + 5, hdr[:max_ch])
        cx_pos += cw

    y = y_top - header_h

    for ri, row in enumerate(display_rows):
        bg = BG_PAGE if ri % 2 == 0 else BG_CARD
        _rect_fill(c, x, y - row_h, total_w, row_h, bg)

        cx_pos = x
        for ci, (cell, cw) in enumerate(zip(row, col_widths)):
            cell_color_map = col_colors.get(ci, {}).get("cells", [])
            cell_clr = T_DARK
            for (r_idx, clr) in cell_color_map:
                if r_idx == ri:
                    cell_clr = clr
                    break

            _rgb(c, cell_clr)
            # Fit cell text — single line, truncated
            max_chars = max(1, int(cw / (font_size * 0.52)))
            text = str(cell)[:max_chars]
            c.setFont("Helvetica", font_size)
            c.drawString(cx_pos + 4, y - row_h + 5, text)
            cx_pos += cw

        y -= row_h

    if truncated:
        _rgb(c, T_LIGHT)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 4, y - 4,
                     f"… {len(rows) - max_rows} more rows — see full signals on the heatmap pages")
        y -= 12

    # Table border
    _stroke(c, BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y, total_w, y_top - y, fill=0, stroke=1)

    return y


# ── Page footer helper ────────────────────────────────────────────────────────

def _draw_footer(c, page_num: int, total_pages: int | None = None,
                 scan_id: str = "", filename: str = "") -> None:
    """Draw a consistent footer line on the current canvas page."""
    fy = BM - 0.12 * inch
    _divider(c, fy + 6)
    _rgb(c, T_LIGHT)
    c.setFont("Helvetica", 6.5)
    c.drawString(LM, fy, "CONFIDENTIAL — FOR AUTHORIZED RECRUITER USE ONLY")
    # Page number (right)
    page_str = f"Page {page_num}" + (f" of {total_pages}" if total_pages else "")
    c.drawRightString(PAGE_W - RM, fy, f"ATS Fraud Detector  |  {page_str}")
    # Center: scan ID ref (if provided)
    if scan_id:
        c.drawCentredString(PAGE_W / 2, fy, f"Scan #{scan_id}")


# ── Heatmap page header helper ────────────────────────────────────────────────

def _stamp_heatmap_header(page: fitz.Page, scan_id: str, filename: str,
                           page_num: int, total: int) -> None:
    """
    Stamp a thin header bar and footer onto a heatmap page using PyMuPDF.
    Works directly on the fitz page object.
    """
    pw = page.rect.width
    ph = page.rect.height
    bar_h = 18

    # Header bar
    page.draw_rect(fitz.Rect(0, 0, pw, bar_h), color=None,
                   fill=(0.094, 0.094, 0.133))
    label = f"ATS Fraud Detector — Forensic Heatmap   |   Scan #{scan_id}   |   {filename[:55]}"
    page.insert_text(fitz.Point(8, bar_h - 5), label,
                     fontsize=6.5, color=(0.8, 0.85, 0.8))

    # Footer bar
    footer_y = ph - 14
    page.draw_rect(fitz.Rect(0, footer_y, pw, ph), color=None,
                   fill=(0.094, 0.094, 0.133))
    foot_label = f"Page {page_num} of {total}   |   CONFIDENTIAL"
    page.insert_text(fitz.Point(8, ph - 4), foot_label,
                     fontsize=6, color=(0.6, 0.65, 0.6))


# ── Main public function ──────────────────────────────────────────────────────

def generate_forensic_report(
    scan_result: dict,
    original_pdf_path: Path,
    output_path: Path,
) -> Path:
    """
    Build the forensic evidence PDF and write it to output_path.

    Page 1  = Single-page forensic summary.
    Page 2+ = Heatmap-annotated resume pages (all original pages, with header/footer).

    Parameters
    ----------
    scan_result        : dict with keys: scan_id, filename, sha256, scanned_at,
                         page_count, fraud_summary, ai_content_score,
                         true_match_score, trust_score, narrative, hidden_words.
    original_pdf_path  : Path to the original uploaded PDF on disk.
    output_path        : Destination for the combined report PDF.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    trust       = scan_result.get("trust_score") or {}
    t_score     = float(trust.get("score") or 0)
    t_label     = trust.get("label", "Unknown")
    badge_color = TRUST_COLORS.get(t_label, T_MED)

    fraud        = scan_result.get("fraud_summary", {})
    signals      = fraud.get("signals", [])
    ai_score     = scan_result.get("ai_content_score")
    match_s      = scan_result.get("true_match_score")
    narrative    = scan_result.get("narrative") or {}
    hidden_words = scan_result.get("hidden_words", []) or []
    scan_id      = str(scan_result.get("scan_id", ""))
    filename     = str(scan_result.get("filename", ""))

    # ── Draw Page 1: Forensic Summary ────────────────────────────────────────
    summary_buf = io.BytesIO()
    c = rl_canvas.Canvas(summary_buf, pagesize=letter)

    # Fill page background
    _rect_fill(c, 0, 0, PAGE_W, PAGE_H, BG_PAGE)

    # ── Header banner ─────────────────────────────────────────────────────────
    BANNER_H = 0.72 * inch
    _rect_fill(c, 0, PAGE_H - BANNER_H, PAGE_W, BANNER_H, BG_HDR)
    # Teal accent stripe at top of banner
    _rect_fill(c, 0, PAGE_H - 3, PAGE_W, 3, badge_color)

    _rgb(c, WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(LM, PAGE_H - 0.36 * inch, "ATS Fraud Detector")
    _rgb(c, (0.7, 0.75, 0.72))
    c.setFont("Helvetica", 8)
    c.drawString(LM, PAGE_H - 0.54 * inch, "FORENSIC EVIDENCE REPORT")

    # Verdict stamp (top-right inside banner)
    stamp = t_label.upper()
    sw = len(stamp) * 6.2 + 16
    bx = PAGE_W - RM - sw
    _rect_fill(c, bx, PAGE_H - 0.60 * inch, sw, 20, badge_color, radius=4)
    _rgb(c, WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(bx + sw / 2, PAGE_H - 0.48 * inch, stamp)

    # Generated timestamp
    _rgb(c, (0.55, 0.60, 0.58))
    c.setFont("Helvetica", 6.5)
    c.drawRightString(PAGE_W - RM, PAGE_H - 0.68 * inch, f"Generated: {generated_at}")

    # ── Metadata strip ────────────────────────────────────────────────────────
    FIELD_H = 0.175 * inch
    meta_y = PAGE_H - BANNER_H - 0.04 * inch
    fields = [
        ("Scan ID",  str(scan_result.get("scan_id", "—"))),
        ("File",     filename[:65]),
        ("SHA-256",  (str(scan_result.get("sha256", "—"))[:54] + "…") if scan_result.get("sha256") else "—"),
        ("Pages",    str(scan_result.get("page_count", "—"))),
        ("Scanned",  str(scan_result.get("scanned_at") or generated_at)[:32]),
    ]
    meta_block_h = len(fields) * FIELD_H
    _rect_fill(c, 0, meta_y - meta_block_h, PAGE_W, meta_block_h, BG_META)

    for i, (key, val) in enumerate(fields):
        ry = meta_y - i * FIELD_H
        if i % 2 == 0:
            _rect_fill(c, 0, ry - FIELD_H, PAGE_W, FIELD_H, BG_CARD)
        _rgb(c, T_LIGHT)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(LM, ry - FIELD_H + 5, key)
        _rgb(c, T_DARK)
        c.setFont("Courier", 7)
        c.drawString(LM + 1.0 * inch, ry - FIELD_H + 5, val)

    meta_bottom = meta_y - meta_block_h - 0.14 * inch

    # ── Trust Gauge + Stat boxes ──────────────────────────────────────────────
    gauge_r  = 0.50 * inch
    gauge_cx = LM + gauge_r + 0.05 * inch
    gauge_cy = meta_bottom - gauge_r - 0.22 * inch
    _draw_gauge(c, gauge_cx, gauge_cy, gauge_r, t_score, t_label)

    box_h   = gauge_r * 2 + 0.16 * inch
    box_w   = 1.30 * inch
    box_gap = 0.10 * inch
    stat_x  = gauge_cx + gauge_r + 0.20 * inch

    hs       = fraud.get("high", 0)
    hs_color = RED_C if hs > 0 else GREEN
    ai_val   = f"{ai_score:.1f}" if ai_score is not None else "—"
    ai_color = RED_C if (ai_score or 0) >= 70 else (AMBER if (ai_score or 0) >= 40 else GREEN)
    ms_val   = f"{match_s:.1f}" if match_s is not None else "—"
    tot_val  = str(fraud.get("total", 0))

    _stat_box(c, stat_x,                        gauge_cy - box_h / 2, box_w, box_h, str(hs),  "HIGH SIGNALS",  hs_color)
    _stat_box(c, stat_x + box_w + box_gap,      gauge_cy - box_h / 2, box_w, box_h, tot_val,  "TOTAL SIGNALS", AMBER)
    _stat_box(c, stat_x + 2*(box_w + box_gap),  gauge_cy - box_h / 2, box_w, box_h, ai_val,   "AI CONTENT %",  ai_color)
    _stat_box(c, stat_x + 3*(box_w + box_gap),  gauge_cy - box_h / 2, box_w, box_h, ms_val,   "JOB MATCH %",   CYAN_C)

    # Executive recommendation (right of stat boxes)
    rec = (narrative.get("recommendation") or "")[:240]
    if rec:
        brief_x = stat_x + 4 * (box_w + box_gap) + 0.10 * inch
        brief_w = PAGE_W - RM - brief_x
        if brief_w > 0.7 * inch:
            brief_y_top = gauge_cy + gauge_r + 0.02 * inch
            brief_y_bot = gauge_cy - gauge_r
            _rect_fill(c, brief_x, brief_y_bot, brief_w, brief_y_top - brief_y_bot, BG_ELEV, radius=4)
            _rect_fill(c, brief_x, brief_y_top - 2, brief_w, 2, badge_color)
            _rgb(c, badge_color)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(brief_x + 5, brief_y_top - 12, "RECOMMENDATION")
            _rgb(c, T_MED)
            c.setFont("Helvetica", 6.5)
            lines = _wrap_text(c, rec, "Helvetica", 6.5, brief_w - 10, max_lines=7)
            for li, ln in enumerate(lines):
                c.drawString(brief_x + 5, brief_y_top - 24 - li * 9, ln)

    section_y = gauge_cy - gauge_r - 0.22 * inch

    # ── Fraud Signals table ───────────────────────────────────────────────────
    section_y = _section_label(c, "DETECTED FRAUD SIGNALS", section_y)

    FOOTER_RESERVE = BM + 0.18 * inch
    HW_RESERVE = 0 if not hidden_words else (
        0.22 * inch + (min(len(hidden_words), 8) + 1) * 14 + 0.12 * inch
    )

    sig_budget    = section_y - FOOTER_RESERVE - HW_RESERVE - 0.16 * inch
    sig_row_h     = 14.0
    sig_header_h  = sig_row_h + 3
    max_sig_rows  = max(0, int((sig_budget - sig_header_h) / sig_row_h))

    sig_col_w = [
        0.44 * inch,   # Sev
        1.15 * inch,   # Type
        0.26 * inch,   # Pg
        2.60 * inch,   # Description
        2.81 * inch,   # Evidence
    ]

    if signals:
        sig_rows: list[list[str]] = []
        sig_col_colors: dict[int, dict] = {0: {"header": T_MED, "cells": []}}
        for ri, s in enumerate(signals):
            sev = s.get("severity", "low").lower()
            sev_color = SEV_COLORS.get(sev, T_MED)
            sig_col_colors[0]["cells"].append((ri, sev_color))

            # Evidence: word-wrap to first ~110 chars, no mid-word cut
            evid_raw = (s.get("evidence_text") or "")
            evid = " ".join(evid_raw.split()[:22])   # ~110 chars of real words

            sig_rows.append([
                sev.upper(),
                s.get("signal_type", "—").replace("_", " "),
                str(s.get("page", "—")),
                s.get("description", "")[:130],
                evid,
            ])

        section_y = _draw_mini_table(
            c, LM, section_y,
            col_widths=sig_col_w,
            headers=["SEV", "SIGNAL TYPE", "PG", "DESCRIPTION", "EVIDENCE"],
            rows=sig_rows,
            row_h=sig_row_h,
            font_size=7.5,
            max_rows=max_sig_rows,
            col_colors=sig_col_colors,
        )
    else:
        _rgb(c, GREEN)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(LM, section_y - 12, "✓  No fraud signals detected.")
        section_y -= 22

    section_y -= 0.12 * inch

    # ── AI Paragraph Breakdown table ─────────────────────────────────────────
    ai_paragraphs = (scan_result.get("ai_content") or {}).get("paragraph_ai_breakdown", [])
    high_ai_paragraphs = [p for p in ai_paragraphs if p.get("ai_score", 0) >= 40]
    high_ai_paragraphs.sort(key=lambda p: p.get("ai_score", 0), reverse=True)
    
    if high_ai_paragraphs:
        section_y = _section_label(c, "AI CONTENT FLAG (TOP PARAGRAPHS)", section_y)
        
        ai_col_w = [0.44 * inch, 4.4 * inch, 2.42 * inch]
        ai_rows: list[list[str]] = []
        ai_col_colors: dict[int, dict] = {0: {"header": T_MED, "cells": []}}
        
        for ri, p in enumerate(high_ai_paragraphs[:3]):
            score = p.get("ai_score", 0)
            ai_color = RED_C if score >= 70 else AMBER
            ai_col_colors[0]["cells"].append((ri, ai_color))
            
            snippet = (p.get("text_snippet") or "").replace('\n', ' ')
            snippet = " ".join(snippet.split()[:20]) # ~100 chars
            factors = ", ".join(p.get("contributing_factors", []))
            
            ai_rows.append([
                f"{score:.1f}%",
                f"Page {p.get('page', 1)}: {snippet}...",
                factors[:65]
            ])
            
        section_y = _draw_mini_table(
            c, LM, section_y,
            col_widths=ai_col_w,
            headers=["SCORE", "TEXT SNIPPET", "FLAGGED FACTORS"],
            rows=ai_rows,
            row_h=14.0,
            font_size=7.5,
            max_rows=3,
            col_colors=ai_col_colors,
        )
        section_y -= 0.12 * inch

    # ── Hidden Words table ────────────────────────────────────────────────────
    if hidden_words:
        section_y = _section_label(c, "HIDDEN WORDS DETECTED", section_y)

        hw_col_w = [3.30 * inch, 0.38 * inch, 0.62 * inch, 2.96 * inch]
        hw_rows: list[list[str]] = []
        hw_col_colors: dict[int, dict] = {2: {"header": T_MED, "cells": []}}
        for ri, hw in enumerate(hidden_words):
            sev = str(hw.get("severity", "low")).lower()
            sev_color = SEV_COLORS.get(sev, T_MED)
            hw_col_colors[2]["cells"].append((ri, sev_color))
            hidden_text = str(hw.get("text") or hw.get("hidden_text") or hw.get("word") or "—")
            hw_rows.append([
                hidden_text[:90],
                str(hw.get("page", "—")),
                sev.upper(),
                str(hw.get("signal_type") or hw.get("type") or "—").replace("_", " "),
            ])

        hw_budget = section_y - FOOTER_RESERVE
        hw_max    = max(0, int((hw_budget - 17) / 14))

        section_y = _draw_mini_table(
            c, LM, section_y,
            col_widths=hw_col_w,
            headers=["HIDDEN TEXT", "PG", "SEV", "SIGNAL TYPE"],
            rows=hw_rows,
            row_h=14.0,
            font_size=7.5,
            max_rows=hw_max,
            col_colors=hw_col_colors,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    _draw_footer(c, page_num=1, scan_id=scan_id, filename=filename)

    c.showPage()
    c.save()
    summary_buf.seek(0)

    # ── Generate heatmap resume pages ─────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        heatmap_path = Path(tmpdir) / "heatmap.pdf"
        generate_heatmap(original_pdf_path, signals, heatmap_path)

        # ── Merge with fitz ───────────────────────────────────────────────────
        summary_doc = fitz.open(stream=summary_buf.read(), filetype="pdf")
        heatmap_doc = fitz.open(str(heatmap_path))

        # Stamp header + footer on each heatmap page
        total_pages = 1 + len(heatmap_doc)
        for i, page in enumerate(heatmap_doc):
            _stamp_heatmap_header(
                page,
                scan_id=scan_id,
                filename=filename[:55],
                page_num=i + 2,
                total=total_pages,
            )

        summary_doc.insert_pdf(heatmap_doc)
        heatmap_doc.close()
        summary_doc.save(str(output_path), garbage=4, deflate=True)
        summary_doc.close()

    return output_path