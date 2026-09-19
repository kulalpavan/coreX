# Extraction Evaluation

This is the initial anonymized evaluation set for the prototype extraction boundary.

| Fixture | Coverage | Expected review behavior |
|---|---|---|
| `clean_report.txt` | Typed report date, units, ranges, and flags | Extract the three recognizable rows with confidence scores |
| `noisy_report.txt` | Missing value and implausible numeric value | Keep rows reviewable and lower confidence; never invent a value |
| Direct test cases | Missing units, missing ranges, unknown text, safe conversions | Return nulls/errors clearly and preserve unsupported units |

The automated checks live in `backend/tests/test_extraction.py` and `backend/tests/test_backend_regressions.py`. They currently verify schema behavior, low-confidence handling, canonical mapping, safe unit conversion, unsupported conversion preservation, patient-scoped deletion, and SQLite reload behavior.

A future labeled-report pass should add, for each field, the expected value and the extracted value, then record:

- Field precision = correct extracted fields / all extracted fields.
- Field recall = correct extracted fields / all expected fields.
- Report-level failure reasons for unreadable, unsupported, or ambiguous input.

Accuracy numbers should only be added after the team labels real anonymized sample reports.
