import pytest
from app.services.pdf_extractor import _extract_font_glyph_map
from app.services.fraud_detectors import detect_font_substitution

def test_font_substitution_no_anomalies():
    spans = [
        {"font_name": "Arial", "text": "Python Developer", "page": 1, "bbox": (10, 10, 50, 20)},
        {"font_name": "ABCDEF+NormalFont", "text": "Just a normal software engineer.", "page": 1, "bbox": (10, 30, 50, 40)},
    ]
    anomalies = _extract_font_glyph_map(spans)
    assert anomalies == []
    
    signals = detect_font_substitution(anomalies)
    assert signals == []

def test_font_substitution_pua_characters():
    spans = [
        {"font_name": "XYZABC+CustomFont", "text": "Hello \uE015 World", "page": 1, "bbox": (10, 10, 50, 20)}
    ]
    anomalies = _extract_font_glyph_map(spans)
    assert len(anomalies) == 1
    assert anomalies[0]["confidence"] == "high"
    
    signals = detect_font_substitution(anomalies)
    assert len(signals) == 1
    assert signals[0]["signal_type"] == "font_substitution"
    assert signals[0]["severity"] == "high"

def test_font_substitution_keyword_stuffing_heuristic():
    spans = [
        {
            "font_name": "QWERTY+StuffedFont", 
            "text": "python java kubernetes aws react agile leadership synergy docker azure", 
            "page": 2, 
            "bbox": (10, 10, 50, 20)
        }
    ]
    anomalies = _extract_font_glyph_map(spans)
    assert len(anomalies) == 1
    assert anomalies[0]["confidence"] == "medium"
    assert anomalies[0]["suspected_visual_text"] == "[visually hidden/swapped]"
    
    signals = detect_font_substitution(anomalies)
    assert len(signals) == 1
    assert signals[0]["severity"] == "high"

