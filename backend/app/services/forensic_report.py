"""
forensic_report.py — Phase 4 (single-page forensic summary + heatmap resume)
=============================================================================
Generates a professional forensic evidence PDF.

Layout
------
  Page 1  — Forensic Summary drawn entirely on the canvas (guaranteed 1 page).
             Contains: banner, metadata, trust gauge, KPI stat boxes,
             severity summary table, fraud signals table (capped/truncated to
             fit), hidden words table (if present), executive briefing snippet.

  Page 2+ — The heatmap-annotated original resume appended via
             fitz.insert_pdf().  All original pages preserved in order.

Strategy: Page 1 is drawn with pure ReportLab canvas calls, never using
Platypus flowables that can reflow across pages.  All tables on Page 1 are
rendered as raw canvas rectangles + text, with automatic row-height scaling
so the content always fits in the available vertical space.

Uses ReportLab (canvas) + PyMuPDF (fitz) — both already in requirements.txt.
"""
from __future__ import annotations

import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

from app.services.heatmap_generator import generate_heatmap

# ── Brand colours ────────────────────────────────────────────────────────────
GREEN   = (16/255,  185/255, 129/255)   # #10B981
AMBER   = (245/255, 158/255,  11/255)   # #F59E0B
RED_C   = (239/255,  68/255,  68/255)   # #EF4444
CYAN_C  = (  6/255, 182/255, 212/255)   # #06B6D4

BG_DARK = (13/255,  15/255,  20/255)    # #0D0F14
BG_CARD = (17/255,  19/255,  24/255)    # #111318
BG_ELEV = (26/255,  29/255,  38/255)    # #1A1D26
BORDER  = (42/255,  48/255,  64/255)    # #2A3040
T_PRI   = (244/255, 245/255, 247/255)   # #F4F5F7
T_SEC   = (160/255, 166/255, 180/255)   # #A0A6B4
WHITE   = (1.0, 1.0, 1.0)

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

PAGE_W, PAGE_H = letter   # 612 × 792 pt


# ── Low-level canvas helpers ─────────────────────────────────────────────────

def _rgb(c: rl_canvas.Canvas, color: tuple) -> None:
    c.setFillColorRGB(*color)

def _stroke(c: rl_canvas.Canvas, color: tuple) -> None:
    c.setStrokeColorRGB(*color)

def _rect_fill(c, x, y, w, h, color, radius=0):
    _rgb(c, color)
    if radius:
        c.roundRect(x, y, w, h, radius, fill=1, stroke=0)
    else:
        c.rect(x, y, w, h, fill=1, stroke=0)

def _draw_gauge(c, cx: float, cy: float, r: float, score: float, label: str) -> None:
    """Semi-circular arc gauge."""
    badge_color = TRUST_COLORS.get(label, T_SEC)

    # Track arc
    _stroke(c, BORDER)
    c.setLineWidth(7)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # Progress arc
    if score > 0:
        extent = 180.0 * (score / 100.0)
        _stroke(c, badge_color)
        c.setLineWidth(7)
        c.arc(cx - r, cy - r, cx + r, cy + r, startAng=180 - extent, extent=extent)

    # Score number
    _rgb(c, badge_color)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(cx, cy + 2, f"{score:.0f}")
    _rgb(c, T_SEC)
    c.setFont("Helvetica", 7)
    c.drawCentredString(cx, cy - 9, "/100")
    _rgb(c, badge_color)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(cx, cy - 20, label.upper())


def _stat_box(c, x: float, y: float, w: float, h: float,
              value: str, label: str, color: tuple) -> None:
    _rect_fill(c, x, y, w, h, BG_ELEV, radius=3)
    _rect_fill(c, x, y + h - 2, w, 2, color)
    _rgb(c, color)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(x + w / 2, y + h - 20, value)
    _rgb(c, T_SEC)
    c.setFont("Helvetica", 6)
    c.drawCentredString(x + w / 2, y + 5, label)


