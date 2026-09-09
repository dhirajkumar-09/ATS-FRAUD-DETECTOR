# ATS Fraud Detector

Recruiter-facing tool that scans resume PDFs for ATS manipulation techniques.

## Project Structure

```
ats-fraud-detector/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint
│   │   ├── config.py              # All tunable thresholds / env vars
│   │   ├── database.py            # SQLAlchemy engine + session
│   │   ├── models.py              # Resume, ScanResult, FraudSignal, TextSpan
│   │   ├── routers/
│   │   │   ├── scan.py            # POST /scan, GET /scan/{id}
│   │   │   └── report.py          # GET /report/{id}/pdf  (Phase 4)
│   │   └── services/
│   │       ├── pdf_extractor.py   # PyMuPDF + pdfplumber + pikepdf
│   │       ├── fraud_detectors.py # Phase 2 detectors (stubs)
│   │       ├── ai_content_detector.py  # Phase 3 stub
│   │       ├── match_scorer.py    # Phase 3 stub
│   │       ├── heatmap_generator.py    # Phase 4 stub
│   │       └── forensic_report.py      # Phase 4 stub
│   ├── requirements.txt
│   └── tests/
│       └── test_pdf_extractor.py
└── frontend/
    └── app.py                     # Streamlit MVP
```

## Quick Start

### 1 — Install dependencies

```powershell
cd ats-fraud-detector\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2 — Run the backend

```powershell
# from backend/
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

### 3 — Run the Streamlit frontend (new terminal)

```powershell
# from ats-fraud-detector/
streamlit run frontend/app.py
```

Visit **http://localhost:8501**

### 4 — Run tests

```powershell
# from backend/
pytest tests/ -v
```

## API Endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/scan` | Upload PDF, extract spans, return `scan_id` |
| `GET`  | `/scan/{scan_id}` | Retrieve full scan result |
| `GET`  | `/report/{scan_id}/pdf` | Download forensic PDF *(Phase 4)* |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | Swagger UI |

## Configuration (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///ats_fraud.db` | SQLAlchemy connection string |
| `MAX_UPLOAD_BYTES` | `20971520` (20 MB) | Max PDF upload size |
| `NEAR_WHITE_THRESHOLD` | `30` | RGB Euclidean distance for hidden-text check |
| `HIDDEN_FONT_SIZE_PT` | `1.0` | Font-size (pt) ≤ this → hidden text flag |
| `AI_DETECTOR_MODEL` | `distilgpt2` | HuggingFace model for Phase 3 |

## Phase Status

- [x] **Phase 1** — Skeleton + PDF extraction + `/scan` endpoint + Streamlit
- [ ] **Phase 2** — Fraud detectors (zero-width, homoglyphs, hidden text, timeline)
- [ ] **Phase 3** — AI content detection + True Match Score
- [ ] **Phase 4** — Visual heatmap + Forensic PDF report
- [ ] **Phase 5** — Frontend polish
- [ ] **Phase 6** — Docker + deployment
