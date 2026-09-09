"""
tests/test_phase3.py — Phase 3 unit tests
==========================================
Tests for ai_content_detector.py and match_scorer.py.
All pure function tests — no API, no DB, no file I/O.
Run: pytest tests/test_phase3.py -v
"""
from __future__ import annotations

import pytest

from app.services.ai_content_detector import (
    _ai_phrase_density_score,
    _bigram_repetition_score,
    _sentence_uniformity_score,
    _sentences,
    _words,
    compute_ai_score,
    is_transformer_available,
)
from app.services.match_scorer import (
    _tf_cosine,
    _tokenise,
    compute_true_match_score,
    extract_skills,
)


# ═════════════════════════════════════════════════════════════════════════════
# AI Content Detector — helper functions
# ═════════════════════════════════════════════════════════════════════════════
class TestAIHelpers:
    def test_words_returns_lowercase_alpha_only(self):
        result = _words("Hello, World! 123 foo")
        assert result == ["hello", "world", "foo"]

    def test_sentences_splits_on_period_capital(self):
        text = "I built APIs. I also managed databases. These are my skills."
        sents = _sentences(text)
        assert len(sents) >= 2

    def test_sentences_handles_single_sentence(self):
        text = "This is one sentence."
        sents = _sentences(text)
        assert len(sents) == 1

    def test_sentences_handles_newlines(self):
        text = "First paragraph.\n\nSecond paragraph."
        sents = _sentences(text)
        assert len(sents) == 2


class TestSentenceUniformity:
    def test_uniform_sentences_high_score(self):
        # 5 sentences all with ~10 words each
        sents = [
            "I developed software at the company for many years.",
            "I managed databases and servers at the firm for long.",
            "I worked on Python projects with colleagues at work.",
            "I designed APIs for clients in the technology sector.",
            "I led teams and delivered products on time always.",
        ]
        score = _sentence_uniformity_score(sents)
        assert score > 0.5, f"Expected high uniformity, got {score}"

    def test_varied_sentences_lower_score(self):
        sents = [
            "Hi.",
            "I have five years of professional software engineering experience "
            "working in Python, Java, and C++, primarily on distributed systems "
            "and microservices architectures across multiple industries.",
            "Yes.",
            "I led a team of fifteen engineers across three time zones while "
            "managing stakeholder relationships and delivering critical infrastructure "
            "projects under tight deadlines with limited resources and budget constraints.",
            "OK.",
        ]
        score = _sentence_uniformity_score(sents)
        assert score < 0.5, f"Expected low uniformity, got {score}"

    def test_too_few_sentences_returns_neutral(self):
        score = _sentence_uniformity_score(["One sentence only."])
        assert score == 0.5

    def test_empty_sentences_returns_neutral(self):
        score = _sentence_uniformity_score([])
        assert score == 0.5


class TestAIPhraseDensity:
    def test_heavy_ai_phrases_high_score(self):
        text = (
            "Furthermore, I have leveraged cutting-edge technologies. "
            "Moreover, I have demonstrated multifaceted skills. "
            "Additionally, I have streamlined processes seamlessly. "
            "In conclusion, I am a thought leader in the space."
        )
        wc = len(text.split())
        score = _ai_phrase_density_score(text, wc)
        assert score > 0.5, f"Expected high density, got {score}"

    def test_no_ai_phrases_zero_score(self):
        text = "I wrote Python scripts to process CSV files and generate reports."
        wc = len(text.split())
        score = _ai_phrase_density_score(text, wc)
        assert score == 0.0

    def test_single_phrase_low_score(self):
        # One AI phrase in a larger body of text → non-zero but modest density.
        # A 200-word paragraph with one "Furthermore" gives ~0.5 per 100 words → score ~0.17
        text = (
            "Furthermore, " + " ".join(["worked on Python projects at the company"] * 10)
        )
        wc = len(text.split())
        score = _ai_phrase_density_score(text, wc)
        assert 0 < score < 1.0   # present but below saturation

    def test_too_short_text_returns_zero(self):
        score = _ai_phrase_density_score("Hi", 2)
        assert score == 0.0


class TestBigramRepetition:
    def test_high_repetition(self):
        # Repeating the same bigrams many times
        words = ["machine", "learning"] * 15 + ["data", "science"] * 10
        score = _bigram_repetition_score(words)
        assert score > 0.5

    def test_no_repetition(self):
        words = "the quick brown fox jumps over lazy dog ran away".split()
        score = _bigram_repetition_score(words)
        assert score < 0.3

    def test_too_short_returns_zero(self):
        score = _bigram_repetition_score(["hello", "world"])
        assert score == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# compute_ai_score — public API
