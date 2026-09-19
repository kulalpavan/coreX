import React from "react";
import { ArrowUpRight, Download, LineChart, RotateCcw, UserCheck } from "lucide-react";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { ReportChat } from "./ReportChat";

export function ExplanationView({ results, reportId, disclaimer, onExportPdf, onViewTrends, onRestart }) {
  const aboveCount = results.filter((result) => result.flag === "H").length;
  const belowCount = results.filter((result) => result.flag === "L").length;

  function jumpToResult(result) {
    document.getElementById(`result-${result.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return (
    <div className="view explanation-view">
      <div className="view-header compact">
        <div>
          <p className="eyebrow">Your simplified report</p>
          <h2>A clearer read on the page</h2>
          <p className="lede">
            These notes describe what each measurement says relative to the range printed on your report.
          </p>
        </div>
        <span className="page-index">03 / 03</span>
      </div>

      <DisclaimerBanner text={disclaimer} />

      <div className="summary-layout">
        <div className="summary-results">
          <div className="summary-strip"><span>{results.length} confirmed measurements</span><span>Review complete</span></div>
          <div className="result-grid">
            {results.map((result) => {
          const isHigh = result.flag === "H";
          const isLow = result.flag === "L";
          const flagLabel = isHigh ? "Above range" : isLow ? "Below range" : "Within range";
          const flagClass = isHigh ? "high" : isLow ? "low" : "normal";

              return (
              <article className="result-card" id={`result-${result.id}`} key={result.id}>
              <div className="result-card-top">
                <span className="result-title">
                  {result.raw_test_name}
                  {result.user_corrected && (
                    <span className="user-corrected-badge" title="Manually edited during review">
                      <UserCheck size={11} /> Corrected
                    </span>
                  )}
                </span>
                <span className={`flag ${flagClass}`}>{flagLabel}</span>
              </div>

              <div className="result-value">
                {result.value ?? "N/A"} <small>{result.unit || ""}</small>
              </div>

              <p className="result-explanation">
                {result.explanation_text ||
                  `${result.raw_test_name} is recorded as ${result.value} ${result.unit}. Discuss this result with your clinician for personal context.`}
              </p>

              <div className="result-range">
                Reported range{" "}
                <strong>
                  {result.reference_range_low !== null && result.reference_range_low !== undefined
                    ? result.reference_range_low
                    : "—"}{" "}
                  to{" "}
                  {result.reference_range_high !== null && result.reference_range_high !== undefined
                    ? result.reference_range_high
                    : "—"}{" "}
                  {result.unit || ""}
                </strong>
              </div>
            </article>
              );
            })}
          </div>

          <div className="action-toolbar">
            <button className="primary-button" onClick={onExportPdf}>
              <Download size={16} /> Export Summary PDF
            </button>

            <button className="secondary-button" onClick={onViewTrends}>
              <LineChart size={16} /> View Historical Trends
            </button>

            <button className="secondary-button restart-button" onClick={onRestart}>
              <RotateCcw size={16} /> Review another report <ArrowUpRight size={15} />
            </button>
          </div>
        </div>
        <aside className="summary-chat-rail">
          <div className="summary-side-stack">
            <section className="side-card takeaways-card">
              <div className="side-card-label">At a glance</div>
              <h3>Key takeaways</h3>
              <p>{results.length} confirmed measurements are available for review.</p>
              <div className="takeaway-stats"><span><strong>{aboveCount}</strong> above range</span><span><strong>{belowCount}</strong> below range</span></div>
              <small>These labels compare only with ranges printed on the report.</small>
            </section>

            <section className="side-card">
              <div className="side-card-label">Navigate</div>
              <h3>Quick jump</h3>
              <nav className="quick-jump" aria-label="Jump to report result">
                {results.map((result) => <button key={result.id} onClick={() => jumpToResult(result)}>{result.raw_test_name}<ArrowUpRight size={13} /></button>)}
              </nav>
            </section>

            <section className="side-card action-card">
              <div className="side-card-label">Next step</div>
              <h3>Bring this to your clinician</h3>
              <p>Use the export or write down questions about any result you want to discuss with an approved healthcare professional.</p>
              <button className="side-action-button" onClick={onExportPdf}><Download size={14} /> Download summary</button>
            </section>

            <ReportChat reportId={reportId} className="side-chat" />
          </div>
        </aside>
      </div>
    </div>
  );
}
