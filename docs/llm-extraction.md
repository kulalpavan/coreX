# Optional LLM Extraction Adapter

The production upload flow remains deterministic by default. Set `LLM_EXTRACTION_URL` to opt into an HTTP JSON extraction provider. The endpoint receives:

```json
{"prompt":"...","text":"normalized report text"}
```

It may return the fixed extraction object directly or as a JSON string in an `output` field. The response is treated as untrusted input and must pass Pydantic schema validation, ISO date validation, numeric/type checks, reference-range validation, duplicate-test checks, normalization, and plausibility review.

If the endpoint is missing, unavailable, returns malformed JSON, or fails validation, the deterministic parser is used. No model response is written to SQLite before validation.

The adapter prompt includes examples for clean rows, multi-column tables, OCR-corrupted names, and missing information. The model is instructed to extract only data, never diagnose, and lower confidence instead of guessing.