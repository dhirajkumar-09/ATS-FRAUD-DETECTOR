"""
forensic_report.py — Phase 4 (redesigned for hackathon demo)
=============================================================
Generates a professional "evidence" PDF for a completed scan.

Layout
------
  1. Cover page  — title banner, metadata table, Trust Score arc gauge
                   (drawn via canvas.arc), three sub-score stat boxes.
  2. Executive Forensic Briefing — shaded callout box with left accent line.
  3. Detected Fraud Signals table — alternating rows, severity-coded cell
     tints, NOSPLIT so no row splits across a page break.
  4. Annotated heatmap pages — a colour legend box, then each heatmap page
     as an embedded PNG with a short caption below it.

Header / footer on every page:
  Left  → "ATS Fraud Detector — Forensic Evidence Report"
  Right → "Page X of Y  |  Generated: <timestamp>"

Brand colours match frontend/app.py CSS vars exactly:
  --green  #10B981   --amber  #F59E0B   --red  #EF4444

Uses ReportLab only (pure-Python, no system-level deps).
"""
from __future__ import annotations

import io
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable

from app.services.heatmap_generator import generate_heatmap, render_page_images

# ── Brand colours (exact match with frontend/app.py CSS) ────────────────────
GREEN   = colors.HexColor("#10B981")   # --green
AMBER   = colors.HexColor("#F59E0B")   # --amber
RED     = colors.HexColor("#EF4444")   # --red

# Light tints for alternating table rows
GREEN_TINT = colors.HexColor("#ecfdf5")
AMBER_TINT = colors.HexColor("#fffbeb")
RED_TINT   = colors.HexColor("#fef2f2")

# Background tones
BG_DARK    = colors.HexColor("#0D0F14")   # --bg-secondary
BG_CARD    = colors.HexColor("#111318")   # --bg-card
BG_ELEV    = colors.HexColor("#1A1D26")   # --bg-elevated
BORDER_CLR = colors.HexColor("#2A3040")   # --border-bright
TEXT_PRI   = colors.HexColor("#F4F5F7")   # --text-primary
TEXT_SEC   = colors.HexColor("#A0A6B4")   # --text-secondary

SEVERITY_ROW_COLORS = {
    "high":   RED_TINT,
    "medium": AMBER_TINT,
    "low":    GREEN_TINT,
}

TRUST_LABEL_COLORS = {
    "Verified":  GREEN,
    "Caution":   AMBER,
    "High Risk": RED,
}

PAGE_W, PAGE_H = letter
LEFT_MARGIN = RIGHT_MARGIN = 0.75 * inch
TOP_MARGIN    = 1.0 * inch
BOTTOM_MARGIN = 0.85 * inch


# ── Header / footer canvas callbacks ────────────────────────────────────────

def _make_header_footer(generated_at: str):
    """Return (on_first_page, on_later_pages) callbacks for SimpleDocTemplate."""

    def _draw(canvas, doc):
        canvas.saveState()
        page_num   = doc.page
        page_total = getattr(doc, "_pageCount", "?")

        # ── Top rule ──────────────────────────────────────────────────────
        y_top = PAGE_H - 0.55 * inch
        canvas.setStrokeColor(BORDER_CLR)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_MARGIN, y_top, PAGE_W - RIGHT_MARGIN, y_top)

        # Left: report title
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(TEXT_SEC)
        canvas.drawString(LEFT_MARGIN, y_top + 5, "ATS Fraud Detector — Forensic Evidence Report")

        # Right: page + timestamp
        right_text = f"Page {page_num}  |  {generated_at}"
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(PAGE_W - RIGHT_MARGIN, y_top + 5, right_text)

        # ── Bottom rule ───────────────────────────────────────────────────
        y_bot = 0.50 * inch
        canvas.setStrokeColor(BORDER_CLR)
        canvas.line(LEFT_MARGIN, y_bot, PAGE_W - RIGHT_MARGIN, y_bot)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(TEXT_SEC)
        canvas.drawString(LEFT_MARGIN, y_bot - 10, "CONFIDENTIAL — FOR AUTHORIZED RECRUITER USE ONLY")
        canvas.drawRightString(PAGE_W - RIGHT_MARGIN, y_bot - 10, "ATS Fraud Detector © 2026")

        canvas.restoreState()

    return _draw, _draw


