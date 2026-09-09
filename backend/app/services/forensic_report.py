"""
forensic_report.py — Phase 4
==============================
Generates a professional "evidence" PDF for a completed scan:

  - Cover section: filename, SHA-256 of the original file, scan timestamp,
    page count, severity summary.
  - Signal table: every FraudSignal with type / severity / page / description.
  - Annotated heatmap pages: the original PDF re-rendered with severity-coded
    boxes (via heatmap_generator.generate_heatmap), embedded page-by-page as
    images so the report is self-contained.

Uses ReportLab (pure-Python, no system deps) rather than WeasyPrint, which
would need a system Cairo/Pango install.
"""
from __future__ import annotations

import io
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak,
)

from app.services.heatmap_generator import generate_heatmap, render_page_images

SEVERITY_ROW_COLORS = {
    "high":   colors.HexColor("#f8d7da"),
    "medium": colors.HexColor("#fff3cd"),
    "low":    colors.HexColor("#fff9db"),
}


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

    # ── 1. Generate the annotated heatmap PDF in a temp file, then render
    #        its pages to PNGs to embed below ──────────────────────────────
    signals = scan_result.get("fraud_summary", {}).get("signals", [])
    with tempfile.TemporaryDirectory() as tmpdir:
        heatmap_path = Path(tmpdir) / "heatmap.pdf"
        generate_heatmap(original_pdf_path, signals, heatmap_path)
        page_images = render_page_images(heatmap_path, dpi=120)

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        h2_style = styles["Heading2"]
        body_style = styles["BodyText"]
        mono_style = ParagraphStyle(
            "Mono", parent=body_style, fontName="Courier", fontSize=8.5,
        )

        story = []

        # ── Cover ─────────────────────────────────────────────────────────
        story.append(Paragraph("ATS Fraud Detector — Forensic Report", title_style))
        story.append(Spacer(1, 0.15 * inch))

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        scanned_at = scan_result.get("scanned_at") or generated_at

        meta_rows = [
            ["Scan ID", str(scan_result.get("scan_id", "—"))],
            ["Filename", str(scan_result.get("filename", "—"))],
            ["SHA-256", str(scan_result.get("sha256", "—"))],
            ["Pages", str(scan_result.get("page_count", "—"))],
            ["Scanned At", str(scanned_at)],
            ["Report Generated", generated_at],
        ]
        meta_table = Table(meta_rows, colWidths=[1.6 * inch, 4.9 * inch])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Courier"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.25 * inch))

        # ── Severity summary ─────────────────────────────────────────────
        fraud = scan_result.get("fraud_summary", {})
        story.append(Paragraph("Severity Summary", h2_style))
        summary_rows = [
            ["Total", "High", "Medium", "Low", "AI Content Score", "True Match Score"],
            [
                str(fraud.get("total", 0)),
                str(fraud.get("high", 0)),
                str(fraud.get("medium", 0)),
                str(fraud.get("low", 0)),
                f"{scan_result.get('ai_content_score'):.1f}" if scan_result.get("ai_content_score") is not None else "—",
                f"{scan_result.get('true_match_score'):.1f}" if scan_result.get("true_match_score") is not None else "—",
            ],
        ]
        summary_table = Table(summary_rows, colWidths=[0.9 * inch] * 6)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))

        # ── Signal detail table ──────────────────────────────────────────
        story.append(Paragraph("Detected Fraud Signals", h2_style))
        if signals:
            sig_rows = [["Sev", "Type", "Pg", "Description", "Evidence"]]
            for s in signals:
                sig_rows.append([
                    s.get("severity", "—").upper(),
                    s.get("signal_type", "—").replace("_", " "),
                    str(s.get("page", "—")),
                    Paragraph(s.get("description", "")[:220], body_style),
                    Paragraph((s.get("evidence_text") or "")[:120], mono_style),
                ])
            sig_table = Table(
                sig_rows,
                colWidths=[0.55 * inch, 1.15 * inch, 0.35 * inch, 2.6 * inch, 1.85 * inch],
                repeatRows=1,
            )
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ]
            for i, s in enumerate(signals, start=1):
                bg = SEVERITY_ROW_COLORS.get(s.get("severity", ""))
                if bg:
                    style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
            sig_table.setStyle(TableStyle(style_cmds))
            story.append(sig_table)
        else:
            story.append(Paragraph("No fraud signals detected.", body_style))

        # ── Annotated heatmap pages ───────────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("Annotated Heatmap Pages", h2_style))
        story.append(Paragraph(
            "Red = high severity, orange = medium, yellow = low. "
            "Boxes mark the exact bounding area of each detected signal.",
            body_style,
        ))
        story.append(Spacer(1, 0.15 * inch))

        max_width = 6.5 * inch
        for page_num, png_bytes in enumerate(page_images, start=1):
            img_buf = io.BytesIO(png_bytes)
            rl_img = RLImage(img_buf)
            # Scale to fit page width, preserving aspect ratio
            scale = max_width / rl_img.imageWidth
            rl_img.drawWidth = max_width
            rl_img.drawHeight = rl_img.imageHeight * scale
            story.append(Paragraph(f"Page {page_num}", styles["Heading4"]))
            story.append(rl_img)
            story.append(Spacer(1, 0.2 * inch))

        doc.build(story)

    return output_path