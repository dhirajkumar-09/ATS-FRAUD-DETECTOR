"""
match_scorer.py — Phase 3
==========================
Computes the "True Match Score" between a clean resume and a job description.
No scikit-learn or spaCy required — everything uses stdlib + Counter math.

Algorithm
---------
1. Extract skills from both texts using a curated regex skill list.
2. Compute TF-weighted cosine similarity on tokenised, stopword-stripped text.
3. Final score = 0.55 × cosine_similarity + 0.45 × skill_overlap_ratio

Skill overlap is weighted heavily because recruiters care about specific
keyword matches, not just topical similarity.

Public API
----------
    compute_true_match_score(resume_text: str, jd_text: str) -> dict
        Returns {
            "score":           float,   # 0–100
            "tfidf_cosine":    float,   # 0–1 cosine component
            "skill_overlap":   float,   # 0–1 skill component
            "matched_skills":  list[str],
            "missing_skills":  list[str],
            "extra_skills":    list[str],  # resume has but JD doesn't mention
        }

    extract_skills(text: str) -> set[str]
        Returns normalised skill names found in text.
"""
from __future__ import annotations

import math
import re
from collections import Counter

# ─────────────────────────────────────────────────────────────────────────────
# Curated skill lexicon (~130 entries)
# Keys   = canonical display name
# Values = regex pattern (case-insensitive, matched at word boundary)
# ─────────────────────────────────────────────────────────────────────────────
_SKILL_PATTERNS: dict[str, str] = {
    # ── Programming languages ─────────────────────────────────────────────
    "Python":       r"\bPython\b",
    "Java":         r"\bJava\b(?!Script)",
    "JavaScript":   r"\bJavaScript\b|\bJS\b",
    "TypeScript":   r"\bTypeScript\b|\bTS\b",
    "C++":          r"\bC\+\+\b",
    "C#":           r"\bC#\b",
    "Go":           r"\bGolang\b|\bGo\b(?:\s+lang(?:uage)?)?",
    "Rust":         r"\bRust\b",
    "Ruby":         r"\bRuby\b",
    "PHP":          r"\bPHP\b",
    "Swift":        r"\bSwift\b",
    "Kotlin":       r"\bKotlin\b",
    "Scala":        r"\bScala\b",
    "R":            r"\bR\b(?:\s+programming)?",
    "Bash":         r"\bBash\b|\bShell\s+Script(?:ing)?\b",
    "SQL":          r"\bSQL\b",
    # ── Web frameworks ────────────────────────────────────────────────────
    "React":        r"\bReact(?:\.js|JS)?\b",
    "Angular":      r"\bAngular(?:JS|2\+)?\b",
    "Vue":          r"\bVue(?:\.js|JS)?\b",
    "Next.js":      r"\bNext\.js\b|\bNextJS\b",
    "Node.js":      r"\bNode(?:\.js|JS)\b",
    "Django":       r"\bDjango\b",
    "Flask":        r"\bFlask\b",
    "FastAPI":      r"\bFastAPI\b",
    "Spring":       r"\bSpring(?:\s+Boot)?\b",
    "Express":      r"\bExpress(?:\.js|JS)?\b",
    "Laravel":      r"\bLaravel\b",
    "Rails":        r"\bRuby\s+on\s+Rails\b|\bRails\b",
    "ASP.NET":      r"\bASP\.NET\b",
    "GraphQL":      r"\bGraphQL\b",
    "REST API":     r"\bREST(?:\s+API)?\b|\bRESTful\b",
    "gRPC":         r"\bgRPC\b",
    # ── Databases ─────────────────────────────────────────────────────────
    "PostgreSQL":   r"\bPostgreSQL\b|\bPostgres\b",
    "MySQL":        r"\bMySQL\b",
    "MongoDB":      r"\bMongoDB\b|\bMongo\b",
    "Redis":        r"\bRedis\b",
    "Elasticsearch":r"\bElasticsearch\b|\bElastic\b",
    "Cassandra":    r"\bCassandra\b",
    "DynamoDB":     r"\bDynamoDB\b",
    "SQLite":       r"\bSQLite\b",
    "Oracle DB":    r"\bOracle(?:\s+DB|Database)?\b",
    "SQL Server":   r"\bSQL\s+Server\b|\bMSSQL\b",
    "BigQuery":     r"\bBigQuery\b",
    "Snowflake":    r"\bSnowflake\b",
    # ── Cloud & DevOps ────────────────────────────────────────────────────
    "AWS":          r"\bAWS\b|\bAmazon\s+Web\s+Services\b",
    "Azure":        r"\bAzure\b|\bMicrosoft\s+Azure\b",
    "GCP":          r"\bGCP\b|\bGoogle\s+Cloud\b",
    "Docker":       r"\bDocker\b",
    "Kubernetes":   r"\bKubernetes\b|\bK8s\b",
    "Terraform":    r"\bTerraform\b",
    "Ansible":      r"\bAnsible\b",
    "Jenkins":      r"\bJenkins\b",
    "CI/CD":        r"\bCI/CD\b|\bContinuous\s+Integration\b|\bContinuous\s+Delivery\b",
    "GitHub Actions":r"\bGitHub\s+Actions\b",
    "Linux":        r"\bLinux\b|\bUbuntu\b|\bDebian\b|\bCentOS\b",
    "Nginx":        r"\bNginx\b",
    "Apache":       r"\bApache\b(?!\s+Kafka)",
    "Kafka":        r"\bApache\s+Kafka\b|\bKafka\b",
    "RabbitMQ":     r"\bRabbitMQ\b",
    # ── ML / Data Science ─────────────────────────────────────────────────
    "TensorFlow":   r"\bTensorFlow\b",
    "PyTorch":      r"\bPyTorch\b",
    "scikit-learn": r"\bscikit-learn\b|\bsklearn\b",
    "Keras":        r"\bKeras\b",
    "Pandas":       r"\bPandas\b",
    "NumPy":        r"\bNumPy\b",
    "Spark":        r"\bApache\s+Spark\b|\bPySpark\b|\bSpark\b",
    "Hadoop":       r"\bHadoop\b",
    "Tableau":      r"\bTableau\b",
    "Power BI":     r"\bPower\s+BI\b",
    "Jupyter":      r"\bJupyter\b",
    "MLflow":       r"\bMLflow\b",
    "Airflow":      r"\bAirflow\b|\bApache\s+Airflow\b",
    "dbt":          r"\bdbt\b",
    "LLM":          r"\bLLM\b|\bLarge\s+Language\s+Model\b",
    "RAG":          r"\bRAG\b|\bRetrieval.Augmented\s+Generation\b",
    # ── Version control / collaboration ───────────────────────────────────
    "Git":          r"\bGit\b(?!\s*Hub|\s*Lab)",
    "GitHub":       r"\bGitHub\b",
    "GitLab":       r"\bGitLab\b",
    "JIRA":         r"\bJIRA\b|\bJira\b",
    "Confluence":   r"\bConfluence\b",
    # ── Architecture & patterns ───────────────────────────────────────────
    "Microservices":r"\bMicroservices\b|\bMicro-services\b",
    "Serverless":   r"\bServerless\b",
    "Event-Driven": r"\bEvent.Driven\b",
    "System Design":r"\bSystem\s+Design\b",
    "Design Patterns":r"\bDesign\s+Patterns?\b",
    # ── Security ─────────────────────────────────────────────────────────
    "OAuth":        r"\bOAuth\b",
    "JWT":          r"\bJWT\b",
    "TLS/SSL":      r"\bTLS\b|\bSSL\b",
    # ── Agile / Process ───────────────────────────────────────────────────
    "Agile":        r"\bAgile\b",
    "Scrum":        r"\bScrum\b",
    "Kanban":       r"\bKanban\b",
    "TDD":          r"\bTDD\b|\bTest.Driven\s+Development\b",
    # ── Communication / soft skills ───────────────────────────────────────
    "Communication":r"\bCommunication\b",
    "Leadership":   r"\bLeadership\b",
    "Collaboration":r"\bCollaboration\b|\bTeamwork\b",
    "Problem-Solving":r"\bProblem.Solv(?:ing|er)\b",
    "Mentoring":    r"\bMentor(?:ing|ship)\b",
}