# ── Trust Score arc gauge (drawn on the canvas directly) ────────────────────

def _draw_gauge(canvas, cx: float, cy: float, r: float,
                score: float, label: str) -> None:
    """
    Draw a semicircular arc gauge centred at (cx, cy) with radius r.
    The arc spans from 180° to 0° (left-to-right across the top half),
    and fills proportionally to score/100.
    """
    badge_color = TRUST_LABEL_COLORS.get(label, colors.HexColor("#555555"))

    # Track arc (grey)
    canvas.setStrokeColor(colors.HexColor("#2A3040"))
    canvas.setLineWidth(8)
    canvas.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # Progress arc (brand colour)
    if score > 0:
        extent = 180.0 * (score / 100.0)
        canvas.setStrokeColor(badge_color)
        canvas.setLineWidth(8)
        canvas.arc(cx - r, cy - r, cx + r, cy + r, startAng=180 - extent, extent=extent)

    # Score number
    canvas.setFillColor(badge_color)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawCentredString(cx, cy + 4, f"{score:.0f}")

    # "/100" subscript
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(TEXT_SEC)
    canvas.drawCentredString(cx, cy - 10, "/100")

    # Label below gauge
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(badge_color)
    canvas.drawCentredString(cx, cy - 24, label.upper())


# ── Sub-score stat box helper ────────────────────────────────────────────────

def _stat_box(canvas, x: float, y: float, w: float, h: float,
              value: str, label: str, accent: colors.Color) -> None:
    """Draw a labelled KPI box at (x, y) with width w and height h."""
    # Background
    canvas.setFillColor(BG_ELEV)
    canvas.roundRect(x, y, w, h, 4, fill=1, stroke=0)
    # Accent top border
    canvas.setFillColor(accent)
    canvas.rect(x, y + h - 3, w, 3, fill=1, stroke=0)
    # Value
    canvas.setFillColor(accent)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(x + w / 2, y + h - 26, value)
    # Label
    canvas.setFillColor(TEXT_SEC)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(x + w / 2, y + 6, label)


# ── Cover page canvas callback ───────────────────────────────────────────────

