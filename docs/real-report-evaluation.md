# Real-Report Evaluation Workflow

## Status

Evaluation infrastructure: READY.

Real-world accuracy measurement: NOT YET POSSIBLE in this repository because no genuinely photographed or scanned anonymized reports have been supplied with labeled ground truth.

Do not place identifiable medical reports in git. Keep them in a local-only directory.

## Add a report

Create a local directory outside the repository, for example:

```text
C:\clarify-labs-private-evaluation\
  report_001.pdf
  report_002.jpg
  report_003.png
  ground_truth.json
```

Use this ground-truth shape, matching the normalized extraction schema:

```json
{
  "reports": [
    {
      "report_id": "report_001",
      "source_file": "report_001.jpg",
      "report_date": "2026-09-19",
      "tests": [
        {
          "test_name": "Hemoglobin",
          "value": 13.5,
          "unit": "g/dL",
          "reference_range": {"low": 12.0, "high": 16.0}
        }
      ]
    }
  ]
}
```

The values in ground truth should represent the post-normalization canonical unit. For example, if a source glucose value is `5.0 mmol/L`, record the expected normalized value as `90.0 mg/dL`.

## Run evaluation

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m app.evaluation --fixture-dir C:\clarify-labs-private-evaluation --ground-truth C:\clarify-labs-private-evaluation\ground_truth.json
```

The output reports separate precision and recall for test name, value, unit, reference range, and date. It also emits failures tagged by likely stage: OCR/ingestion, text normalization, test-name matching, value parsing, unit parsing, reference-range parsing, or date extraction.

## Interpretation

- OCR quality: whether readable source text was produced and whether OCR confidence is acceptable.
- Extraction quality: whether structured fields match ground truth.
- Validation quality: whether malformed, implausible, or incomplete fields are flagged instead of guessed.

The included `backend/tests/fixtures/image_samples` files are synthetic scan proxies only. Their passing checks validate the workflow and file format, not real-world OCR accuracy.
