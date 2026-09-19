# Extraction Evaluation

This is the initial anonymized evaluation set for the prototype extraction boundary.

| Fixture | Coverage | Expected review behavior |
|---|---|---|
| `clean_report.txt` | Typed report date, units, ranges, and flags | Extract the three recognizable rows with confidence scores |
| `noisy_report.txt` | Missing value and implausible numeric value | Keep rows reviewable and lower confidence; never invent a value |
| Direct test cases | Missing units, missing ranges, unknown text, safe conversions | Return nulls/errors clearly and preserve unsupported units |

The automated checks live in `backend/tests/test_extraction.py`, `backend/tests/test_evaluation.py`, and `backend/tests/test_end_to_end.py`. They verify schema behavior, low-confidence handling, canonical mapping, safe unit conversion, unsupported conversion preservation, patient-scoped deletion, SQLite reload behavior, and the complete upload-to-delete workflow.

The current three-fixture baseline is:

| Fixture set | Field-name precision | Field-name recall |
|---|---:|---:|
| Clean typed report | 1.00 | 1.00 |
| Clarify Labs 10-row table | 1.00 | 1.00 |
| OCR-noisy report | 1.00 | 1.00 |

These are deterministic anonymized fixtures, not a claim about production accuracy. More photographed reports must be labeled before using these numbers as a broader quality estimate.

A future labeled-report pass should add, for each field, the expected value and the extracted value, then record:

- Field precision = correct extracted fields / all extracted fields.
- Field recall = correct extracted fields / all expected fields.
- Report-level failure reasons for unreadable, unsupported, or ambiguous input.

Accuracy numbers should only be added after the team labels real anonymized sample reports.

## Image OCR corpus

`backend/tests/fixtures/image_samples/` contains three synthetic scan proxies for CBC, lipid, and thyroid panels plus `ground_truth.json`. They exercise the image upload path without containing real patient information. They are intentionally labeled synthetic and are not presented as real photographed-report accuracy. On a demo machine with Tesseract installed, run the image files through `ingest_document()` and record field precision/recall separately from the deterministic text/PDF baseline.

The application now reports a clear setup error when the Tesseract executable is missing, rather than returning an opaque server traceback.
