# Phase 6 — Full Audit, Stabilisation & Feature Changes

> This document records every bug fixed, every determinism guarantee added, every UI change, and every new API feature introduced in Phase 6.

---

## 1. Bugs Fixed

### 1.1 `chardet` / `RequestsDependencyWarning` on every startup
- **Root cause**: `chardet 7.6.0` was listed in `requirements.txt` and conflict with `urllib3`'s bundled `charset-normalizer`.
- **Fix**: Removed `chardet` from `requirements.txt`; added `charset-normalizer==3.5.1` as the explicit dependency.
- **Files**: `backend/requirements.txt`

### 1.2 `detect_metadata_red_flags` — false "metadata_stripped" signal on clean PDFs
- **Root cause**: Guard was `metadata = metadata or {}`, so a `None` metadata dict became `{}` and immediately triggered the "metadata_stripped" signal for every clean PDF that had no metadata at all.
- **Fix**: Changed to `if metadata is None: return signals` (early exit).
- **Files**: `backend/app/services/fraud_detectors.py` — `detect_metadata_red_flags()`

### 1.3 Trust Score clock dependence — non-deterministic results
- **Root cause**: The rapid-edit-window detector compared `gap_minutes` against `datetime.now()` via `age_days`, making the "Caution" signal fire at different times depending on *when* the scan ran.
- **Fix**: Removed `age_days` / `datetime.now()` comparison entirely. Signal now fires purely on `0 < gap_minutes < 120`.
- **Files**: `backend/app/services/fraud_detectors.py` — `detect_metadata_red_flags()`

### 1.4 UNIQUE constraint violation on rescan (batch idempotency)
- **Root cause**: Re-uploading the same PDF (same SHA-256 + owner) inserted a second `Resume` row, violating the UNIQUE constraint on `(sha256, owner_id)`.
- **Fix**: `_execute_pdf_scan()` now detects an existing `Resume` by SHA-256 + owner and reuses it; the corresponding `ScanResult` is upserted (old `FraudSignal` and `TextSpan` rows deleted first).
- **Files**: `backend/app/routers/scan.py`

### 1.5 Non-deterministic homoglyph descriptions (set ordering)
- **Root cause**: Homoglyph descriptions were built from a Python `set`, whose iteration order is undefined between runs.
- **Fix**: Changed `{non_neutral}` to `sorted(non_neutral)` before joining into the description string.
- **Files**: `backend/app/services/fraud_detectors.py` — `detect_homoglyphs()`

### 1.6 pdfplumber fallback could raise unhandled exceptions
- **Root cause**: `_extract_with_pdfplumber()` had no try/except; any pdfplumber error propagated as a 500.
- **Fix**: Wrapped pdfplumber block in `try/except Exception` with graceful degradation.
- **Files**: `backend/app/services/pdf_extractor.py`

### 1.7 Missing 0-byte / encrypted / corrupted PDF validation
- **Root cause**: Passing a 0-byte file, an encrypted PDF, or a corrupted PDF caused cryptic PyMuPDF errors.
- **Fix**: Added explicit guards in `extract_pdf()` and `_extract_with_pymupdf()`:
  - 0-byte file → `ValueError("PDF file is empty")`
  - Encrypted → `ValueError("PDF is password-protected")`
  - 0-page → `ValueError("PDF has no pages")`
  - Corrupted → caught `fitz.FileDataError` → `ValueError("PDF file is corrupted or invalid")`
- **Files**: `backend/app/services/pdf_extractor.py`

### 1.8 SQLite schema drift — missing `trust_score` / `trust_label` columns
- **Root cause**: Existing databases created before Phase 5 lacked the `trust_score` and `trust_label` columns added to `ScanResult`.
- **Fix**: `init_db()` in `database.py` runs `PRAGMA table_info(scan_results)` and issues `ALTER TABLE ... ADD COLUMN` if either column is missing. Safe on both fresh and existing databases.
- **Files**: `backend/app/database.py`, `backend/app/main.py`

---

## 2. Determinism Guarantees

### 2.1 Signal sort order
- `run_all_detectors()` now returns signals sorted by `(page, severity_rank, signal_type, bbox_tuple, description)` — the same PDF always produces the same ordered list.
- **Files**: `backend/app/services/fraud_detectors.py`

### 2.2 Reference date parameter for future-date detection
- `_parse_date_fuzzy()`, `extract_date_ranges()`, `detect_timeline_issues()`, and `run_all_detectors()` all accept a new `ref_date: date | None = None` parameter.
- Tests can pass a fixed date to guarantee reproducible future-date signals.
- **Files**: `backend/app/services/fraud_detectors.py`

### 2.3 Trust Score consistency invariant enforced
- `_label_for()` now takes `high_count: int` and enforces:
  - `high_count >= 2` → label is always `"High Risk"` and `score = min(score, 44.0)`
  - `high_count == 1` → label is capped at `"Caution"` and `score = min(score, 74.0)`
