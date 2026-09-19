import React, { useEffect, useState } from "react";
import { ArrowLeft, Calendar, Info, LineChart } from "lucide-react";
import { DisclaimerBanner } from "./DisclaimerBanner";
import { getTrends } from "../services/api";

export function TrendsView({ results, onBackToExplanation }) {
  const availableTests = Array.from(
    new Set(results.map((r) => r.raw_test_name).concat(["Hemoglobin", "Total Cholesterol", "TSH", "ALT"]))
  );

  const [selectedTest, setSelectedTest] = useState(availableTests[0] || "Hemoglobin");
  const [trendData, setTrendData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    getTrends("p_demo", selectedTest)
      .then((data) => {
        if (isMounted) {
          setTrendData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("Failed to load trends:", err);
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedTest]);

  const points = trendData?.points || [];

  // SVG Chart Dimensions & Calculations
  const chartWidth = 560;
  const chartHeight = 220;
  const padding = 40;

  const minVal = points.length ? Math.min(...points.map((p) => p.value)) * 0.9 : 0;
  const maxVal = points.length ? Math.max(...points.map((p) => p.value)) * 1.1 : 100;

  function getX(index) {
    if (points.length <= 1) return chartWidth / 2;
    return padding + (index / (points.length - 1)) * (chartWidth - padding * 2);
  }

  function getY(val) {
    if (maxVal === minVal) return chartHeight / 2;
    return chartHeight - padding - ((val - minVal) / (maxVal - minVal)) * (chartHeight - padding * 2);
  }

  const svgPointsPath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${getX(i)} ${getY(p.value)}`)
    .join(" ");

  return (
    <div className="view trends-view">
      <div className="view-header compact">
        <div>
          <button className="back-link-btn" onClick={onBackToExplanation}>
            <ArrowLeft size={14} /> Back to Summary
          </button>
          <p className="eyebrow">Multi-report Tracking</p>
          <h2>Historical Trends</h2>
          <p className="lede">
            Compare results across multiple dated reports. Neutral tracking without subjective interpretations.
          </p>
        </div>
      </div>

      <DisclaimerBanner />

      <div className="trends-controls">
        <label className="test-selector-label">
          <LineChart size={16} /> Select Test:
        </label>
        <select
          className="test-selector-dropdown"
          value={selectedTest}
          onChange={(e) => setSelectedTest(e.target.value)}
        >
          {availableTests.map((testName) => (
            <option key={testName} value={testName}>
              {testName}
            </option>
          ))}
        </select>
      </div>

      <div className="trend-summary-box">
        <Info size={18} className="trend-info-icon" />
        <p className="trend-description-text">
          {loading ? "Loading historical data..." : trendData?.description || "No sufficient historical points recorded yet."}
        </p>
      </div>

      {!loading && points.length > 0 && (
        <div className="chart-container">
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="trend-svg">
            {/* Grid lines */}
            <line x1={padding} y1={padding} x2={chartWidth - padding} y2={padding} stroke="#e5e7eb" strokeDasharray="4" />
            <line
              x1={padding}
              y1={chartHeight / 2}
              x2={chartWidth - padding}
              y2={chartHeight / 2}
              stroke="#e5e7eb"
              strokeDasharray="4"
            />
            <line
              x1={padding}
              y1={chartHeight - padding}
              x2={chartWidth - padding}
              y2={chartHeight - padding}
              stroke="#e5e7eb"
            />

            {/* Line connecting points */}
            <path d={svgPointsPath} fill="none" stroke="#155c51" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

            {/* Data point circles & value tags */}
            {points.map((p, i) => {
              const cx = getX(i);
              const cy = getY(p.value);
              return (
                <g key={i} className="chart-point-group">
                  <circle cx={cx} cy={cy} r="6" fill="#155c51" stroke="#ffffff" strokeWidth="2" />
                  <text x={cx} y={cy - 12} textAnchor="middle" className="chart-value-text">
                    {p.value} {trendData?.unit || ""}
                  </text>
                  <text x={cx} y={chartHeight - 12} textAnchor="middle" className="chart-date-text">
                    {p.date}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}

      <div className="trend-history-table-wrap">
        <h3>Historical Readings</h3>
        <table className="trend-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Recorded Value</th>
              <th>Unit</th>
              <th>Flag</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p, index) => (
              <tr key={index}>
                <td>
                  <span className="date-cell">
                    <Calendar size={13} /> {p.date}
                  </span>
                </td>
                <td>
                  <strong>{p.value}</strong>
                </td>
                <td>{trendData?.unit || "—"}</td>
                <td>
                  <span className={`flag ${p.flag === "H" ? "high" : p.flag === "L" ? "low" : "normal"}`}>
                    {p.flag === "H" ? "High" : p.flag === "L" ? "Low" : "Normal"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