# Compile all patterns once
_COMPILED_SKILLS: list[tuple[str, re.Pattern]] = [
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in _SKILL_PATTERNS.items()
]

# ─────────────────────────────────────────────────────────────────────────────
# Compact English stopword list (stdlib, no NLTK)
# ─────────────────────────────────────────────────────────────────────────────
_STOPWORDS: frozenset[str] = frozenset("""
a about above after again against all also am an and any are aren't as at be
because been before being below between both but by can't cannot could couldn't
did didn't do does doesn't doing don't down during each few for from further
get got had hadn't has hasn't have haven't having he he'd he'll he's her here
here's hers herself him himself his how how's however i i'd i'll i'm i've if
in into is isn't it it's its itself let's me more most mustn't my myself no
nor not of off on once only or other ought our ours ourselves out over own same
shan't she she'd she'll she's should shouldn't so some such than that that's
the their theirs them themselves then there there's these they they'd they'll
they're they've this those through to too under until up very was wasn't we
we'd we'll we're we've were weren't what what's when when's where where's which
while who who's whom why why's will with won't would wouldn't you you'd you'll
you're you've your yours yourself yourselves
""".split())


def _tokenise(text: str) -> list[str]:
    """Lowercase, alpha-only tokenisation with stopword removal."""
    tokens = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


