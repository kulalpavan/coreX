# Specification Sheet — AI-Powered Medical Report Simplifier (H2)

Companion to `system_design.md`. This document defines *what* must be built and *how it will
be judged internally*, so the team can build against a checklist rather than a vibe.

## 1. Functional Requirements

Priority key: **M** = Must have (MVP, demo will look broken without it), **S** = Should have
(strong differentiator, build if time allows), **C** = Could have (stretch/polish).

| ID | Requirement | Priority |
|---|---|---|
| FR1 | User can upload a report as PDF, JPG, or PNG | M |
| FR2 | System OCRs image-based reports and directly parses text from born-digital PDFs | M |
| FR3 | System extracts test name, value, unit, reference range, flag, and date per result | M |
| FR4 | Extraction returns a confidence score per field | M |
| FR5 | User can review extracted fields against the source document and correct them before confirming | M |
| FR6 | System generates a plain-language explanation per confirmed test result | M |
| FR7 | Explanations never contain diagnostic, prescriptive, or alarm-toned language (enforced by guardrail, not just prompt) | M |
| FR8 | Every explanation view and export includes a visible medical disclaimer | M |
| FR9 | System maps synonymous test names/units to a canonical form for cross-report comparison | S |
| FR10 | User can view a trend chart + table for any test with ≥2 confirmed data points | S |
| FR11 | User can export a PDF summary containing the structured table, explanations, and disclaimer | M |
| FR12 | User can delete their uploaded reports and derived data | S |
| FR13 | System flags low-confidence/unreadable reports instead of silently guessing | M |
| FR14 | Trend view includes a neutral, non-interpretive one-line description of movement (not "improving/worsening") | S |
| FR15 | Multiple report types supported out of the box (CBC, lipid profile, thyroid, liver, kidney panels) | S |
| FR16 | Support for additional report layouts via config/prompt update, not code rewrite | C |
| FR17 | Multi-report/multi-date dashboard view summarizing all tracked tests at a glance | C |

## 2. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR1 | Guardrail check runs synchronously on every generated explanation before display — no explanation reaches the UI unchecked |
| NFR2 | End-to-end pipeline (upload → structured review table) completes within a demo-friendly time (target: under ~15s for a typical single-page report on the demo machine) |
| NFR3 | Raw documents and structured data are not exposed to any component beyond the pipeline; no third-party logging of full report contents |
| NFR4 | UI clearly communicates this is a prototype, not a certified medical device, in-app (not just in a README) |
| NFR5 | Extraction review table remains usable/correctable even when confidence is low, never blocking the user from proceeding manually |
| NFR6 | System degrades gracefully on unsupported file types/languages with a clear message, not a crash |

## 3. Core User Stories

1. *As a patient*, I upload a photo of my lab report and see the individual test values pulled
   out into a table, so I don't have to decode dense report formatting myself.
2. *As a patient*, I can fix a value the system misread before anything is saved, so I trust
   what gets stored and explained.
3. *As a patient*, I read a short explanation of each test in plain language, with a clear
   note that this isn't a diagnosis, so I know what the numbers mean without being told what's
   "wrong with me."
4. *As a patient with multiple past reports*, I see how my cholesterol/HbA1c/etc. has changed
   over time, so I can bring an informed picture to my next doctor visit.
5. *As a patient*, I export a clean PDF of my simplified report to share with a caregiver or
   doctor, disclaimer included.

## 4. Data Model

```
Patient (profile — no verified identity required for MVP)
  - id
  - display_name
  - created_at

Report
  - id
  - patient_id (FK → Patient)
  - raw_file_ref (path/URL to stored original)
  - report_date
  - source_type (pdf_text | pdf_scanned | image)
  - ocr_confidence (nullable)
  - status (pending_review | confirmed)
  - created_at

TestResult
  - id
  - report_id (FK → Report)
  - canonical_test_id (FK → TestDictionary, nullable if unmapped)
  - raw_test_name (as it appeared on the report)
  - value
  - unit
  - reference_range_low (nullable)
  - reference_range_high (nullable)
  - flag (H | L | normal | null)
  - extraction_confidence (0.0–1.0)
  - user_corrected (boolean)
  - explanation_text (nullable until generated)

TestDictionary (canonical reference)
  - id
  - canonical_name
  - synonyms (list)
  - canonical_unit
  - unit_conversions (map of unit → conversion factor, where safe)
  - plain_description ("what this test measures")

ExportRecord (optional, for audit/demo)
  - id
  - patient_id
  - generated_at
  - report_ids_included
```

## 5. API Endpoints (proposed)

