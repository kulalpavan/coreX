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

## Prototype boundaries

The ingestion adapter currently handles text-bearing files and includes a deterministic sample fallback for a demo report. PDF OCR/LLM providers, persistent database storage, authentication, and production privacy controls are intentionally left as replaceable next steps. This is not a certified medical device and does not provide diagnosis or treatment advice.
