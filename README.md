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

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the recommended walkthrough and [docs/extraction-evaluation.md](docs/extraction-evaluation.md) for the current anonymized evaluation set.

## Prototype boundaries

The ingestion adapter uses direct PDF text extraction and Tesseract/PyMuPDF OCR when those local dependencies are available. The sample report is an explicit demo action, not an upload fallback. LLM extraction, authentication, cloud storage, and production privacy controls remain future work. This is not a certified medical device and does not provide diagnosis or treatment advice.
