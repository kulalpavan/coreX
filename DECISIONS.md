# Decisions

## 2026-09-19: Keep the first slice local and deterministic

The MVP uses an in-memory FastAPI store and a deterministic extraction adapter so the upload-to-review flow can be demonstrated without API keys, third-party logging, or an unreliable model dependency. The adapter boundary is ready for PDF/OCR and schema-constrained LLM implementations later.

## 2026-09-19: Review before explanation

Explanations are generated only after confirmation. This makes the safety boundary visible in the UI and prevents an unreviewed candidate value from being presented as patient-facing information.
