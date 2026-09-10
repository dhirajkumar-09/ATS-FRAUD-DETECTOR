"""
badge_generator.py — SVG Trust Badge Generator
===============================================
Generates standalone, retina-crisp SVG Trust Badges for candidate resumes.
Can be rendered inline, downloaded, or embedded in ATS portfolios.
"""
from __future__ import annotations


def generate_trust_badge_svg(score: float, label: str) -> str:
    """Generate a modern shields-style SVG badge."""
    score_str = f"{score:.0f}/100"

    if label == "Verified":
        color_bg = "#2f9e6e"
        status_text = f"{score_str} VERIFIED"
        icon_path = '<path d="M12 2L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-3zm-2 16l-4-4 1.41-1.41L10 15.17l6.59-6.59L18 10l-8 8z" fill="#ffffff"/>'
    elif label == "Caution":
        color_bg = "#d97706"
        status_text = f"{score_str} CAUTION"
        icon_path = '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" fill="#ffffff"/>'
    else:
        color_bg = "#dc2626"
        status_text = f"{score_str} HIGH RISK"
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill="#ffffff"/>'

    label_width = 76
    status_width = len(status_text) * 8 + 26
    total_width = label_width + status_width

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="28" viewBox="0 0 {total_width} 28" role="img" aria-label="ATS TRUST: {status_text}">
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#fff" stop-opacity=".15"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="28" rx="6" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{label_width}" height="28" fill="#1e293b"/>
        <rect x="{label_width}" width="{status_width}" height="28" fill="{color_bg}"/>
        <rect width="{total_width}" height="28" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-weight="700" font-size="11">
        <text x="38" y="18" fill="#94a3b8" letter-spacing="0.5">ATS TRUST</text>
        <g transform="translate({label_width + 8}, 6) scale(0.66)">
            {icon_path}
        </g>
        <text x="{label_width + (status_width // 2) + 8}" y="18" fill="#ffffff" letter-spacing="0.5">{status_text}</text>
    </g>
</svg>"""
    return svg