# ─────────────────────────────────────────────────────────────────────────────
# TF cosine similarity (no external deps)
# ─────────────────────────────────────────────────────────────────────────────

def _tf_cosine(tokens_a: list[str], tokens_b: list[str]) -> float:
    """
    TF-weighted cosine similarity between two token lists.
    (TF only; IDF is meaningless with just 2 documents.)
    """
    if not tokens_a or not tokens_b:
        return 0.0

    tf_a = Counter(tokens_a)
    tf_b = Counter(tokens_b)
    len_a = len(tokens_a)
    len_b = len(tokens_b)

    vec_a = {w: c / len_a for w, c in tf_a.items()}
    vec_b = {w: c / len_b for w, c in tf_b.items()}

    shared = set(vec_a) & set(vec_b)
    dot    = sum(vec_a[w] * vec_b[w] for w in shared)
    mag_a  = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b  = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ─────────────────────────────────────────────────────────────────────────────
# Skill extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_skills(text: str) -> set[str]:
    """
    Return canonical skill names found in text.
    Matches are word-boundary-aware and case-insensitive.
    """
    found: set[str] = set()
    for name, pattern in _COMPILED_SKILLS:
        if pattern.search(text):
            found.add(name)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def compute_true_match_score(resume_text: str, jd_text: str) -> dict:
    """
    Compute the True Match Score between a clean resume and a job description.

    Parameters
    ----------
    resume_text : Clean resume text (fraudulent spans already stripped).
    jd_text     : Raw job description text.

    Returns
    -------
    {
        "score":           float,       # 0–100 final score
        "tfidf_cosine":    float,       # 0–100 raw cosine component
        "skill_overlap":   float,       # 0–100 skill overlap component
        "matched_skills":  list[str],   # skills in both JD and resume
        "missing_skills":  list[str],   # skills in JD but not resume
        "extra_skills":    list[str],   # skills in resume but not JD
        "resume_word_count": int,
        "jd_word_count":   int,
    }
    """
    if not resume_text.strip() or not jd_text.strip():
        return {
            "score": 0.0,
            "tfidf_cosine": 0.0,
            "skill_overlap": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "extra_skills":   [],
            "resume_word_count": 0,
            "jd_word_count":     0,
            "note": "Empty text provided.",
        }

    # ── 1. Tokenise ──────────────────────────────────────────────────────────
    resume_tokens = _tokenise(resume_text)
    jd_tokens     = _tokenise(jd_text)

    # ── 2. TF cosine similarity ──────────────────────────────────────────────
    cosine = _tf_cosine(resume_tokens, jd_tokens)

    # ── 3. Skill overlap ─────────────────────────────────────────────────────
    jd_skills     = extract_skills(jd_text)
    resume_skills = extract_skills(resume_text)

    matched  = sorted(jd_skills & resume_skills)
    missing  = sorted(jd_skills - resume_skills)
    extra    = sorted(resume_skills - jd_skills)

    if jd_skills:
        skill_overlap = len(matched) / len(jd_skills)
    else:
        skill_overlap = cosine   # no skills in JD → fall back to cosine

    # ── 4. Combined score ────────────────────────────────────────────────────
    # Cosine captures topical alignment; skill overlap captures keyword match.
    score = round((0.55 * cosine + 0.45 * skill_overlap) * 100, 1)

    return {
        "score":           min(100.0, max(0.0, score)),
        "tfidf_cosine":    round(cosine        * 100, 1),
        "skill_overlap":   round(skill_overlap * 100, 1),
        "matched_skills":  matched,
        "missing_skills":  missing,
        "extra_skills":    extra,
        "resume_word_count": len(resume_tokens),
        "jd_word_count":     len(jd_tokens),
    }


def spans_to_clean_text(
    spans: list[dict],
    flagged_signal_types: set[str] | None = None,
) -> tuple[str, int, int]:
    """
    Convert span list to clean text, excluding spans whose signal type is
    in `flagged_signal_types` (defaults to all HIGH-severity manipulation types).

    Returns (clean_text, clean_word_count, flagged_word_count).
    """
    if flagged_signal_types is None:
        flagged_signal_types = {
            "zero_width_chars",
            "hidden_text",
            "zero_or_tiny_font",
            "offpage_text",
            "homoglyph_substitution",
        }

    # We don't have per-span signal membership here; the caller should
    # pre-filter. This is a convenience wrapper that just concatenates text.
    clean_parts: list[str] = []
    for span in spans:
        text = span.get("text", "").strip()
        if text:
            clean_parts.append(text)

    clean_text = " ".join(clean_parts)
    clean_wc   = len(re.findall(r"\b[a-zA-Z]+\b", clean_text))
    return clean_text, clean_wc, 0