def _make_cover_page(scan_result: dict, generated_at: str):
    """Return an onFirstPage callback that draws the entire cover page."""

    def _draw_cover(canvas, doc):
        canvas.saveState()

        trust   = scan_result.get("trust_score") or {}
        t_score = float(trust.get("score") or 0)
        t_label = trust.get("label", "Unknown")
        badge_color = TRUST_LABEL_COLORS.get(t_label, colors.HexColor("#555555"))
        fraud   = scan_result.get("fraud_summary", {})
        ai_score = scan_result.get("ai_content_score")
        match_s  = scan_result.get("true_match_score")

        # ── Dark title banner ─────────────────────────────────────────────
        banner_h = 1.4 * inch
        canvas.setFillColor(BG_DARK)
        canvas.rect(0, PAGE_H - banner_h, PAGE_W, banner_h, fill=1, stroke=0)

        # Accent line at bottom of banner
        canvas.setFillColor(badge_color)
        canvas.rect(0, PAGE_H - banner_h, PAGE_W, 3, fill=1, stroke=0)

        canvas.setFillColor(TEXT_PRI)
        canvas.setFont("Helvetica-Bold", 20)
        canvas.drawString(LEFT_MARGIN, PAGE_H - 0.65 * inch,
                          "ATS Fraud Detector")
        canvas.setFont("Helvetica", 11)
        canvas.setFillColor(TEXT_SEC)
        canvas.drawString(LEFT_MARGIN, PAGE_H - 0.90 * inch,
                          "FORENSIC EVIDENCE REPORT")

        # Badge stamp (top-right)
        stamp_text = t_label.upper()
        canvas.setFillColor(badge_color)
        sw = len(stamp_text) * 6.5 + 16
        bx = PAGE_W - RIGHT_MARGIN - sw
        canvas.roundRect(bx, PAGE_H - 0.85 * inch, sw, 20, 4, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(bx + sw / 2, PAGE_H - 0.74 * inch, stamp_text)

        # ── Metadata section ──────────────────────────────────────────────
        meta_y = PAGE_H - banner_h - 0.35 * inch
        fields = [
            ("Scan ID",          str(scan_result.get("scan_id", "—"))),
            ("Filename",         str(scan_result.get("filename", "—"))),
            ("SHA-256",          str(scan_result.get("sha256", "—"))[:48] + "…"),
            ("Pages",            str(scan_result.get("page_count", "—"))),
            ("Scanned At",       str(scan_result.get("scanned_at") or generated_at)),
            ("Report Generated", generated_at),
        ]
        col1_x = LEFT_MARGIN
        col2_x = LEFT_MARGIN + 1.3 * inch
        row_h   = 0.22 * inch
        for i, (key, val) in enumerate(fields):
            ry = meta_y - i * row_h
            canvas.setFillColor(BG_ELEV)
            canvas.rect(col1_x, ry - 2, 6.5 * inch, row_h - 1, fill=1, stroke=0)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(TEXT_SEC)
            canvas.drawString(col1_x + 4, ry + 5, key)
            canvas.setFont("Courier", 8)
            canvas.setFillColor(TEXT_PRI)
            canvas.drawString(col2_x + 4, ry + 5, val)

        # ── Trust Score gauge ─────────────────────────────────────────────
        gauge_cx = LEFT_MARGIN + 0.85 * inch
        gauge_cy = meta_y - len(fields) * row_h - 1.25 * inch
        _draw_gauge(canvas, gauge_cx, gauge_cy, r=0.65 * inch,
                    score=t_score, label=t_label)

        # ── Sub-score stat boxes ──────────────────────────────────────────
        box_y  = gauge_cy - 0.5 * inch
        box_h  = 0.85 * inch
        box_w  = 1.55 * inch
        box_gap = 0.18 * inch
        stat_x = LEFT_MARGIN + 1.9 * inch

        high_signals = fraud.get("high", 0)
        hs_color = RED if high_signals > 0 else GREEN

        ai_val = f"{ai_score:.1f}" if ai_score is not None else "—"
        ai_color = RED if (ai_score or 0) >= 70 else (AMBER if (ai_score or 0) >= 40 else GREEN)

        ms_val = f"{match_s:.1f}" if match_s is not None else "—"
        ms_color = colors.HexColor("#06B6D4")  # cyan

        _stat_box(canvas, stat_x,                    box_y, box_w, box_h,
                  str(high_signals), "HIGH SIGNALS", hs_color)
        _stat_box(canvas, stat_x + box_w + box_gap,  box_y, box_w, box_h,
                  ai_val, "AI CONTENT %", ai_color)
        _stat_box(canvas, stat_x + 2*(box_w + box_gap), box_y, box_w, box_h,
                  ms_val, "JOB MATCH %", ms_color)

        # ── Header / footer ───────────────────────────────────────────────
        # (Cover page gets a simplified header — no "Page X of Y")
        y_top = PAGE_H - 0.30 * inch
        canvas.setStrokeColor(BORDER_CLR)
        canvas.setLineWidth(0.4)
        canvas.line(LEFT_MARGIN, y_top, PAGE_W - RIGHT_MARGIN, y_top)

        y_bot = 0.50 * inch
        canvas.line(LEFT_MARGIN, y_bot, PAGE_W - RIGHT_MARGIN, y_bot)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(TEXT_SEC)
        canvas.drawString(LEFT_MARGIN, y_bot - 10,
                          "CONFIDENTIAL — FOR AUTHORIZED RECRUITER USE ONLY")
        canvas.drawRightString(PAGE_W - RIGHT_MARGIN, y_bot - 10,
                               "ATS Fraud Detector © 2026")

        canvas.restoreState()

    return _draw_cover


# ── Heatmap legend flowable ──────────────────────────────────────────────────

def _heatmap_legend() -> Table:
    """Return a styled Table that serves as the heatmap colour legend."""
    legend_data = [
        ["", "Colour", "Severity",    "Meaning"],
        ["", "■ Red",   "High",       "Deliberate ATS evasion / tampering — immediate review required"],
        ["", "■ Orange","Medium",     "Formatting anomaly or timeline inconsistency — warrants verification"],
        ["", "■ Yellow","Low",        "Minor irregularity — low risk, log for reference"],
    ]
    swatch_colors = [None, RED, AMBER, colors.HexColor("#F0C040")]

    tbl = Table(
        legend_data,
        colWidths=[0.1 * inch, 0.85 * inch, 0.7 * inch, 4.85 * inch],
    )

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BG_ELEV),
        ("TEXTCOLOR",  (0, 0), (-1, 0), TEXT_SEC),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_CARD, BG_ELEV]),
        ("GRID",       (0, 0), (-1, -1), 0.3, BORDER_CLR),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ]
    # Colour the swatch cells
    for i, sc in enumerate(swatch_colors):
        if sc is not None:
            style_cmds.append(("TEXTCOLOR", (1, i), (1, i), sc))
            style_cmds.append(("FONTNAME",  (1, i), (1, i), "Helvetica-Bold"))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ── Executive Briefing callout box ───────────────────────────────────────────

