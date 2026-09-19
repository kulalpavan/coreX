import React, { useState } from "react";
import { ArrowUpRight, Download, LineChart, MessageCircle, RotateCcw, UserCheck } from "lucide-react";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { ReportChat } from "./ReportChat";

export function ExplanationView({ results, reportId, disclaimer, onExportPdf, onViewTrends, onRestart }) {

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

      <div className="summary-strip"><span>{results.length} confirmed measurements</span><span>Review complete</span></div>
      <div className="result-grid summary-result-grid">
            {results.map((result) => {
          const isHigh = result.flag === "H";
          const isLow = result.flag === "L";
          const flagLabel = isHigh ? "Above range" : isLow ? "Below range" : "Within range";
          const flagClass = isHigh ? "high" : isLow ? "low" : "normal";

              return (
              <article className="result-card" key={result.id}>
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
                <div className="result-range">
                  Range <strong>{result.reference_range_low ?? "—"} to {result.reference_range_high ?? "—"} {result.unit || ""}</strong>
                </div>
                <p className="result-explanation">
                  {result.explanation_text ||
                    `${result.raw_test_name} is recorded as ${result.value} ${result.unit}. Discuss this result with your clinician for personal context.`}
                </p>
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
      {reportId && <ReportChat reportId={reportId} />}
    </div>
  );
}
