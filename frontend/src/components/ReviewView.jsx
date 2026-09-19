import React from "react";
import { AlertCircle, ArrowUpRight, FileText, Plus, Trash2 } from "lucide-react";

function confidenceLabel(value) {
  if (value >= 0.9) return "High confidence";
  if (value >= 0.8) return "Review suggested";
  return "Needs review";
}

export function ReviewView({ fileName, sourceText, results, onUpdate, onAddRow, onDeleteRow, onConfirm, error }) {
  const lowConfidenceCount = results.filter((r) => r.extraction_confidence < 0.8).length;

  return (
    <div className="view review-view">
      <div className="view-header compact">
        <div>
          <p className="eyebrow">Review & correct</p>
          <h2>Check what we found</h2>
          <p className="lede">
            Compare the extracted values with your original report. Make any edits or additions before confirming.
          </p>
        </div>
        <span className="page-index">02 / 03</span>
      </div>

      <div className="review-meta">
        <span>
          <FileText size={15} />
          {fileName || "uploaded-report.pdf"}
        </span>
        <span>{results.length} values found</span>
      </div>

      <div className="source-preview" aria-label="Extracted source text">
        <div className="source-preview-header"><span>Source text</span><span>Read-only evidence</span></div>
        <pre>{sourceText || "No readable source text was returned. Review the extracted fields manually."}</pre>
      </div>

      <div className="review-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Test Name</th>
              <th>Value</th>
              <th>Unit</th>
              <th>Reference Range</th>
              <th>Flag</th>
              <th>Read Quality</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => {
              const isLowConf = result.extraction_confidence < 0.8;
              return (
                <tr key={result.id} className={isLowConf ? "row-low-confidence" : ""}>
                  <td>
                    <input
                      type="text"
                      value={result.raw_test_name || ""}
                      onChange={(e) => onUpdate(result.id, "raw_test_name", e.target.value)}
                      placeholder="e.g. Hemoglobin"
                    />
                  </td>
                  <td>
                    <input
                      className="value-input"
                      type="number"
                      step="any"
                      value={result.value ?? ""}
                      onChange={(e) =>
                        onUpdate(result.id, "value", e.target.value === "" ? null : Number(e.target.value))
                      }
                      placeholder="0.0"
                    />
                  </td>
                  <td>
                    <input
                      type="text"
                      value={result.unit ?? ""}
                      onChange={(e) => onUpdate(result.id, "unit", e.target.value)}
                      placeholder="e.g. g/dL"
                    />
                  </td>
                  <td>
                    <div className="range-inputs">
                      <input
                        type="number"
                        step="any"
                        value={result.reference_range_low ?? ""}
                        onChange={(e) =>
                          onUpdate(
                            result.id,
                            "reference_range_low",
                            e.target.value === "" ? null : Number(e.target.value)
                          )
                        }
                        placeholder="Low"
                      />
                      <span>to</span>
                      <input
                        type="number"
                        step="any"
                        value={result.reference_range_high ?? ""}
                        onChange={(e) =>
                          onUpdate(
                            result.id,
                            "reference_range_high",
                            e.target.value === "" ? null : Number(e.target.value)
                          )
                        }
                        placeholder="High"
                      />
                    </div>
                  </td>
                  <td>
                    <select
                      className="flag-select"
                      value={result.flag || "normal"}
                      onChange={(e) => onUpdate(result.id, "flag", e.target.value)}
                    >
                      <option value="normal">Normal</option>
                      <option value="H">High (H)</option>
                      <option value="L">Low (L)</option>
                    </select>
                  </td>
                  <td>
                    <span className={`confidence ${isLowConf ? "low" : ""}`}>
                      <span className="confidence-bar">
                        <i style={{ width: `${Math.min(100, (result.extraction_confidence || 0.5) * 100)}%` }} />
                      </span>
                      {confidenceLabel(result.extraction_confidence ?? 0.5)}
                    </span>
                  </td>
                  <td>
                    <button
                      className="icon-button delete-row-btn"
                      onClick={() => onDeleteRow(result.id)}
                      title="Remove row"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="table-actions">
        <button className="secondary-button add-row-btn" onClick={onAddRow}>
          <Plus size={14} /> Add Test Row
        </button>
      </div>

      {error && (
        <p className="error-message" role="alert">
          <AlertCircle size={15} />
          {error}
        </p>
      )}

      <div className="review-footer">
        <span>
          <AlertCircle size={15} />
          {lowConfidenceCount > 0
            ? `${lowConfidenceCount} field(s) have low read confidence and are highlighted for your verification.`
            : "All fields checked. You can adjust any value before confirming."}
        </span>
        <button className="primary-button" onClick={onConfirm}>
          Confirm & Explain <ArrowUpRight size={16} />
        </button>
      </div>
    </div>
  );
}