def _briefing_callout(narrative: dict, label: str, body_style: ParagraphStyle) -> Table:
    """
    Wrap the executive briefing text in a shaded callout box with a
    left accent line colour-coded by trust verdict.
    """
    accent = TRUST_LABEL_COLORS.get(label, colors.HexColor("#555555"))

    rec_text = narrative.get("recommendation", "")
    factors  = narrative.get("key_factors", [])[:4]
    discl    = narrative.get("limitations_disclaimer", "")

    # Build inner content as a single-cell table
    inner_style = ParagraphStyle(
        "CalloutBody", parent=body_style,
        fontSize=8.5, leading=13, textColor=TEXT_PRI,
    )
    heading_style = ParagraphStyle(
        "CalloutHeading", parent=body_style,
        fontSize=10, fontName="Helvetica-Bold",
        textColor=accent, spaceAfter=4,
    )
    note_style = ParagraphStyle(
        "CalloutNote", parent=body_style,
        fontSize=7.5, textColor=TEXT_SEC, leading=11, spaceBefore=6,
    )

    paras = [Paragraph("Executive Forensic Briefing", heading_style)]
    if rec_text:
        paras.append(Paragraph(f"<b>Recommendation:</b> {rec_text}", inner_style))
        paras.append(Spacer(1, 0.06 * inch))
    for factor in factors:
        paras.append(Paragraph(f"• {factor}", inner_style))
    if discl:
        paras.append(Paragraph(discl, note_style))

    # Left accent strip
    accent_strip_data = [["", paras]]
    callout = Table(
        accent_strip_data,
        colWidths=[0.12 * inch, 5.88 * inch],
    )
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), accent),
        ("BACKGROUND", (1, 0), (1, 0), BG_ELEV),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (1, 0), (1, 0), 10),
        ("BOTTOMPADDING", (1, 0), (1, 0), 10),
        ("LEFTPADDING",   (1, 0), (1, 0), 10),
        ("RIGHTPADDING",  (1, 0), (1, 0), 10),
        ("BOX",        (0, 0), (-1, -1), 0.5, BORDER_CLR),
    ]))
    return callout


# ── Main public function ─────────────────────────────────────────────────────