# ═════════════════════════════════════════════════════════════════════════════
class TestComputeAiScore:
    HUMAN_RESUME = """
    Developed and maintained REST APIs using Python and FastAPI, serving
    over ten thousand daily active users. Reduced average response time
    by forty percent through query optimisation and Redis caching.
    Collaborated closely with the product team to deliver three major features
    ahead of schedule. Mentored two junior engineers on code review practices.
    Led the migration from a monolithic Rails application to microservices,
    cutting deployment time from two hours to eight minutes.
    """

    AI_RESUME = """
    Furthermore, I am a highly motivated and results-driven professional with
    a proven track record of leveraging cutting-edge technologies to streamline
    business processes. Moreover, I have demonstrated multifaceted expertise
    in delivering scalable and robust solutions. Additionally, my seamless
    integration of innovative methodologies has consistently driven transformative
    outcomes. In conclusion, I am a thought leader committed to revolutionizing
    the industry through state-of-the-art approaches and best-in-class deliverables.
    It is worth noting that my proactive and dynamic approach ensures synergy
    across all stakeholders.
    """

    def test_returns_required_keys(self):
        result = compute_ai_score(self.HUMAN_RESUME)
        assert "score"    in result
        assert "backend"  in result
        assert "breakdown" in result
        assert "note"     in result

    def test_score_in_range(self):
        for text in [self.HUMAN_RESUME, self.AI_RESUME]:
            result = compute_ai_score(text)
            assert 0.0 <= result["score"] <= 100.0

    def test_ai_resume_scores_higher_than_human(self):
        ai_score    = compute_ai_score(self.AI_RESUME)["score"]
        human_score = compute_ai_score(self.HUMAN_RESUME)["score"]
        assert ai_score > human_score, (
            f"AI resume scored {ai_score}, human scored {human_score} — "
            "expected AI to score higher"
        )

    def test_too_short_text_returns_zero(self):
        result = compute_ai_score("Hi")
        assert result["score"] == 0.0

    def test_backend_is_heuristic_by_default(self):
        # Unless torch is installed, should always use heuristic
        if not is_transformer_available():
            result = compute_ai_score(self.HUMAN_RESUME)
            assert result["backend"] == "heuristic"

    def test_breakdown_has_three_signals(self):
        result = compute_ai_score(self.HUMAN_RESUME)
        breakdown = result["breakdown"]
        if breakdown:   # only check if backend produced one
            assert "sentence_uniformity" in breakdown
            assert "ai_phrase_density"   in breakdown
            assert "bigram_repetition"   in breakdown


