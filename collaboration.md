# Clarify Labs Collaboration Guide

This document splits the Clarify Labs MVP across four team members. Each person owns a complete area, but the project only works when the interfaces between those areas are agreed early and checked regularly.

## Shared Product Understanding

Clarify Labs is a prototype that turns a patient's PDF, JPG, or PNG laboratory report into a reviewable plain-language summary.

The most important product rule is:

> The system must never silently present an extracted value as final. The patient reviews and confirms extracted values before explanations are generated or data is treated as confirmed.

The system is not a diagnostic tool. It must not diagnose a disease, prescribe medication, imply urgency, or tell a patient what treatment to take. Every explanation and exported summary must include the medical disclaimer.

## Team Roles At A Glance

| Member | Primary ownership | Main question they answer |
|---|---|---|
| Member 1 | Frontend and user experience | Can a patient upload, review, correct, confirm, and understand the report? |
| Member 2 | Backend API and persistence | Are reports, candidate values, confirmations, and patient data handled consistently? |
| Member 3 | OCR, extraction, and normalization | Can messy report input become structured data with honest confidence scores? |
| Member 4 | Explanation safety, trends, export, and QA | Are outputs safe, useful, traceable, and ready to demonstrate? |

Use real names in the assignment table below before development begins.

| Role | Name | Backup |
|---|---|---|
| Member 1: Frontend and UX | ____________________ | ____________________ |
| Member 2: Backend and persistence | ____________________ | ____________________ |
| Member 3: OCR and extraction | ____________________ | ____________________ |
| Member 4: Safety, trends, export, and QA | ____________________ | ____________________ |

## Working Rules

### 1. Keep ownership clear

The owner of a module is responsible for implementation, tests, documentation, and explaining the design to the rest of the team. Ownership does not mean working alone; it means there is one person accountable for the result.

### 2. Agree on contracts before integration

Do not wait until the end to connect frontend and backend. Use the API shapes in this document and in `Implementation/specsheet.md` as the shared contract. If a contract must change, update the documentation and tell the team before changing code.

### 3. Work in small commits

Use commits that describe one meaningful change, for example:

```text
Add editable extraction review table
Add report upload validation
Add confidence-aware extraction adapter
Add explanation guardrail tests
```

Do not combine unrelated frontend, OCR, export, and documentation changes in one commit.

### 4. Never commit sensitive reports

Sample medical reports must stay local or use anonymized fixtures. Do not commit real names, dates of birth, addresses, patient identifiers, or full report images. Do not print full report contents in logs.

### 5. Every feature needs a visible failure state

The UI must show a useful message for unsupported files, unreadable reports, low-confidence extraction, API failure, missing ranges, and blocked explanations. A silent empty state is not acceptable for this product.

### 6. Review before merge

Before merging a branch, the owner should provide:

- What changed.
- Which files changed.
- How to run it.
- What test or manual check passed.
- Any known limitation.

## Shared Data Contract

The extraction layer returns candidate results in this shape:

```json
{
  "raw_test_name": "Hb",
  "value": 11.2,
  "unit": "g/dL",
  "reference_range_low": 12.0,
  "reference_range_high": 15.5,
  "flag": "L",
  "report_date": "2026-08-14",
  "extraction_confidence": 0.94,
  "user_corrected": false
}
```

Rules for this contract:

- `raw_test_name` must preserve the name as it appeared in the source report.
- `value`, range values, and confidence must be numeric when present.
- Unknown or unreadable fields are `null`; they must not be guessed.
- `extraction_confidence` is between `0.0` and `1.0`.
- `user_corrected` is `false` for model/OCR output and `true` after a user edits that field.
- `flag` may be `H`, `L`, `normal`, or `null` when the source does not state a flag.
- Explanations are generated only after confirmation.

## Member 1: Frontend And User Experience

### Ownership

Own the React/Vite application, patient workflow, visual hierarchy, editable review table, API loading states, and responsive behavior.

### Required screens

#### Upload screen

- PDF, JPG, and PNG file picker.
- Drag-and-drop support if time allows.
- File type and 15 MB size guidance.
- Upload progress or processing state.
- Clear error when the backend rejects a file.
- A visible prototype disclaimer or trust statement.
- A sample-report path for the demo when real OCR is unavailable.

#### Review and correction screen