def _draw_mini_table(
    c,
    x: float, y_top: float,
    col_widths: list[float],
    headers: list[str],
    rows: list[list[str]],
    row_h: float = 14.0,
    font_size: float = 7.0,
    max_rows: int | None = None,
    col_colors: dict[int, dict[str, tuple]] | None = None,
) -> float:
    """
    Draw a compact table entirely via canvas calls.
    Returns the y coordinate of the bottom of the table.

    col_colors: {col_index: {"header": color, "cells": [(row_index, color), ...]}}
    """
    if col_colors is None:
        col_colors = {}

    # Clamp rows to max_rows
    display_rows = rows if max_rows is None else rows[:max_rows]
    truncated = max_rows is not None and len(rows) > max_rows

    total_w = sum(col_widths)
    header_h = row_h + 2

    # Header background
    _rect_fill(c, x, y_top - header_h, total_w, header_h, BG_ELEV)

    # Header text
    cx_pos = x
    for ci, (hdr, cw) in enumerate(zip(headers, col_widths)):
        color = col_colors.get(ci, {}).get("header", T_SEC)
        _rgb(c, color)
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(cx_pos + 3, y_top - header_h + 4, hdr[:int(cw / (font_size * 0.55))])
        cx_pos += cw

    y = y_top - header_h

    for ri, row in enumerate(display_rows):
        bg = BG_CARD if ri % 2 == 0 else (13/255, 15/255, 20/255)
        _rect_fill(c, x, y - row_h, total_w, row_h, bg)

        cx_pos = x
        for ci, (cell, cw) in enumerate(zip(row, col_widths)):
            # per-cell colour overrides
            cell_color_map = col_colors.get(ci, {}).get("cells", [])
            cell_clr = T_PRI
            for (r_idx, clr) in cell_color_map:
                if r_idx == ri:
                    cell_clr = clr
                    break

            _rgb(c, cell_clr)
            max_chars = max(1, int(cw / (font_size * 0.52)))
            text = str(cell)[:max_chars]
            c.setFont("Helvetica", font_size)
            c.drawString(cx_pos + 3, y - row_h + 4, text)
            cx_pos += cw

        y -= row_h

    if truncated:
        _rgb(c, T_SEC)
        c.setFont("Helvetica-Oblique", 6)
        c.drawString(x + 3, y - 2, f"… {len(rows) - max_rows} more rows omitted — see full signals list above")
        y -= 10

    # Border around entire table
    _stroke(c, BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y, total_w, y_top - y, fill=0, stroke=1)

    return y


# ── Main public function ─────────────────────────────────────────────────────

