\# Phase 5 — New Features (this patch)



Four features added on top of your existing Phase 1-4 pipeline. Nothing

existing was removed; new signals just flow through your existing

severity table, heatmap, and forensic-report machinery automatically.



\## 1. PDF Layer-Order Forensics

\- `backend/app/services/pdf\_extractor.py`

&#x20; - `\_visual\_sort\_key()`, `\_count\_inversions()`, `\_compute\_word\_order\_signal()`

&#x20; - `extract\_pdf()` now also returns `"word\_order"`: per-page

&#x20;   `{page, word\_count, disorder\_ratio, sample\_words}`

\- `backend/app/services/fraud\_detectors.py`

&#x20; - `detect\_layer\_order\_mismatch(word\_order)` → `layer\_order\_mismatch` signal

&#x20;   (medium >15% disorder, high >30% disorder)



\## 2. Metadata Forensics ("Digital Fingerprint")

\- `backend/app/services/fraud\_detectors.py`

&#x20; - `detect\_metadata\_red\_flags(metadata)` → three possible signals:

&#x20;   `metadata\_generic\_builder\_tool`, `metadata\_rapid\_edit\_window`,

&#x20;   `metadata\_stripped` (+ `metadata\_mod\_before\_creation` edge case)

&#x20; - Uses metadata already returned by your existing

&#x20;   `pdf\_extractor.\_extract\_metadata()` — no new extraction needed.



\## 3. Image-only Page Detection (OCR bypass check)

\- `backend/app/services/pdf\_extractor.py`

&#x20; - `\_compute\_image\_page\_stats()` — per-page text-char-count vs.

&#x20;   image-area-coverage ratio

&#x20; - `extract\_pdf()` now also returns `"image\_pages"`

\- `backend/app/services/fraud\_detectors.py`

&#x20; - `detect\_image\_only\_pages(image\_pages)` → `image\_only\_page` signal (high)

\- `backend/app/services/ocr\_helper.py` (NEW FILE)

&#x20; - `ocr\_page\_text()` — rasterises a flagged page and runs Tesseract OCR

&#x20;   via `pytesseract`. Degrades gracefully (same pattern as your existing

&#x20;   `pikepdf` optional-import) if `pytesseract` or the Tesseract binary

&#x20;   isn't installed — the fraud signal still fires either way.

&#x20; - \*\*You need the Tesseract binary installed separately from the pip

&#x20;   package\*\* — see comments in `requirements.txt`.



\## 4. Trust Score Badge

\- `backend/app/services/trust\_score.py` (NEW FILE)

&#x20; - `compute\_trust\_score(fraud\_summary, ai\_content\_score, true\_match\_score)`

&#x20; - Weighted blend: 60% fraud signals, 25% AI-content/human-authorship,

&#x20;   15% job-match (only when a JD was supplied — weights renormalise to

&#x20;   85/15→100% split otherwise so the score never penalises a resume for

&#x20;   an optional feature the recruiter didn't use)

&#x20; - Returns `{score, label, emoji, color, breakdown, weights}`

&#x20; - `label` is one of `Verified` (🟢 ≥75) / `Caution` (🟡 45-74) /

&#x20;   `High Risk` (🔴 <45)



\## Wiring

\- `backend/app/models.py` — `ScanResult` gained `trust\_score` (Float) and

&#x20; `trust\_label` (String) columns.

\- `backend/scripts/migrate\_trust\_score.py` (NEW FILE) — \*\*run this once\*\*

&#x20; against your existing `ats\_fraud.db` before starting the server, or the

&#x20; ORM will error on the missing columns:

&#x20; ```bash

&#x20; cd backend

&#x20; python -m scripts.migrate\_trust\_score

&#x20; ```

&#x20; (Fresh installs / a deleted `ats\_fraud.db` don't need this — SQLAlchemy

&#x20; will create the columns from scratch.)

\- `backend/app/routers/scan.py` — passes `metadata`, `word\_order`,

&#x20; `image\_pages` into `run\_all\_detectors()`; runs OCR on any page flagged

&#x20; image-only; computes and stores the Trust Score; all new data

&#x20; (`trust\_score`, `word\_order`, `image\_pages`, `ocr\_results`) is included

&#x20; in the `POST /scan` response.

\- `backend/app/routers/report.py` + `backend/app/services/forensic\_report.py`

&#x20; — the forensic PDF report's cover page now shows the Trust Score badge

&#x20; above the existing severity-summary table. Old scans (pre-migration,

&#x20; `trust\_score IS NULL`) get it recomputed on the fly so old reports still

&#x20; work.

\- `frontend/app.py` — new "Trust Score" section (prominent gauge + badge)

&#x20; right after the case-file submission step; new expanders for

&#x20; "Layer-order forensics", "Image-only page check", and OCR-recovered text.

\- `backend/requirements.txt` — added `Pillow` and `pytesseract` (optional;

&#x20; install notes for the Tesseract system binary included inline).

\- `backend/tests/test\_phase5\_features.py` (NEW FILE) — unit tests for all

&#x20; four features; all passing as pure-function tests

&#x20; (`pytest tests/test\_phase5\_features.py -v`).



\## Quick start after unzipping

```bash

cd backend

python -m venv .venv \&\& source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows

pip install -r requirements.txt

python -m scripts.migrate\_trust\_score      # only if reusing the bundled ats\_fraud.db

uvicorn app.main:app --reload



\# in a second terminal

cd frontend

streamlit run app.py

```



Optional, for the OCR-bypass check to actually recover text (the fraud

signal itself works either way):

\- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki

\- macOS: `brew install tesseract`

\- Linux: `sudo apt install tesseract-ocr`