```
POST   /api/reports/upload
  → multipart file upload; returns { report_id, status: "processing" }

GET    /api/reports/{report_id}/extraction
  → returns candidate TestResult[] with confidence scores, pending review

POST   /api/reports/{report_id}/confirm
  body: corrected TestResult[]
  → persists confirmed results, triggers explanation generation

GET    /api/reports/{report_id}/explanations
  → returns TestResult[] with explanation_text populated

GET    /api/patients/{patient_id}/trends/{canonical_test_id}
  → returns [{ date, value, unit }] time series + one-line trend description

POST   /api/reports/{report_id}/export
  → returns a generated PDF (or a URL to download it)

DELETE /api/patients/{patient_id}/data
  → deletes all reports/results for that patient profile
```

**Example extraction response:**
```json
{
  "report_id": "r_123",
  "results": [
    {
      "raw_test_name": "Hb",
      "value": 11.2,
      "unit": "g/dL",
      "reference_range_low": 12.0,
      "reference_range_high": 15.5,
      "flag": "L",
      "date": "2026-08-14",
      "extraction_confidence": 0.94
    }
  ]
}
```

## 6. Input / Output Formats

- **Accepted uploads:** PDF, JPG, PNG (define a max file size, e.g. 15 MB, for demo stability).
- **Extraction schema:** fixed JSON array as shown in §5 — this is the contract between the
  Extraction Engine and everything downstream; changes to it should be versioned, not silent.
- **Export format:** single PDF per report (or per patient, for a multi-report summary),
  disclaimer on every page.

## 7. Screens (UI scope)

1. **Upload** — file picker/drag-drop, camera capture on mobile, upload progress.
2. **Review & Correct** — split view: original document alongside the editable extracted table.
3. **Explanation** — per-test card with plain-language text, value, range, flag, disclaimer
   banner always visible.
4. **Trends** — test picker → line chart + underlying value table + one-line trend note.
5. **Export** — preview + download button for the PDF summary.
6. *(Should-have)* **Dashboard** — all tracked tests at a glance across the patient's reports.

## 8. Suggested Build Timeline (typical hackathon window)

| Phase | Focus | Deliverable at end of phase |
|---|---|---|
| 0 | Repo setup, architecture skeleton, CI-lite (lint/format), empty endpoints | Running skeleton app, first real commits |
| 1 | Upload + OCR/PDF-text pipeline | Raw text extracted and viewable for a sample report |
| 2 | Extraction Engine + JSON schema + confidence | Structured table (uncorrected) from a real report |
| 3 | Review/correction UI + persistence | Confirmed, stored TestResult records |
| 4 | Explanation Engine + Guardrail middleware | Safe plain-language explanations, guardrail test suite passing |
| 5 | Normalization/canonical mapping + Trends | Working trend chart across ≥2 reports |
| 6 | Export (PDF) + disclaimer placement | Downloadable summary PDF |
| 7 | Polish, edge-case handling, demo script, README | Demo-ready build |

Adjust phase count to the actual hackathon duration; the ordering (pipeline stage by pipeline
stage) is the part worth keeping, since each phase produces something independently demoable.

## 9. Evaluation / Success Metrics

Map internal testing to what judges are likely to score:

| Metric | How it's measured | Judging dimension it supports |
|---|---|---|
| Field-level extraction precision/recall on labeled sample set | Manual comparison against ground truth | Technical soundness |
| Guardrail pass rate on adversarial prompt set | Automated test suite (see system_design §11) | Safety / responsible AI |
| End-to-end latency on a typical report | Timed run | Feasibility / performance |
| Number of report types correctly handled | Count against target list (§ FR15) | Scope coverage |
| Clarity of explanation (readability check, e.g. no jargon left unexplained) | Manual review against a plain-language checklist | Usability |
| Disclaimer visibility | Present on every explanation view and every export page | Compliance/safety |

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OCR fails badly on phone-camera photos | Pre-processing (deskew/contrast), fallback to manual entry, confidence flagging |
| LLM extraction hallucinates a value | Confidence scoring + mandatory human review step before anything is stored |
| Explanation drifts into diagnostic language | Two-layer guardrail (prompt constraints + independent rule-based checker), adversarial test suite |
| Limited time to cover many lab formats | Prioritize FR15's fixed list; design canonical dictionary so new formats are additive, not a rewrite |
| Judges probe "what disease do I have?" live | Guardrail must handle this as a first-class test case, not an afterthought |

## 11. Team / Skill Mapping (summary — see `skill.md` for the implementation guide)

| Area | Skills needed |
|---|---|
| Frontend | React, basic charting library, file upload/camera handling |
| Backend | Python (FastAPI) or Node, REST API design |
| OCR/Document processing | Tesseract or equivalent, PDF text extraction libraries |
| AI/LLM integration | Prompt design, JSON-schema-constrained output, evaluating model output |
| Data | PostgreSQL schema design, unit conversion logic |
| Safety/QA | Writing adversarial test cases, guardrail rule design |
| DevOps (light) | Environment setup, deployment for demo, git hygiene for commit-history review |