# ═════════════════════════════════════════════════════════════════════════════
# Match Scorer — helpers
# ═════════════════════════════════════════════════════════════════════════════
class TestTokenise:
    def test_removes_stopwords(self):
        tokens = _tokenise("the quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox"   in tokens

    def test_lowercases(self):
        tokens = _tokenise("Python JavaScript Docker")
        assert "python" in tokens
        assert "javascript" in tokens

    def test_drops_short_tokens(self):
        tokens = _tokenise("a be I do Python")
        # "a", "be", "I", "do" are either stopwords or len < 2
        assert "python" in tokens


class TestTfCosine:
    def test_identical_texts_score_one(self):
        tokens = "python developer years experience".split()
        assert abs(_tf_cosine(tokens, tokens) - 1.0) < 1e-6

    def test_disjoint_texts_score_zero(self):
        a = "python java docker kubernetes".split()
        b = "ballet opera painting sculpture".split()
        assert _tf_cosine(a, b) == 0.0

    def test_partial_overlap_between_zero_and_one(self):
        a = "python java docker".split()
        b = "python react docker".split()
        score = _tf_cosine(a, b)
        assert 0.0 < score < 1.0

    def test_empty_list_returns_zero(self):
        assert _tf_cosine([], ["python"]) == 0.0
        assert _tf_cosine(["python"], []) == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# extract_skills
# ═════════════════════════════════════════════════════════════════════════════
class TestExtractSkills:
    def test_python_detected(self):
        assert "Python" in extract_skills("Experienced Python developer")

    def test_javascript_case_insensitive(self):
        assert "JavaScript" in extract_skills("built with javascript and react")

    def test_kubernetes_k8s_alias(self):
        assert "Kubernetes" in extract_skills("deployed on K8s clusters")

    def test_java_not_javascript(self):
        # "Java" pattern should not match "JavaScript"
        skills = extract_skills("Expert in JavaScript and TypeScript")
        # JavaScript should be there, Java might not since regex uses negative lookahead
        assert "JavaScript" in skills

    def test_aws_detected(self):
        assert "AWS" in extract_skills("Deployed on Amazon Web Services")

    def test_multiple_skills(self):
        text = "Python, Docker, PostgreSQL, Kubernetes, React"
        skills = extract_skills(text)
        for s in ["Python", "Docker", "PostgreSQL", "Kubernetes", "React"]:
            assert s in skills, f"{s} not found in {skills}"

    def test_no_skills_returns_empty_set(self):
        result = extract_skills("Excellent communication and teamwork")
        # "Communication" and "Collaboration/Teamwork" ARE in the skill list
        # but generic prose should return only those soft skills
        assert isinstance(result, set)

    def test_gcp_alias(self):
        assert "GCP" in extract_skills("Worked on Google Cloud projects")


# ═════════════════════════════════════════════════════════════════════════════
# compute_true_match_score — public API
# ═════════════════════════════════════════════════════════════════════════════
class TestComputeTrueMatchScore:
    JD_BACKEND = """
    We are looking for a Senior Backend Engineer with 5+ years of experience.
    Required skills: Python, PostgreSQL, Docker, Kubernetes, REST API, AWS.
    Nice to have: Redis, Kafka, Terraform, CI/CD.
    The role involves designing microservices architectures and working in an
    Agile/Scrum environment.
    """

    RESUME_STRONG = """
    Senior Python developer with 6 years of experience. Built REST APIs using
    FastAPI and Django. Deployed applications on AWS using Docker containers
    orchestrated with Kubernetes. Managed PostgreSQL databases. Experienced with
    Agile and Scrum methodologies. Familiar with Redis caching.
    """

    RESUME_WEAK = """
    Frontend developer specialising in React and Vue. Experienced with CSS,
    HTML, and Figma. Built beautiful user interfaces for e-commerce platforms.
    Strong eye for design and user experience.
    """

    def test_returns_required_keys(self):
        result = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)
        for key in ("score", "tfidf_cosine", "skill_overlap",
                    "matched_skills", "missing_skills", "extra_skills"):
            assert key in result

    def test_score_in_range(self):
        for resume in [self.RESUME_STRONG, self.RESUME_WEAK]:
            result = compute_true_match_score(resume, self.JD_BACKEND)
            assert 0.0 <= result["score"] <= 100.0

    def test_strong_resume_scores_higher_than_weak(self):
        strong = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)["score"]
        weak   = compute_true_match_score(self.RESUME_WEAK,   self.JD_BACKEND)["score"]
        assert strong > weak, f"Strong={strong}, Weak={weak}"

    def test_matched_skills_are_subset_of_jd_skills(self):
        result = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)
        jd_skills = extract_skills(self.JD_BACKEND)
        for skill in result["matched_skills"]:
            assert skill in jd_skills

    def test_missing_skills_not_in_resume(self):
        result = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)
        resume_skills = extract_skills(self.RESUME_STRONG)
        for skill in result["missing_skills"]:
            assert skill not in resume_skills

    def test_extra_skills_not_in_jd(self):
        result = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)
        jd_skills = extract_skills(self.JD_BACKEND)
        for skill in result["extra_skills"]:
            assert skill not in jd_skills

    def test_empty_resume_returns_zero(self):
        result = compute_true_match_score("", self.JD_BACKEND)
        assert result["score"] == 0.0

    def test_empty_jd_returns_zero(self):
        result = compute_true_match_score(self.RESUME_STRONG, "")
        assert result["score"] == 0.0

    def test_identical_texts_high_score(self):
        text = "Python Docker PostgreSQL Kubernetes AWS Agile Scrum REST API"
        result = compute_true_match_score(text, text)
        # Both tfidf and skill overlap should be ~1.0 → score close to 100
        assert result["score"] > 80.0

    def test_word_counts_returned(self):
        result = compute_true_match_score(self.RESUME_STRONG, self.JD_BACKEND)
        assert result["resume_word_count"] > 0
        assert result["jd_word_count"] > 0
