import pytest
from app.services.ai_content_detector import compute_paragraph_ai_scores

def test_ai_paragraph_scores_synthetic_higher_than_natural():
    natural_text = (
        "During my time at Acme Corp, I focused on improving the backend APIs. "
        "I worked closely with the frontend team to ensure that the new endpoints "
        "met their requirements. We managed to reduce the average response time "
        "by over thirty percent. It was a challenging but rewarding project."
    )
    
    # Highly synthetic, uniform, buzzword-heavy text
    synthetic_text = (
        "Furthermore, leveraging a synergistic paradigm shift, it is important to note "
        "that we revolutionized the dynamic environment. Additionally, we seamlessly "
        "streamlined the proactive approach to move the needle. In conclusion, it goes "
        "without saying that our holistic approach provided a robust solution."
    )
    
    full_text = f"{natural_text}\n\n{synthetic_text}"
    
    results = compute_paragraph_ai_scores(full_text)
    
    assert len(results) == 2
    
    natural_result = results[0]
    synthetic_result = results[1]
    
    assert natural_result["paragraph_index"] == 0
    assert synthetic_result["paragraph_index"] == 1
    
    # The synthetic text should score significantly higher than the natural text
    assert synthetic_result["ai_score"] > natural_result["ai_score"]
    assert synthetic_result["ai_score"] > 60  # Should be flagged as AI
    assert natural_result["ai_score"] < 40    # Should not be flagged as AI