def generate_forensic_report(
    scan_result: dict,
    original_pdf_path: Path,
    output_path: Path,
) -> Path:
    """
    Build the forensic evidence PDF and write it to output_path.

    Page 1  = Single-page forensic summary (always exactly 1 page).
    Page 2+ = Heatmap-annotated resume pages (all original pages preserved).

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

    trust    = scan_result.get("trust_score") or {}
    t_score  = float(trust.get("score") or 0)
    t_label  = trust.get("label", "Unknown")
    badge_color = TRUST_COLORS.get(t_label, T_SEC)

    fraud    = scan_result.get("fraud_summary", {})
    signals  = fraud.get("signals", [])
    ai_score = scan_result.get("ai_content_score")
    match_s  = scan_result.get("true_match_score")
    narrative = scan_result.get("narrative") or {}
    hidden_words = scan_result.get("hidden_words", []) or []

    # ── Step 1: draw Page 1 forensic summary via ReportLab canvas ────────────
    summary_buf = io.BytesIO()
    c = rl_canvas.Canvas(summary_buf, pagesize=letter)

    LM = 0.5 * inch    # left margin
    RM = 0.5 * inch    # right margin
    BM = 0.4 * inch    # bottom margin
    CONTENT_W = PAGE_W - LM - RM   # 7.5 inch

    # ── Banner ───────────────────────────────────────────────────────────────
    BANNER_H = 0.80 * inch
    _rect_fill(c, 0, PAGE_H - BANNER_H, PAGE_W, BANNER_H, BG_DARK)
    _rect_fill(c, 0, PAGE_H - BANNER_H, PAGE_W, 2.5, badge_color)  # accent line

    _rgb(c, T_PRI)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(LM, PAGE_H - 0.40 * inch, "ATS Fraud Detector")
    _rgb(c, T_SEC)
    c.setFont("Helvetica", 9)
    c.drawString(LM, PAGE_H - 0.60 * inch, "FORENSIC EVIDENCE REPORT")

    # Verdict stamp (top-right)
    stamp = t_label.upper()
    sw = len(stamp) * 6 + 14
    bx = PAGE_W - RM - sw
    _rect_fill(c, bx, PAGE_H - 0.65 * inch, sw, 18, badge_color, radius=3)
    _rgb(c, WHITE)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(bx + sw / 2, PAGE_H - 0.54 * inch, stamp)

    # Report generated timestamp (top-right, below stamp)
    _rgb(c, T_SEC)
    c.setFont("Helvetica", 6)
    c.drawRightString(PAGE_W - RM, PAGE_H - 0.76 * inch, f"Generated: {generated_at}")

    # ── Metadata strip ───────────────────────────────────────────────────────
    meta_y = PAGE_H - BANNER_H - 0.06 * inch
    fields = [
        ("Scan ID",   str(scan_result.get("scan_id", "—"))),
        ("File",      str(scan_result.get("filename", "—"))[:60]),
        ("SHA-256",   str(scan_result.get("sha256", "—"))[:52] + "…"),
        ("Pages",     str(scan_result.get("page_count", "—"))),
        ("Scanned",   str(scan_result.get("scanned_at") or generated_at)[:30]),
    ]
    field_h = 0.175 * inch
    _rect_fill(c, LM, meta_y - len(fields) * field_h, CONTENT_W, len(fields) * field_h, BG_ELEV)
    for i, (key, val) in enumerate(fields):
        ry = meta_y - i * field_h
        if i % 2 == 1:
            _rect_fill(c, LM, ry - field_h, CONTENT_W, field_h, BG_CARD)
        _rgb(c, T_SEC)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(LM + 4, ry - field_h + 4, key)
        _rgb(c, T_PRI)
        c.setFont("Courier", 6.5)
        c.drawString(LM + 1.1 * inch, ry - field_h + 4, val)

    meta_bottom = meta_y - len(fields) * field_h - 0.06 * inch

    # ── Trust gauge + stat boxes (side by side) ───────────────────────────────
    gauge_r  = 0.52 * inch
    gauge_cx = LM + gauge_r + 0.05 * inch
    gauge_cy = meta_bottom - gauge_r - 0.30 * inch
    _draw_gauge(c, gauge_cx, gauge_cy, gauge_r, t_score, t_label)

    # Three stat boxes to the right of gauge
    box_h   = gauge_r * 2 + 0.20 * inch   # match gauge height
    box_w   = 1.35 * inch
    box_gap = 0.12 * inch
    stat_x  = gauge_cx + gauge_r + 0.22 * inch

    hs = fraud.get("high", 0)
    hs_color = RED_C if hs > 0 else GREEN
    ai_val   = f"{ai_score:.1f}" if ai_score is not None else "—"
    ai_color = RED_C if (ai_score or 0) >= 70 else (AMBER if (ai_score or 0) >= 40 else GREEN)
    ms_val   = f"{match_s:.1f}" if match_s is not None else "—"
    tot_val  = str(fraud.get("total", 0))

    _stat_box(c, stat_x,                       gauge_cy - box_h / 2, box_w, box_h, str(hs),   "HIGH SIGNALS", hs_color)
    _stat_box(c, stat_x + box_w + box_gap,     gauge_cy - box_h / 2, box_w, box_h, tot_val,   "TOTAL SIGNALS", AMBER)
    _stat_box(c, stat_x + 2*(box_w + box_gap), gauge_cy - box_h / 2, box_w, box_h, ai_val,    "AI CONTENT %",  ai_color)
    _stat_box(c, stat_x + 3*(box_w + box_gap), gauge_cy - box_h / 2, box_w, box_h, ms_val,    "JOB MATCH %",   CYAN_C)

    # Executive briefing snippet (right column, beside gauge area)
    rec = (narrative.get("recommendation") or "")[:200]
    if rec:
        brief_x = stat_x + 4 * (box_w + box_gap) + 0.1 * inch
        brief_w = PAGE_W - RM - brief_x
        if brief_w > 0.8 * inch:
            brief_y_top = gauge_cy + gauge_r + 0.05 * inch
            _rect_fill(c, brief_x, gauge_cy - gauge_r, brief_w,
                       brief_y_top - (gauge_cy - gauge_r), BG_ELEV, radius=3)
            _rect_fill(c, brief_x, brief_y_top - 2, brief_w, 2, badge_color)
            _rgb(c, badge_color)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawString(brief_x + 4, brief_y_top - 10, "RECOMMENDATION")
            _rgb(c, T_PRI)
            c.setFont("Helvetica", 6)
            # Word-wrap the recommendation text
            words = rec.split()
            line, lines_out = [], []
            for w in words:
                test = " ".join(line + [w])
                if c.stringWidth(test, "Helvetica", 6) < brief_w - 8:
                    line.append(w)
                else:
                    if line:
                        lines_out.append(" ".join(line))
                    line = [w]
                if len(lines_out) >= 5:
                    break
            if line and len(lines_out) < 5:
                lines_out.append(" ".join(line))
            for li, ln in enumerate(lines_out):
                c.drawString(brief_x + 4, brief_y_top - 22 - li * 8, ln)

    section_y = gauge_cy - gauge_r - 0.18 * inch

    # ── Section divider helper ────────────────────────────────────────────────
    def _section_label(label: str, y: float) -> float:
        _rgb(c, CYAN_C)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(LM, y, label)
        _stroke(c, BORDER)
        c.setLineWidth(0.4)
        c.line(LM + c.stringWidth(label, "Helvetica-Bold", 6.5) + 4, y + 2,
               PAGE_W - RM, y + 2)
        return y - 0.12 * inch

    # ── Signals table ─────────────────────────────────────────────────────────
    section_y = _section_label("DETECTED FRAUD SIGNALS", section_y)

    # Budget the available height: reserve space for hidden words if present
    # and for footer. We compute a max_row count dynamically.
    FOOTER_RESERVE = BM + 0.15 * inch
    HW_RESERVE = 0 if not hidden_words else (
        0.22 * inch + (len(hidden_words[:6]) + 1) * 12 + 0.10 * inch
    )

    sig_table_h_budget = section_y - FOOTER_RESERVE - HW_RESERVE - 0.20 * inch
    sig_row_h = 12.0
    sig_header_h = sig_row_h + 2
    max_sig_rows = max(0, int((sig_table_h_budget - sig_header_h) / sig_row_h))

    sig_col_w = [
        0.45 * inch,  # Sev
        1.20 * inch,  # Type
        0.28 * inch,  # Pg
        2.55 * inch,  # Description
        3.02 * inch,  # Evidence
    ]

    if signals:
        sig_rows = []
        sig_col_colors: dict[int, dict] = {0: {"header": T_SEC, "cells": []}}
        for ri, s in enumerate(signals):
            sev = s.get("severity", "low")
            sev_color = SEV_COLORS.get(sev, T_SEC)
            sig_col_colors[0]["cells"].append((ri, sev_color))
            sig_rows.append([
                sev.upper(),
                s.get("signal_type", "—").replace("_", " "),
                str(s.get("page", "—")),
                s.get("description", "")[:120],
                (s.get("evidence_text") or "")[:90],
            ])

        section_y = _draw_mini_table(
            c, LM, section_y,
            col_widths=sig_col_w,
            headers=["SEV", "SIGNAL TYPE", "PG", "DESCRIPTION", "EVIDENCE"],
            rows=sig_rows,
            row_h=sig_row_h,
            font_size=6.5,
            max_rows=max_sig_rows,
            col_colors=sig_col_colors,
        )
    else:
        _rgb(c, GREEN)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(LM, section_y - 10, "✓  No fraud signals detected.")
        section_y -= 18

    section_y -= 0.10 * inch

    # ── Hidden Words table ────────────────────────────────────────────────────
    if hidden_words:
        section_y = _section_label("HIDDEN WORDS DETECTED", section_y)

        hw_col_w = [3.40 * inch, 0.40 * inch, 0.65 * inch, 3.05 * inch]
        hw_rows = []
        hw_col_colors: dict[int, dict] = {2: {"header": T_SEC, "cells": []}}
        for ri, hw in enumerate(hidden_words):
            sev = str(hw.get("severity", "low")).lower()
            sev_color = SEV_COLORS.get(sev, T_SEC)
            hw_col_colors[2]["cells"].append((ri, sev_color))
            hidden_text = str(hw.get("text") or hw.get("hidden_text") or hw.get("word") or "—")
            hw_rows.append([
                hidden_text[:80],
                str(hw.get("page", "—")),
                sev.upper(),
                str(hw.get("signal_type") or hw.get("type") or "—").replace("_", " "),
            ])

        # Remaining height for the hidden words table
        hw_h_budget = section_y - FOOTER_RESERVE
        hw_max = max(0, int((hw_h_budget - 14) / 12))

        section_y = _draw_mini_table(
            c, LM, section_y,
            col_widths=hw_col_w,
            headers=["HIDDEN TEXT", "PG", "SEV", "SIGNAL TYPE"],
            rows=hw_rows,
            row_h=12.0,
            font_size=6.5,
            max_rows=hw_max,
            col_colors=hw_col_colors,
        )

    # ── Footer ────────────────────────────────────────────────────────────────
    _stroke(c, BORDER)
    c.setLineWidth(0.4)
    c.line(LM, BM, PAGE_W - RM, BM)
    _rgb(c, T_SEC)
    c.setFont("Helvetica", 6)
    c.drawString(LM, BM - 9, "CONFIDENTIAL — FOR AUTHORIZED RECRUITER USE ONLY")
    c.drawRightString(PAGE_W - RM, BM - 9, "ATS Fraud Detector © 2026  |  Page 1")

    c.showPage()
    c.save()
    summary_buf.seek(0)

    # ── Step 2: generate heatmap-annotated resume PDF ─────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        heatmap_path = Path(tmpdir) / "heatmap.pdf"
        generate_heatmap(original_pdf_path, signals, heatmap_path)

        # ── Step 3: merge with fitz ───────────────────────────────────────────
        # Open the single-page forensic summary from the in-memory buffer
        summary_doc = fitz.open(stream=summary_buf.read(), filetype="pdf")
        heatmap_doc = fitz.open(str(heatmap_path))

        # Append heatmap resume pages after the summary page
        summary_doc.insert_pdf(heatmap_doc)

        heatmap_doc.close()
        summary_doc.save(str(output_path), garbage=4, deflate=True)
        summary_doc.close()

    return output_path