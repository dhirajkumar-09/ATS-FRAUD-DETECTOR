"""
generate_fixtures.py — Generate Known Fixture PDFs for Test Suite
==================================================================
Creates 5 deterministic test PDFs in tests/fixtures/:
  1. clean_resume.pdf
  2. hidden_text_resume.pdf
  3. homoglyphs_resume.pdf
  4. layer_order_mismatch_resume.pdf
  5. scanned_image_only_resume.pdf
"""
from __future__ import annotations

import io
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


def generate_clean_resume() -> Path:
    out_path = FIXTURES_DIR / "clean_resume.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Letter

    # Title & Contact
    page.insert_text(fitz.Point(50, 60), "Jane Doe — Senior Software Engineer", fontsize=18, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 85), "jane.doe@example.com | San Francisco, CA | github.com/janedoe", fontsize=10, color=(0.2, 0.2, 0.2))

    # Experience
    page.insert_text(fitz.Point(50, 130), "Experience", fontsize=14, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 155), "Staff Backend Engineer — TechCorp Inc. (Jan 2021 – Present)", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 175), "• Architected high-throughput microservices using Python, FastAPI, and PostgreSQL.", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 195), "• Deployed distributed applications on AWS using Docker and Kubernetes clusters.", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 215), "• Improved API response latency by 45% through Redis caching and query optimisation.", fontsize=10, color=(0.2, 0.2, 0.2))

    page.insert_text(fitz.Point(50, 255), "Software Engineer — StartupX (Jun 2018 – Dec 2020)", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 275), "• Built real-time analytics streaming pipelines using Kafka, Go, and SQL.", fontsize=10, color=(0.2, 0.2, 0.2))

    # Skills
    page.insert_text(fitz.Point(50, 320), "Technical Skills", fontsize=14, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 345), "Languages: Python, Go, SQL, TypeScript", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 365), "Technologies: Docker, Kubernetes, AWS, FastAPI, PostgreSQL, Redis, Git", fontsize=10, color=(0.2, 0.2, 0.2))

    doc.set_metadata({
        "creator": "LibreOffice 7.4",
        "producer": "LibreOffice PDF Export",
        "creationDate": "D:20230501100000",
        "modDate": "D:20230501100000",
    })
    doc.save(str(out_path))
    doc.close()
    return out_path


def generate_hidden_text_resume() -> Path:
    out_path = FIXTURES_DIR / "hidden_text_resume.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    page.insert_text(fitz.Point(50, 60), "Alex Smith — Software Developer", fontsize=16, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 100), "Experience in building web applications with Python and JavaScript.", fontsize=10, color=(0, 0, 0))

    # Near-white hidden text stuffed at bottom (color (254/255, 255/255, 255/255))
    page.insert_text(
        fitz.Point(50, 750),
        "kubernetes aws docker gcp machine learning microservices lead executive director architect",
        fontsize=9,
        color=(254 / 255.0, 255 / 255.0, 255 / 255.0),
    )

    doc.set_metadata({"creator": "Microsoft Word", "creationDate": "D:20230101120000"})
    doc.save(str(out_path))
    doc.close()
    return out_path


def generate_homoglyphs_resume() -> Path:
    out_path = FIXTURES_DIR / "homoglyphs_resume.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Use PyMuPDF's built-in Unicode-capable font (tiro)
    font_buffer = fitz.Font("tiro").buffer
    page.insert_font(fontname="f0", fontbuffer=font_buffer)

    page.insert_text(fitz.Point(50, 60), "Bob Johnson — Senior Engineer", fontsize=16, fontname="f0", color=(0, 0, 0))
    # "Pуthon" with Cyrillic 'у' (U+0443), "Sоftware" with Cyrillic 'о' (U+043E)
    page.insert_text(fitz.Point(50, 100), "Lead developer skilled in P\u0443thon and S\u043Eftware architecture.", fontsize=11, fontname="f0", color=(0, 0, 0))

    doc.set_metadata({"creator": "Google Docs", "creationDate": "D:20230101120000"})
    doc.save(str(out_path))
    doc.close()
    return out_path


def generate_layer_order_mismatch_resume() -> Path:
    out_path = FIXTURES_DIR / "layer_order_mismatch_resume.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Insert lines in reverse visual order: bottom line first, top line last
    # This creates a high inversion count between content stream order and visual layout order
    lines = [
        (50, 500, "Education: Bachelor of Science in Computer Science, State University 2018."),
        (50, 450, "Projects: Open-source contributor to distributed cloud frameworks and tools."),
        (50, 400, "Skills: Python, Go, Docker, Kubernetes, AWS, Terraform, Microservices."),
        (50, 350, "Designed scalable backends serving millions of daily requests with 99.9% uptime."),
        (50, 300, "Led cross-functional engineering pods to deliver cloud modernization initiatives."),
        (50, 250, "Senior Distributed Systems Engineer — Enterprise Corp (2021 to 2024)."),
        (50, 200, "Summary: Experienced software architect specializing in resilient cloud platforms."),
        (50, 150, "Contact: candidate@example.com | Portfolio: candidate.dev | Location: Remote"),
        (50, 100, "Jordan Taylor — Lead Cloud Systems Architect & Engineer"),
    ]

    for x, y, text in lines:
        page.insert_text(fitz.Point(x, y), text, fontsize=10, color=(0, 0, 0))

    doc.set_metadata({"creator": "LaTeX", "creationDate": "D:20230101120000"})
    doc.save(str(out_path))
    doc.close()
    return out_path


def generate_scanned_image_only_resume() -> Path:
    out_path = FIXTURES_DIR / "scanned_image_only_resume.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Create a full-page image (simulating a scanned paper resume)
    img = Image.new("RGB", (600, 780), color=(245, 245, 245))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    # Insert image covering 95% of page area, with ZERO text spans inserted
    page.insert_image(fitz.Rect(10, 10, 600, 780), stream=img_bytes)

    doc.set_metadata({"creator": "Scanner", "producer": "ScanToPDF 3.0"})
    doc.save(str(out_path))
    doc.close()
    return out_path


def generate_all_fixtures() -> dict[str, Path]:
    return {
        "clean": generate_clean_resume(),
        "hidden_text": generate_hidden_text_resume(),
        "homoglyphs": generate_homoglyphs_resume(),
        "layer_order": generate_layer_order_mismatch_resume(),
        "image_only": generate_scanned_image_only_resume(),
    }


if __name__ == "__main__":
    generated = generate_all_fixtures()
    for name, path in generated.items():
        print(f"Generated {name}: {path} ({path.stat().st_size} bytes)")
