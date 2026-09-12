import pytest
from app.services.match_scorer import compute_pairwise_similarity
from app.services.trust_score import compute_trust_score

def test_compute_pairwise_similarity_identical():
    text1 = "Developed scalable backend systems in Python using FastAPI. Managed a team of 5 engineers."
    text2 = "Developed scalable backend systems in Python using FastAPI. Managed a team of 5 engineers. Added some extra text."
    
    resume_texts = {
        1: text1,
        2: text2
    }
    
    results = compute_pairwise_similarity(resume_texts, threshold=80.0)
    assert len(results) == 1
    match = results[0]
    
    assert match["id_a"] == 1 or match["id_b"] == 1
    assert match["similarity_score"] > 80.0
    assert len(match["shared_phrases"]) > 0

def test_compute_pairwise_similarity_unrelated():
    text1 = "Frontend developer skilled in React and TypeScript. Built interactive UI components."
    text2 = "Data scientist specializing in machine learning, pandas, and scikit-learn. Trained predictive models."
    
    resume_texts = {
        1: text1,
        2: text2
    }
    
    results = compute_pairwise_similarity(resume_texts, threshold=80.0)
    assert len(results) == 0

def test_trust_score_invariant_with_duplicate():
    fraud_summary = {
        "total": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "signals": []
    }
    trust = compute_trust_score(fraud_summary, ai_content_score=20.0, true_match_score=85.0)
    assert trust["label"] == "Verified"
    
    fraud_summary_flagged = {
        "total": 1,
        "high": 1,
        "medium": 0,
        "low": 0,
        "signals": [{"severity": "high", "signal_type": "duplicate_template"}]
    }
    trust_flagged = compute_trust_score(fraud_summary_flagged, ai_content_score=20.0, true_match_score=85.0)
    assert trust_flagged["label"] in ["Caution", "High Risk"]
    assert trust_flagged["score"] <= 74.0
