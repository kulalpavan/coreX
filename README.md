# Clarify Labs

Clarify Labs is a local prototype that turns a lab report into a reviewable, plain-language summary. It is designed around a human confirmation step: extracted values remain candidates until the user checks and confirms them.

## Run locally

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal. The frontend uses `http://localhost:8000` for the API.

## Working MVP flow

Upload a report, review the retained source text beside the extracted fields, correct any low-confidence values, confirm the report, read the guarded explanation, view trends after two confirmed data points, and export a disclaimer-bearing PDF. The extraction parser recognizes common tabular CBC, lipid, and thyroid rows while filtering report metadata. Confirmed reports are stored in local SQLite at `backend/storage/reports.sqlite3`.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the recommended walkthrough and [docs/extraction-evaluation.md](docs/extraction-evaluation.md) for the current anonymized evaluation set. The architecture is documented in [Implementation/system_design.md](Implementation/system_design.md).

For a fresh clone, run the backend tests with `cd backend; pytest -q` and the frontend build with `cd frontend; npm install; npm run build`. Image OCR additionally requires the Tesseract executable installed and available on `PATH`; text-based PDFs work without it.

The backend health endpoint reports `ocr_available`, `tesseract_version`, and `pdf_text_extraction_available`. See [docs/ocr-setup.md](docs/ocr-setup.md) for Tesseract installation and [docs/real-report-evaluation.md](docs/real-report-evaluation.md) for adding local-only photographed reports and running field-level precision/recall evaluation.

The optional extraction provider is disabled by default. To use OpenRouter's free router model, set `LLM_EXTRACTION_TOKEN`; it defaults to `https://openrouter.ai/api/v1/chat/completions` and model `openrouter/free`. You can override these with `LLM_EXTRACTION_URL` and `LLM_EXTRACTION_MODEL`. Invalid or failed responses automatically fall back to the deterministic parser.

## Prototype boundaries

The ingestion adapter uses direct PDF text extraction and Tesseract/PyMuPDF OCR when those local dependencies are available. The sample report is an explicit demo action, not an upload fallback. LLM extraction, cloud storage, and production privacy controls remain future work. This is not a certified medical device and does not provide diagnosis or treatment advice.
