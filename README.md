# 🕵️ ATS Fraud Detector

> **Recruiter-grade forensic tool** that scans resume PDFs for ATS-manipulation techniques, scores AI authorship, measures job-description match, and issues a blended **Trust Score** with an executive briefing.

🔗 **Live App:** [ats-fraud-detector.vercel.app](https://ats-fraud-detector.vercel.app)
📦 **Repo:** [dhirajkumar-09/ATS-FRAUD-DETECTOR](https://github.com/dhirajkumar-09/ATS-FRAUD-DETECTOR)

![Status](https://img.shields.io/badge/status-active-success)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-Next.js-000000)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Phase Status](#phase-status)
- [Running Tests](#running-tests)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Why This Exists

Recruiters today rely on ATS software that only checks **keyword matches** — it has no way to detect resumes engineered with hidden text, zero-width characters, or fully AI-generated content designed to game the system. This leads to genuine candidates being filtered out while manipulated resumes slip through.

**ATS Fraud Detector** closes that gap: it forensically analyzes the actual resume PDF, flags manipulation signals with visual evidence, scores likely AI authorship, measures true relevance to the job description, and rolls it all into one actionable **Trust Score** — without sending candidate data to any third-party database.

---

## Features

| Category | What it detects / generates |
|---|---|
| **Fraud Signals** | Zero-width characters, Unicode homoglyphs, hidden / near-white text, off-page / tiny-font text, layer-order & word-order mismatch, metadata red flags, image-only pages |
| **AI Content Score** | Heuristic burstiness + perplexity score (0–100, higher = more likely AI-written) |
| **True Match Score** | TF-IDF cosine similarity of resume text vs. job description (0–100) |
| **Trust Score** | Blended verdict — `Verified` / `Caution` / `High Risk` — consistent with signal severity |
| **Forensic Narrative** | Plain-English executive briefing: verdict, key factors, recommendation, limitations |
| **SVG Trust Badge** | Shields-style coloured badge, embeddable in ATS dashboards or emails |
| **Batch Leaderboard** | Upload multiple resumes, get a ranked table sorted by Trust Score + Match Score |
| **Span Inspector** | Side-by-side clean vs. flagged text-span comparison, per page |
| **Forensic PDF Report** | Full ReportLab PDF with heatmap, executive briefing, and signal detail table |

---

## Tech Stack

**Frontend (`frontend-web/`)**
Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Three.js + React Three Fiber, Framer Motion — deployed on **Vercel**.

**Backend (`backend/`)**
FastAPI, SQLAlchemy, JWT authentication, PyMuPDF + pdfplumber (PDF parsing), Tesseract OCR fallback, HuggingFace `distilgpt2` (AI content detection), scikit-learn TF-IDF (match scoring), ReportLab (PDF reports), Google Gemini API (assistant features) — deployed on **Render**.

---

## Project Structure

```
ATS-FRAUD-DETECTOR/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entry-point + lifespan
│   │   ├── config.py                 # All tunable thresholds / env vars
│   │   ├── database.py               # SQLAlchemy engine + auto-migration
│   │   ├── models.py                 # Resume, ScanResult, FraudSignal, TextSpan
│   │   ├── auth.py                   # JWT auth helpers
│   │   ├── routers/
│   │   │   ├── scan.py               # /scan endpoints (single, batch, inspect, badge)
│   │   │   └── report.py             # GET /report/{id}/pdf
│   │   └── services/
│   │       ├── pdf_extractor.py      # PyMuPDF + pdfplumber — robust extraction
│   │       ├── fraud_detectors.py    # 8 fraud detectors, deterministic output
│   │       ├── ai_content_detector.py
│   │       ├── match_scorer.py       # TF-IDF cosine match
│   │       ├── heatmap_generator.py  # Per-page heatmap rendering
│   │       ├── forensic_report.py    # ReportLab PDF report
│   │       ├── forensic_narrative.py # Plain-English executive briefing
│   │       ├── badge_generator.py    # SVG trust badge
│   │       ├── trust_score.py        # Blended scoring + consistency enforcement
│   │       └── ocr_helper.py         # Tesseract fallback
│   ├── requirements.txt
│   └── tests/
│       ├── fixtures/                 # Deterministic test PDFs
│       ├── generate_fixtures.py
│       ├── test_pdf_extractor.py
│       ├── test_fraud_detectors.py
│       ├── test_phase3.py
│       ├── test_phase5_features.py
│       └── test_audit_and_features.py
│
├── frontend-web/                     # Next.js recruiter dashboard (live on Vercel)
│   ├── app/                          # App router pages
│   ├── components/                   # UI components (shadcn/ui based)
│   └── public/
│
├── PHASE5_CHANGES.md
├── PHASE6_CHANGES.md
└── README.md
```

---

## Quick Start

### 1 — Clone the repo

```bash
git clone https://github.com/dhirajkumar-09/ATS-FRAUD-DETECTOR.git
cd ATS-FRAUD-DETECTOR
```

### 2 — Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
```
> **Note:** `chardet` is intentionally **not** listed — it conflicts with `urllib3`'s `charset-normalizer`. Use `charset-normalizer` (already listed) instead.

### 3 — Run the backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```
Visit **http://localhost:8000/docs** for the interactive Swagger UI.

### 4 — Run the frontend (new terminal)

```bash
cd frontend-web
npm install
npm run dev
```
Visit **http://localhost:3000**

### 5 — Run tests

```bash
cd backend
pytest tests/ -v
```

---

## Authentication

Every `/scan` and `/report` endpoint requires a **Bearer JWT**. There is no anonymous access — calling any of them without a token returns `401 Unauthorized`. Accounts are scoped to an **organization**: the first person to register under a given `organization` name is auto-promoted to admin for that org.

### Auth Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Create an account, returns a JWT immediately |
| `POST` | `/auth/login` | No | OAuth2 password flow (`username` = email), returns a JWT |
| `GET` | `/auth/me` | Yes | Current user's profile |
| `GET` | `/auth/org-settings` | Yes | This user's org threshold overrides |
| `PUT` | `/auth/org-settings` | Yes (admin only) | Update org threshold overrides |

### Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "recruiter@acme.com",
  "password": "at-least-8-chars",
  "full_name": "Jane Recruiter",
  "organization": "Acme Corp"
}
```

Response (also returned by `/auth/login`):

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user_id": 1,
  "email": "recruiter@acme.com",
  "organization": "Acme Corp",
  "is_admin": true
}
```

### Login

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=recruiter@acme.com&password=at-least-8-chars
```
> Login uses standard OAuth2 password-flow form fields (`username` / `password`), **not** JSON — this lets you authorize directly from the `/docs` Swagger UI's "Authorize" button.

### Using the token

Every other endpoint needs this header:

```
Authorization: Bearer <access_token>
```

### Org settings (admin)

```http
PUT /auth/org-settings
Authorization: Bearer <admin's access_token>
Content-Type: application/json

{
  "near_white_threshold": 25,
  "hidden_font_size_pt": 1.5
}
```
Pass `null` for either field to fall back to the app default. Non-admins can `GET /auth/org-settings` to view current org values but cannot change them.

---

## API Reference

All endpoints below require the `Authorization: Bearer <access_token>` header described in [Authentication](#authentication).

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Backend health check (no auth required) |
| `POST` | `/scan` | Upload a single resume PDF; optional `job_description` form field |
| `GET` | `/scan/{scan_id}` | Retrieve full scan result (fraud signals, scores, narrative) |
| `POST` | `/scan/batch` | Upload multiple resumes; returns ranked Trust Score leaderboard |
| `GET` | `/scan/{scan_id}/inspect` | Forensic side-by-side span inspector (clean vs. flagged) |
| `GET` | `/scan/{scan_id}/badge.svg` | Download SVG trust badge for embedding |
| `GET` | `/report/{scan_id}/pdf` | Download full forensic PDF report |
| `GET` | `/docs` | Swagger UI |

### `/scan` — Request

```http
POST /scan
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file:            <resume.pdf>             (required)
job_description: "Senior Python engineer…" (optional)
```

### `/scan` — Response (abbreviated)

```json
{
  "scan_id": 42,
  "filename": "resume.pdf",
  "trust_score": 78.3,
  "trust_label": "Caution",
  "fraud_signals": [...],
  "fraud_summary": {"high": 0, "medium": 1, "low": 2},
  "ai_content_score": 34.1,
  "true_match_score": 61.2,
  "narrative": {
    "verdict_title": "Caution — Moderate Manipulation Risk",
    "recommendation": "...",
    "summary": "...",
    "key_factors": [...],
    "limitations_disclaimer": "..."
  }
}
```

### `/scan/batch` — Request

```http
POST /scan/batch
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

files:           [resume1.pdf, resume2.pdf, …]
job_description: "…" (optional)
```
Returns an array sorted by `trust_score DESC`, `true_match_score DESC`.

### End-to-end example (curl)

```bash
# 1. Register (or use /auth/login if you already have an account)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"recruiter@acme.com","password":"at-least-8-chars","organization":"Acme Corp"}'

# Copy the "access_token" from the response, then:

# 2. Scan a resume using the token
curl -X POST http://localhost:8000/scan \
  -H "Authorization: Bearer <PASTE_ACCESS_TOKEN_HERE>" \
  -F "file=@resume.pdf"
```

---

## Configuration

All thresholds live in `backend/app/config.py` and can be overridden with environment variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///ats_fraud.db` | SQLAlchemy connection string |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MB) | Max PDF upload size |
| `NEAR_WHITE_THRESHOLD` | `30` | RGB Euclidean distance for hidden-text check |
| `HIDDEN_FONT_SIZE_PT` | `1.0` | Font size (pt) ≤ this → hidden text flag |
| `AI_DETECTOR_MODEL` | `distilgpt2` | HuggingFace model for AI content detection |
| `SECRET_KEY` | *(random)* | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT TTL |

---

## Phase Status

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Skeleton + PDF extraction + `/scan` endpoint + MVP UI | ✅ Done |
| **Phase 2** | Fraud detectors (zero-width, homoglyphs, hidden text, off-page/tiny-font, timeline) | ✅ Done |
| **Phase 3** | AI content detection + True Match Score (TF-IDF) | ✅ Done |
| **Phase 4** | Visual heatmap + Forensic PDF report (ReportLab) | ✅ Done |
| **Phase 5** | Evidence/case-file UI redesign | ✅ Done |
| **Phase 6** | Full audit + determinism + UI redesign + new features | ✅ Done |
| **Phase 7** | Docker + cloud deployment automation | 🔲 Planned |

See [`PHASE5_CHANGES.md`](https://github.com/dhirajkumar-09/ATS-FRAUD-DETECTOR/blob/main/PHASE5_CHANGES.md) and [`PHASE6_CHANGES.md`](https://github.com/dhirajkumar-09/ATS-FRAUD-DETECTOR/blob/main/PHASE6_CHANGES.md) for the detailed change logs.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Single suite
pytest tests/test_audit_and_features.py -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Test suites

| File | Tests | Coverage |
|---|---|---|
| `test_pdf_extractor.py` | PDF parsing, edge cases | `pdf_extractor.py` |
| `test_fraud_detectors.py` | All 8 detectors, edge cases | `fraud_detectors.py` |
| `test_phase3.py` | AI content + match scorer | `ai_content_detector.py`, `match_scorer.py` |
| `test_phase5_features.py` | Layer order, metadata, trust score | `trust_score.py`, `fraud_detectors.py` |
| `test_audit_and_features.py` | Determinism, consistency, API endpoints, edge PDFs | All services + routers |

---

## Roadmap

- 🐳 Docker + one-click cloud deployment for recruiter teams
- 🎥 Identity & video verification (catch interview-stage deepfakes / proxy interviewers)
- 📊 Benchmark-tested AI detector with published precision/recall on a labeled dataset
- 🧩 Browser extension for in-platform scanning (LinkedIn, Naukri, etc.)
- 🌐 Regional language support (Hindi and other Indian-language resumes)

---

## Contributing

Issues and PRs are welcome. Please open an issue first to discuss significant changes before submitting a pull request.

---

## License

MIT — see [LICENSE](LICENSE) for details.
