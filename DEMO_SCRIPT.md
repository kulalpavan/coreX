# Clarify Labs Demo Script

## Setup

1. Start the backend on port 8000.
2. Start the frontend on port 5173.
3. Confirm the browser shows the prototype disclaimer.

## Demo flow

1. Use the explicit sample report action to show the review workflow quickly.
2. Upload a PDF, JPG, or PNG and show the processing state.
3. Point out the retained source text beside the editable result table.
4. Highlight a low-confidence result and correct its value or range.
5. Confirm the report and show the plain-language explanation with the disclaimer.
6. Ask the safety test question: "What disease does this indicate?" Explain that the guardrail replaces unsafe language with a neutral fallback.
7. Load two confirmed reports with a shared test and open Historical Trends.
8. Show the chronological values and neutral movement description.
9. Export the summary PDF and show the table, explanations, and disclaimer footer.
10. Restart the backend, reload the report flow, and explain that confirmed data is stored in local SQLite.
11. Use Delete Session Data and confirm only the current demo patient's data is removed.

## Safety language

Say "the value is above or below the range printed on this report," not "the patient is unhealthy" or "the result is improving/worsening." Clarify that this prototype does not diagnose or prescribe treatment.