- Original filename and report status.
- Extracted test name, value, unit, reference range, flag, date, and confidence.
- Every field editable.
- Low-confidence fields visually distinct but still editable.
- No confirmation button disabled solely because confidence is low. The user must be allowed to correct data manually.
- Clear action to confirm the reviewed values.

#### Explanation screen

- One result card or row per confirmed test.
- Value, unit, source range, and neutral explanation.
- Medical disclaimer visible without requiring a hidden menu or hover.
- Clear path to review another report.

#### Trends and export placeholders or screens

When those features are available, integrate them into the existing workflow instead of creating an unrelated second app.

### Frontend acceptance checks

- A patient can complete the sample flow without reading developer documentation.
- The review table remains usable on a small laptop and mobile-width viewport.
- Keyboard focus is visible on inputs and buttons.
- Loading, success, empty, and error states are all represented.
- The UI never says that a result is a diagnosis or treatment recommendation.
- The disclaimer appears on the explanation screen and export preview.

### Handoffs

Receive from Member 2:

- API base URL.
- Upload request and response shape.
- Extraction response shape.
- Confirmation request and response shape.
- Error response format.

Provide to Member 2:

- Exact fields the review table edits.
- Any frontend assumptions about nullable fields.
- A short recording or screenshots of the upload-to-confirm flow.

### Suggested files

- `frontend/src/main.jsx`
- `frontend/src/styles.css`
- Additional focused components under `frontend/src/` as the UI grows.

## Member 2: Backend API And Persistence

### Ownership

Own FastAPI routes, request validation, report lifecycle, persistence, deletion, CORS/configuration, and the stable service boundary used by the frontend and processing modules.

### Required API behavior

Implement and document:

```text
POST   /api/reports/upload
GET    /api/reports/{report_id}/extraction
POST   /api/reports/{report_id}/confirm
GET    /api/reports/{report_id}/explanations
GET    /api/patients/{patient_id}/trends/{canonical_test_id}
POST   /api/reports/{report_id}/export
DELETE /api/patients/{patient_id}/data
```

For the first demo, in-memory storage is acceptable. The persistence boundary must still be isolated so it can later be replaced by PostgreSQL without changing frontend contracts.

### Report lifecycle

Use explicit states:

```text
pending_review -> confirmed
```

Rules:

- Upload creates a report in `pending_review`.
- Candidate extraction results are not confirmed results.
- Confirmation replaces or updates candidates with the user-reviewed values.
- Explanations are generated only for confirmed results.
- Delete removes raw report data and all derived results for the patient.
- Invalid report IDs return a clear 404.
- Confirmation of a missing or malformed result returns a clear validation error.

### Backend acceptance checks

- Reject unsupported MIME types.
- Reject files over 15 MB.
- Do not log full report text or raw uploaded bytes.
- Validate confidence values from 0 through 1.
- Preserve `user_corrected` values from the confirmation request.
- Return a stable JSON error shape.
- Add an API smoke test for upload, extraction, confirmation, explanation, and deletion.

### Handoffs

Receive from Member 3:

- Extraction adapter function/interface.
- Candidate result schema.
- Processing failure and low-confidence states.

Provide to Member 1:

- API examples and local run instructions.
- Stable CORS settings for the Vite URL.
- Test data or a seeded demo endpoint if useful.

Provide to Member 4:

- Confirmed result retrieval method.
- Patient/report identifiers needed for trends and export.
- Deletion behavior and audit expectations.

### Suggested files

- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/routes/`
- `backend/app/storage/`
- `backend/tests/`

## Member 3: OCR, Extraction, And Normalization

### Ownership

Own the path from uploaded document to candidate structured results: file classification, PDF text extraction, OCR preprocessing, schema-constrained extraction, confidence scoring, validation, canonical test mapping, and sample fixtures.

### Ingestion behavior

Branch by source type:

- Born-digital PDF: extract its text layer directly with PyMuPDF or pdfplumber.
- Scanned PDF: render pages to images and run OCR.
- JPG/PNG: preprocess and run OCR.

For image input, the baseline preprocessing should consider deskewing, contrast normalization, and readable resolution. If OCR quality is poor, return a low-confidence result or processing warning rather than inventing values.

### Extraction behavior

Use a fixed JSON schema and defensive parsing. The extraction prompt or adapter must:

- Return only the expected result structure.
- Preserve raw test names.
- Return `null` for unreadable fields.
- Lower confidence when OCR text is garbled or a row is ambiguous.
- Include examples for clean single-column, multi-column, and noisy reports.
- Never fill a missing reference range from memory.

If an LLM provider is not configured, keep a deterministic local adapter for the demo. The adapter must have the same interface as the future provider.

### Plausibility checks

Add rough per-test checks for obvious OCR mistakes. These checks downgrade confidence and flag a value for review; they do not silently delete a candidate.

Examples:

- Glucose values with implausible magnitudes.
- Hemoglobin values with impossible digit shifts.
- Reference low values greater than reference high values.
- Missing units or dates.

### Normalization

Create a small `TestDictionary` for the target report families:

- CBC.
- Lipid profile.
- Thyroid panel.
- Liver panel.
- Kidney panel.

Start with synonyms such as `Hb`, `HGB`, and `Hemoglobin`. Unit conversion is allowed only when the conversion is safe and documented. Unmapped tests must remain visible under their raw name.

### Extraction acceptance checks

- Test clean text input with expected fields.
- Test OCR-noisy input and verify null/low-confidence behavior.
- Test malformed model JSON and verify fallback or retry behavior.
- Test physiological plausibility downgrade behavior.
- Test synonym mapping and at least two safe unit conversions.
- Maintain a small hand-labeled fixture table with precision/recall notes.

### Handoffs

Provide to Member 2:

- Versioned result schema.
- Adapter entry point.
- Error types and low-confidence semantics.
- Sample fixtures without real patient identifiers.

Provide to Member 1:

- Confidence display guidance.
- Which fields may be null.
- Example results containing high, medium, and low confidence.

Provide to Member 4:

- Canonical test IDs.
- Normalized units.
- Report dates and confirmed-result query requirements.

### Suggested files

- `backend/app/ingestion.py`
- `backend/app/extraction.py`
- `backend/app/normalization.py`
- `backend/tests/fixtures/`
- `backend/tests/test_extraction.py`

## Member 4: Safety, Trends, Export, And Quality Assurance

### Ownership

Own the independent explanation guardrail, safe explanation templates or provider integration, trend behavior, PDF export, adversarial tests, end-to-end QA, and demo readiness.

### Explanation engine

Each explanation should follow this structure:

1. What the test measures in everyday language.
2. The confirmed value and unit.
3. The reference range printed on the report.
4. Whether the value is inside, above, or below that reported range.
5. A neutral instruction to discuss the result with a clinician.

The explanation must not claim what condition the patient has or what they should do medically.

### Guardrail

Implement the guardrail as an independent function or middleware layer, not only as a prompt instruction. It should scan every generated explanation before it is stored or displayed.

At minimum, test patterns involving:

- Diagnosis requests.
- Disease names presented as conclusions.
- Medication or treatment instructions.
- Alarm language such as dangerous, emergency, or urgent.
- Certainty language such as definitely or proves.

On a violation, reject and regenerate with a stricter template or return a safe fallback. The UI must never receive the unchecked text.

### Trends

Implement:

```text
GET /api/patients/{patient_id}/trends/{canonical_test_id}
```

Return dates, values, units, and a neutral movement sentence. Use wording such as:

```text
This value moved from 186 mg/dL on 2026-06-10 to 214 mg/dL on 2026-08-14.
```

Do not use `improving`, `worsening`, `healthy`, `unhealthy`, or diagnostic interpretations.

### Export

Generate a PDF containing:

- Patient-entered display label, not verified identity.
- Report date and source filename.
- Structured confirmed-result table.
- Explanation for each result.
- Trend table or chart when available.
- Disclaimer in the header or footer of every page.

### QA acceptance checks

- Run the adversarial guardrail suite.
- Verify no explanation reaches the UI before confirmation.
- Verify every explanation view includes the disclaimer.
- Verify every PDF page includes the disclaimer.
- Upload two reports and verify one canonical test produces a two-point trend.
- Test deletion and confirm reports/results are no longer retrievable.
- Run the complete fresh-clone setup flow before demo day.

### Handoffs

Receive from Member 2:

- Confirmed result endpoint.
- Patient and report identifiers.
- Export request contract.

Receive from Member 3:

- Canonical names and units.
- Confidence semantics.
- Sample report fixtures.

Provide to Member 1:

- Explanation response shape.
- Disclaimer text.
- Trend and export UI data requirements.

### Suggested files

- `backend/app/guardrail.py`
- `backend/app/explanations.py`
- `backend/app/trends.py`
- `backend/app/export.py`
- `backend/tests/test_guardrail.py`
- `backend/tests/test_end_to_end.py`

## Phase Ownership And Schedule

### Phase 0: Skeleton and contracts

All members:

- Agree on names and ownership.
- Read `Implementation/specsheet.md` and `Implementation/system_design.md`.
- Confirm the shared result schema.
- Run frontend and backend locally.
- Create anonymized fixtures.

Member 1 creates the initial upload screen. Member 2 stabilizes API routes. Member 3 creates the extraction adapter interface. Member 4 creates the first guardrail test cases.

**Exit check:** both apps run independently and the team can explain the upload-to-confirmation data flow.

### Phase 1: Ingestion and extraction

Member 2 and Member 3 lead. Member 1 connects the upload and review screens. Member 4 records extraction failures and checks that low confidence is visible.

**Exit check:** a clean sample report and a noisy sample report produce reviewable candidate rows.

### Phase 2: Review and confirmation

Member 1 and Member 2 lead. Member 3 supports schema and validation issues. Member 4 verifies that only confirmed values receive explanations.

**Exit check:** deliberately edit a value, confirm it, and verify the corrected value is used later.

### Phase 3: Explanation and safety

Member 4 leads. Member 2 wires the guardrail into the backend. Member 1 displays the disclaimer and safe fallback states. Member 3 reviews whether explanations use the reported range rather than invented clinical ranges.

**Exit check:** adversarial prompts cannot produce unchecked diagnostic or prescriptive text.

### Phase 4: Trends and export

Member 4 leads with Member 2. Member 3 owns canonical mapping and units. Member 1 builds chart/table and download views.

**Exit check:** two confirmed reports produce a neutral trend and a PDF with a disclaimer on every page.

### Phase 5: Demo hardening

All members participate.

- Member 1 rehearses the patient workflow.
- Member 2 verifies clean startup and API errors.
- Member 3 prepares the best sample reports and explains confidence behavior.
- Member 4 runs the QA checklist and leads the safety demonstration.

## Integration Checklist

Before calling the MVP complete, verify all of the following:

- [ ] Upload accepts PDF, JPG, and PNG.
- [ ] Files over 15 MB and unsupported types are rejected clearly.
- [ ] Born-digital PDF text extraction is separate from image OCR.
- [ ] Candidate results show field-level confidence.
- [ ] Low-confidence fields can still be edited and confirmed.
- [ ] User corrections are persisted as `user_corrected: true`.
- [ ] Explanations are generated only after confirmation.
- [ ] Guardrail runs synchronously before display and storage.
- [ ] Adversarial guardrail tests pass.
- [ ] Every explanation view shows the disclaimer.
- [ ] Canonical test mapping supports CBC, lipid, thyroid, liver, and kidney examples.
- [ ] Two confirmed reports produce a neutral trend view.
- [ ] Export includes the structured table, explanations, and disclaimer on every page.
- [ ] Delete removes uploaded and derived data.
- [ ] No real patient data is committed or printed in logs.
- [ ] A fresh clone can be started using the README instructions.

## Demo Script

The team should demonstrate the product in this order:

1. Open the upload screen and state that this is a prototype, not a medical device.
2. Upload a clean sample report.
3. Show extracted values and confidence scores.
4. Deliberately change one value in the review table.
5. Confirm the report and show that the explanation uses the corrected value.
6. Show the disclaimer and explain that no diagnosis is generated.
7. Attempt an adversarial question such as “What disease does this indicate?” and show the guardrail fallback.
8. Upload or load a second dated report with a shared canonical test.
9. Show the neutral trend sentence and underlying values.
10. Export the summary and show the disclaimer on every page.
11. Demonstrate the delete-data action.

## Definition Of Done

The team is done with the MVP when a new person can follow the README, upload an anonymized report, review and correct extracted values, confirm them, read a guarded explanation, view a trend from two reports, export a disclaimer-bearing PDF, and delete the demo data without manual database edits.
