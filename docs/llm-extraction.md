# Optional LLM Extraction Adapter

The production upload flow remains deterministic by default. Set `LLM_EXTRACTION_TOKEN` to opt into OpenRouter's free router model, or set `LLM_EXTRACTION_URL` for another OpenAI-compatible JSON provider. The default OpenRouter model is `openrouter/free`; override it with `LLM_EXTRACTION_MODEL`. The endpoint receives:

```json
{"prompt":"...","text":"normalized report text"}
```

It may return the fixed extraction object directly or as a JSON string in an `output` field. The response is treated as untrusted input and must pass Pydantic schema validation, ISO date validation, numeric/type checks, reference-range validation, duplicate-test checks, normalization, and plausibility review.

If the endpoint is missing, unavailable, returns malformed JSON, or fails validation, the deterministic parser is used. No model response is written to SQLite before validation.

The configured provider is attempted at most twice. A successful response is merged with the deterministic result; deterministic values remain authoritative when the two disagree, and the row receives `review_required: true` plus `extraction_conflict: true`. Reports expose `extraction_provider`, `fallback_used`, and `fallback_reason` metadata without logging report text, raw model output, or credentials.

The adapter prompt includes examples for clean rows, multi-column tables, OCR-corrupted names, and missing information. The model is instructed to extract only data, never diagnose, and lower confidence instead of guessing.