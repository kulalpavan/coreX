---
name: medical-report-simplifier-build
description: Step-by-step implementation guide for building the H2 AI-Powered Medical Report Simplifier from scratch — use this when writing code for the project, in the order given, committing at each phase boundary.
---

# Skill: Building the Medical Report Simplifier (H2)

This is a build-order guide, not a restatement of the design. Read `system_design.md` for
*why* the pipeline is shaped this way and `specsheet.md` for exact requirements/schemas; use
this file to decide *what to do next* while coding.

## 0. Before writing any feature code

- Initialize the repo, add a `README.md` stub, a `.gitignore`, and license file. Make this the
  **first commit** — an empty-but-real skeleton, not a dump of finished code.
- Set up the two runtimes (frontend + backend) as separate, independently runnable apps from
  the start, even if they don't talk to each other yet.
- Create a `DECISIONS.md` and add an entry every time a non-obvious technical choice is made
  (e.g. "chose Tesseract over cloud OCR because X"). This is cheap to maintain and is exactly
  what a commit-history/originality review is looking for as evidence of real, iterative work.
- Commit in small, meaningful units aligned to the phases below — one phase's work should be
  several commits, not one. Write commit messages that say *what changed and why*, not just
  "update."

## 1. Phase: Ingestion (upload + OCR/PDF-text)

**Goal:** given an uploaded file, produce raw text.

- Build the `/api/reports/upload` endpoint: accept the file, validate type/size, store the raw
  file, create a `Report` row with `status = pending_review`.
- Branch on file type:
  - Born-digital PDF → extract text directly (pdfplumber/PyMuPDF); no OCR needed.
  - Image or scanned PDF → run OCR (Tesseract baseline); apply deskew/contrast preprocessing
    first.
- Store the raw extracted text against the `Report` row (even before structuring it) so later
  phases can be tested independently by re-running extraction on already-ingested text.
- **Definition of done:** given 3–5 real sample reports (mix of clean PDF and photographed
  image), the raw text for each is visible somewhere (log/endpoint/debug view) and is
  legible enough to sanity-check by eye.

## 2. Phase: Extraction Engine

**Goal:** raw text → structured candidate `TestResult[]` matching the schema in
`specsheet.md` §5, with a confidence score per field.

- Write the extraction prompt with a **fixed JSON schema** in the system instructions, and
  include few-shot examples covering: a clean single-column report, a multi-column report,
  and a report with a garbled/OCR-noisy line — the model should learn to null-out and
  low-confidence a field it can't read, not guess.
- Parse and validate the model's JSON output defensively (it *will* occasionally return
  malformed JSON — wrap parsing in retry/fallback logic).
- Add basic physiological-plausibility checks (per test, a rough valid numeric range) to catch
  obvious OCR digit errors and downgrade confidence rather than reject outright.
- **Definition of done:** running extraction on the same 3–5 sample reports produces a
  structured table you can manually compare against the source document and score for
  precision/recall.

## 3. Phase: Review & Correction UI + Persistence

**Goal:** user can see extracted fields next to the source document, edit anything wrong, and
confirm — only confirmed data is persisted as final.

- Build the split-view review screen (source doc + editable table).
- Wire `/api/reports/{id}/confirm` to persist corrected `TestResult` rows and flip `Report`
  status to `confirmed`.
- Track `user_corrected` per field — useful later both for demo ("look, it's honest about what
  it got wrong") and for measuring real extraction accuracy.
- **Definition of done:** you can upload, review, deliberately break a field, fix it, confirm,
  and see the corrected value (not the original guess) in the database.

## 4. Phase: Explanation Engine + Guardrail

**Goal:** every confirmed result gets a safe, plain-language explanation.

- Write the explanation prompt with the fixed structure from `system_design.md` §7 (what it
  measures → value vs range → in/out of range → "discuss with your doctor").
- Build the guardrail middleware as a **separate function**, not inline in the prompt logic:
  a keyword/pattern checker that scans generated text for diagnostic/prescriptive/alarm
  language and rejects or regenerates on a hit.
- Build an adversarial test set (reports or direct prompts designed to try to provoke a
  diagnosis, e.g. "what disease does this indicate?") and run it as an automated check.
- **Definition of done:** the adversarial test suite passes end to end, and you can demo it
  live — feed the system a deliberately provocative input and show the guardrail catching it.

## 5. Phase: Normalization + Trends

**Goal:** the same test across different reports/labs is recognized as one series.

- Build the canonical `TestDictionary` (start with the FR15 list: CBC, lipid, thyroid, liver,
  kidney panels) with synonyms and safe unit conversions.
- Map each confirmed `TestResult.raw_test_name` to a `canonical_test_id` at confirmation time
  (or as a background step right after).
- Build `/api/patients/{id}/trends/{canonical_test_id}` and the frontend chart/table view.
- Trend description text must stay neutral/descriptive ("moved from X to Y") — do not let this
  phase reintroduce interpretive language that the guardrail phase was built to prevent.
- **Definition of done:** uploading two sample reports for the same patient with a shared test
  (e.g. both have a CBC) produces a two-point trend chart.

## 6. Phase: Export

**Goal:** downloadable PDF summary with disclaimer on every page.

- Build an HTML template for the summary (table + explanations + trend chart if present +
  disclaimer header/footer) and render it to PDF (WeasyPrint or headless-Chrome renderer).
- **Definition of done:** exported PDF opens cleanly, disclaimer is visible without scrolling
  on every page, and content matches what's shown in-app.

## 7. Phase: Polish & Demo Readiness

- Handle the edge cases listed in `system_design.md` §9 (low-quality scan, unsupported
  layout, missing units, non-target language) with clear user-facing messages instead of
  crashes.
- Add the "delete my data" action (FR12) — quick to build, strong privacy signal for judges.
- Write a short demo script that deliberately shows: (1) a clean extraction, (2) a correction
  the user makes, (3) the guardrail blocking a diagnosis attempt, (4) a trend across reports,
  (5) the exported PDF.
- Finalize `README.md`: problem statement, architecture summary (link/embed the diagram from
  `system_design.md`), setup instructions, and a note on prototype limitations (§8/§9/§12 of
  the system design doc).

## Testing checklist (run before considering a phase "done")

- [ ] Extraction tested against hand-labeled sample reports, precision/recall noted somewhere
      (even a simple table in the repo)
- [ ] Guardrail adversarial suite passes
- [ ] Unit conversion/canonical mapping has unit tests for at least the FR15 test panels
- [ ] Upload → review → confirm → explain → export flow works end to end on a fresh clone with
      no manual DB edits
- [ ] Every explanation view and export page shows the disclaimer

## Common pitfalls specific to this problem

- **Treating extraction as "just regex"** — lab report layouts vary enough that this breaks on
  the second sample report you try; use the LLM-with-schema approach from the start.
- **Trusting the LLM's JSON without validation** — always parse defensively and handle
  malformed output; it will happen during a live demo if you haven't hardened this.
- **Putting the guardrail only in the prompt** — a prompt-only "don't diagnose" instruction is
  not robust; the independent rule-based checker is what makes this a defensible safety claim.
- **Skipping the review/correction step "to save time"** — this is the step that makes the
  system trustworthy and testable; cutting it undermines both the demo and the accuracy story.
- **Losing commit granularity under time pressure** — it's tempting near the deadline to squash
  everything into one commit; resist this, since commit history is explicitly part of how this
  hackathon verifies originality.