- This guarantees the badge label and signal severity table can **never contradict** each other.
- **Files**: `backend/app/services/trust_score.py`

---

## 3. New Services

### 3.1 `forensic_narrative.py` — Executive Forensic Briefing
- `generate_score_narrative(trust_score, trust_label, fraud_summary, ai_content_score, true_match_score)` → dict
- Returns: `verdict_title`, `recommendation`, `summary`, `key_factors`, `limitations_disclaimer`
- Included in `/scan` and `/report/{id}/pdf` responses under the `"narrative"` key.
- **Files**: `backend/app/services/forensic_narrative.py`

### 3.2 `badge_generator.py` — SVG Trust Badge
- `generate_trust_badge_svg(trust_label, trust_score)` → SVG string
- Shields.io–style badge: green for Verified, amber for Caution, red for High Risk.
- Served at `GET /scan/{scan_id}/badge.svg`.
- **Files**: `backend/app/services/badge_generator.py`

---

## 4. New API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/scan/batch` | Upload multiple PDFs, returns ranked leaderboard |
| `GET`  | `/scan/{scan_id}/inspect` | Forensic span inspector — clean vs flagged spans per page |
| `GET`  | `/scan/{scan_id}/badge.svg` | Download shields-style SVG trust badge |

---

## 5. Scan Router Refactor

- Core pipeline extracted into `_execute_pdf_scan()` — shared by single and batch endpoints.
- Batch endpoint builds leaderboard sorted by `trust_score DESC`, `true_match_score DESC`.
- Span inspector groups spans by page and annotates each with `is_flagged` and `signal_types`.
- **Files**: `backend/app/routers/scan.py`

---

## 6. Forensic Report Enhancement

- Added **"Executive Forensic Briefing"** section at the top of the PDF using narrative data.
- Guarded heatmap page rendering with `if page_images:` to prevent crash when heatmap is unavailable.
- **Files**: `backend/app/services/forensic_report.py`, `backend/app/routers/report.py`

---

## 7. Frontend Redesign ("Cyber-Forensic Audit Station")

### Visual Changes
- Dark forensic colour scheme (`#0D0F14` background, `#3CB697` primary, monospace headers).
- Streamlit config theme in `.streamlit/config.toml` (root and `frontend/`).
- Animated SVG gauge (circle stroke-dashoffset animation) replacing CSS Houdini gauge.
- API online/offline indicator with pulsing coloured dot in sidebar.

### New Tabs
| Tab | Description |
|---|---|
| **Single Resume Scan** | Upload one PDF, view trust score gauge, fraud signals, narrative panel |
| **Side-by-Side Span Inspector** | Calls `/scan/{id}/inspect`; shows clean vs flagged spans per page |
| **Batch Leaderboard** | Multi-file upload; sortable table + per-candidate drilldown |
| **Shareable Trust Badge** | Displays badge SVG + Markdown embed snippet + recruiter ATS notes |

### Accessibility
- `@media (prefers-reduced-motion)` CSS to disable animations for users who prefer reduced motion.

### Files
- `frontend/app.py` — Complete rewrite
- `.streamlit/config.toml` — Created (dark forensic theme)
- `frontend/.streamlit/config.toml` — Created (same theme)

---

## 8. New Tests (`test_audit_and_features.py`)

12 new tests added on top of the existing 127:

| Test | What it covers |
|---|---|
| `test_determinism_same_pdf_same_signals` | Same PDF → identical signal list on 2 runs |
| `test_high_fraud_never_verified` | High fraud signals → Trust Score always High Risk |
| `test_clean_pdf_no_fraud_signals` | Clean fixture → zero fraud signals |
| `test_hidden_text_detected` | Hidden-text fixture → near-white signal flagged |
| `test_homoglyph_detected` | Homoglyph fixture → homoglyph signal flagged |
| `test_image_only_page_detected` | Image-only fixture → image-only signal flagged |
| `test_zero_byte_pdf_raises` | 0-byte file → clean `ValueError` |
| `test_corrupted_pdf_raises` | Corrupted bytes → clean `ValueError` |
| `test_health_endpoint` | `GET /health` → 200 |
| `test_scan_endpoint_returns_trust_score` | `POST /scan` → trust score + label present |
| `test_inspect_endpoint` | `GET /scan/{id}/inspect` → paginated spans |
| `test_badge_endpoint_returns_svg` | `GET /scan/{id}/badge.svg` → valid SVG |
| `test_batch_scan_leaderboard` | `POST /scan/batch` → sorted leaderboard |

**Total tests: 139 passed.**

---

## 9. Requirements Changes

| Package | Change | Reason |
|---|---|---|
| `chardet` | **Removed** | Conflicts with `urllib3`/`charset-normalizer` |
| `charset-normalizer==3.5.1` | **Added** | Explicit replacement for `chardet` |
| `pandas>=2.2.0` | **Added** | Used by batch leaderboard display in Streamlit |