def generate_forensic_report(
    scan_result: dict,
    original_pdf_path: Path,
    output_path: Path,
) -> Path:
    """
    Build the forensic evidence PDF and write it to output_path.

    Parameters
    ----------
    scan_result : dict shaped like the /scan/{id} response, expecting at
        least: scan_id, filename, sha256, scanned_at (iso str, optional),
        page_count, fraud_summary {total, high, medium, low, signals: [...]},
        ai_content_score (optional), true_match_score (optional).
    original_pdf_path : Path to the original uploaded PDF on disk.
    output_path : where to write the generated report PDF.

    Returns
    -------
    Path to the generated report (same as output_path).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    scanned_at   = scan_result.get("scanned_at") or generated_at

    # ── 1. Render heatmap pages to PNG blobs ───────────────────────────────
    signals = scan_result.get("fraud_summary", {}).get("signals", [])
    with tempfile.TemporaryDirectory() as tmpdir:
        heatmap_path = Path(tmpdir) / "heatmap.pdf"
        generate_heatmap(original_pdf_path, signals, heatmap_path)
        page_images = render_page_images(heatmap_path, dpi=120)

        # ── 2. Build callbacks ─────────────────────────────────────────────
        on_first_page  = _make_cover_page(scan_result, generated_at)
        on_later_pages, _ = _make_header_footer(generated_at)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            topMargin=TOP_MARGIN,
            bottomMargin=BOTTOM_MARGIN,
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN,
        )

        # ── 3. Styles ──────────────────────────────────────────────────────
        styles      = getSampleStyleSheet()
        body_style  = ParagraphStyle(
            "Body", parent=styles["BodyText"],
            fontSize=9, leading=14, textColor=TEXT_PRI,
        )
        h2_style    = ParagraphStyle(
            "H2", parent=styles["Heading2"],
            fontSize=12, textColor=TEXT_PRI, fontName="Helvetica-Bold",
            spaceBefore=14, spaceAfter=6,
        )
        mono_style  = ParagraphStyle(
            "Mono", parent=body_style, fontName="Courier", fontSize=8,
            textColor=TEXT_SEC,
        )
        caption_style = ParagraphStyle(
            "Caption", parent=body_style,
            fontSize=7.5, textColor=TEXT_SEC, alignment=1,  # centred
        )

        story: list = []

        # ── 4. Cover page placeholder ──────────────────────────────────────
        # The actual cover content is drawn by _draw_cover via onFirstPage;
        # we push the story to page 2 onward.  A tall Spacer reserves the
        # visible area of page 1 so Platypus doesn't render flowables over it.
        cover_space_h = PAGE_H - TOP_MARGIN - BOTTOM_MARGIN - 0.5 * inch
        story.append(Spacer(1, cover_space_h))
        story.append(PageBreak())

        # ── 5. Executive Forensic Briefing callout ─────────────────────────
        narrative = scan_result.get("narrative")
        trust     = scan_result.get("trust_score") or {}
        t_label   = trust.get("label", "Unknown")

        if narrative:
            story.append(_briefing_callout(narrative, t_label, body_style))
            story.append(Spacer(1, 0.25 * inch))

        # ── 6. Severity summary table ──────────────────────────────────────
        fraud = scan_result.get("fraud_summary", {})
        story.append(Paragraph("Severity Summary", h2_style))
        ai_s  = scan_result.get("ai_content_score")
        ms_s  = scan_result.get("true_match_score")
        summary_rows = [
            ["Total", "High", "Medium", "Low", "AI Content", "Match Score"],
            [
                str(fraud.get("total", 0)),
                str(fraud.get("high", 0)),
                str(fraud.get("medium", 0)),
                str(fraud.get("low", 0)),
                f"{ai_s:.1f}" if ai_s is not None else "—",
                f"{ms_s:.1f}" if ms_s is not None else "—",
            ],
        ]
        summary_tbl = Table(summary_rows, colWidths=[0.9 * inch] * 6)
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), BG_ELEV),
            ("TEXTCOLOR",   (0, 0), (-1, 0), TEXT_SEC),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",    (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("GRID",        (0, 0), (-1, -1), 0.4, BORDER_CLR),
            ("BACKGROUND",  (0, 1), (-1, 1), BG_CARD),
            ("TEXTCOLOR",   (1, 1), (1, 1), RED),    # High col
            ("TEXTCOLOR",   (2, 1), (2, 1), AMBER),  # Medium col
            ("TEXTCOLOR",   (3, 1), (3, 1), GREEN),  # Low col
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 0.3 * inch))

        # ── 7. Signal detail table ─────────────────────────────────────────
        story.append(Paragraph("Detected Fraud Signals", h2_style))

        if signals:
            header_row = [
                Paragraph("<b>Sev</b>", body_style),
                Paragraph("<b>Signal Type</b>", body_style),
                Paragraph("<b>Pg</b>", body_style),
                Paragraph("<b>Description</b>", body_style),
                Paragraph("<b>Evidence</b>", body_style),
            ]
            sig_rows = [header_row]
            for s in signals:
                sig_rows.append([
                    Paragraph(s.get("severity", "—").upper(), body_style),
                    Paragraph(
                        s.get("signal_type", "—").replace("_", " "),
                        body_style,
                    ),
                    Paragraph(str(s.get("page", "—")), body_style),
                    Paragraph(s.get("description", "")[:220], body_style),
                    Paragraph((s.get("evidence_text") or "")[:120], mono_style),
                ])

            sig_tbl = Table(
                sig_rows,
                colWidths=[0.6 * inch, 1.35 * inch, 0.35 * inch, 2.5 * inch, 1.7 * inch],
                repeatRows=1,
            )

            style_cmds = [
                # Header row
                ("BACKGROUND",  (0, 0), (-1, 0), BG_ELEV),
                ("TEXTCOLOR",   (0, 0), (-1, 0), TEXT_SEC),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 8),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("GRID",        (0, 0), (-1, -1), 0.3, BORDER_CLR),
                ("TOPPADDING",  (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                # NOSPLIT — keep each body row together
                ("NOSPLIT",     (0, 1), (-1, -1)),
            ]
            for i, s in enumerate(signals, start=1):
                # Alternating base rows
                alt_bg = BG_CARD if (i % 2 == 1) else colors.HexColor("#0D0F14")
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), alt_bg))

                # Severity cell tint overlay on the first column only
                sev = s.get("severity", "")
                tint = SEVERITY_ROW_COLORS.get(sev)
                if tint:
                    style_cmds.append(("BACKGROUND", (0, i), (0, i), tint))
                    # Also colour the severity text
                    txt_color = (RED if sev == "high" else
                                 AMBER if sev == "medium" else GREEN)
                    style_cmds.append(("TEXTCOLOR", (0, i), (0, i), txt_color))
                    style_cmds.append(("FONTNAME",  (0, i), (0, i), "Helvetica-Bold"))

            sig_tbl.setStyle(TableStyle(style_cmds))
            story.append(sig_tbl)
        else:
            story.append(Paragraph("No fraud signals detected.", body_style))

        story.append(Spacer(1, 0.15 * inch))

        # ── 8. Annotated heatmap pages ─────────────────────────────────────
        if page_images:
            story.append(PageBreak())
            story.append(Paragraph("Annotated Heatmap Pages", h2_style))
            story.append(_heatmap_legend())
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(
                "The heatmap below shows the original resume with coloured bounding boxes "
                "drawn at each detected fraud signal's location.",
                body_style,
            ))
            story.append(Spacer(1, 0.1 * inch))

            n_pages = len(page_images)
            max_width = 6.5 * inch
            for page_num, png_bytes in enumerate(page_images, start=1):
                img_buf = io.BytesIO(png_bytes)
                rl_img = RLImage(img_buf)
                scale = max_width / rl_img.imageWidth
                rl_img.drawWidth  = max_width
                rl_img.drawHeight = rl_img.imageHeight * scale

                caption = Paragraph(
                    f"Page {page_num} of {n_pages} — annotated heatmap overlay",
                    caption_style,
                )
                story.append(KeepTogether([rl_img, Spacer(1, 0.05 * inch), caption]))
                story.append(Spacer(1, 0.2 * inch))
        else:
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph(
                "No renderable pages found for heatmap display.", body_style,
            ))

        # ── 9. Build the PDF ───────────────────────────────────────────────
        doc.build(
            story,
            onFirstPage=on_first_page,
            onLaterPages=on_later_pages,
        )

    return output_path