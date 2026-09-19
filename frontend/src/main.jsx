import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { AlertCircle, ArrowUpRight, Check, FileText, LockKeyhole, UploadCloud } from "lucide-react";
import "./styles.css";

const API_URL = "http://localhost:8000";

const demoResults = [
  { id: "demo_1", raw_test_name: "Hemoglobin", value: 13.8, unit: "g/dL", reference_range_low: 12, reference_range_high: 15.5, flag: "normal", extraction_confidence: 0.97 },
  { id: "demo_2", raw_test_name: "Total Cholesterol", value: 214, unit: "mg/dL", reference_range_low: 0, reference_range_high: 200, flag: "H", extraction_confidence: 0.94 },
  { id: "demo_3", raw_test_name: "TSH", value: 2.4, unit: "mIU/L", reference_range_low: 0.4, reference_range_high: 4, flag: "normal", extraction_confidence: 0.88 },
  { id: "demo_4", raw_test_name: "ALT", value: 31, unit: "U/L", reference_range_low: 7, reference_range_high: 56, flag: "normal", extraction_confidence: 0.72 },
];

function confidenceLabel(value) {
  if (value >= 0.9) return "High confidence";
  if (value >= 0.8) return "Review suggested";
  return "Needs review";
}

function App() {
  const [screen, setScreen] = useState("upload");
  const [fileName, setFileName] = useState("");
  const [results, setResults] = useState([]);
  const [reportId, setReportId] = useState(null);
  const [error, setError] = useState("");

  async function loadReport(file) {
    setError("");
    setFileName(file?.name || "demo-lab-report.pdf");
    if (!file) {
      setResults(demoResults);
      setScreen("review");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(`${API_URL}/api/reports/upload`, { method: "POST", body: formData });
      if (!response.ok) throw new Error("Upload failed. Check that the API is running.");
      const { report_id } = await response.json();
      setReportId(report_id);
      const extraction = await fetch(`${API_URL}/api/reports/${report_id}/extraction`).then((item) => item.json());
      setResults(extraction.results);
      setScreen("review");
    } catch (uploadError) {
      setError(uploadError.message);
    }
  }

  function updateResult(id, field, value) {
    setResults((current) => current.map((result) => result.id === id ? { ...result, [field]: field === "value" ? Number(value) : value, user_corrected: true } : result));
  }

  async function confirm() {
    if (!reportId) {
      setResults((current) => current.map((result) => ({ ...result, explanation_text: explanationFor(result) })));
      setScreen("explanation");
      return;
    }
    const response = await fetch(`${API_URL}/api/reports/${reportId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results }),
    });
    const payload = await response.json();
    if (!response.ok) return setError(payload.detail || "Could not confirm this report.");
    setResults(payload.results);
    setScreen("explanation");
  }

  function explanationFor(result) {
    const position = result.value >= result.reference_range_low && result.value <= result.reference_range_high ? "within" : result.value > result.reference_range_high ? "above" : "below";
    return `${result.raw_test_name} is recorded as ${result.value} ${result.unit}. This is ${position} the reported range of ${result.reference_range_low}-${result.reference_range_high} ${result.unit}. Discuss this result with your clinician for personal context.`;
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">C</span><span>clarify<span className="brand-accent">/</span>labs</span></div>
      <div className="prototype-tag"><span className="status-dot" />Prototype workspace</div>
    </header>
    <section className="workspace">
      <aside className="sidebar">
        <p className="eyebrow">Your report, made legible</p>
        <h1>Read the numbers.<br /><em>Keep the context.</em></h1>
        <p className="sidebar-copy">A calm, review-first way to understand the information in a lab report. Nothing is finalized until you check it.</p>
        <div className="step-list">
          <Step number="01" label="Upload report" active={screen === "upload"} done={screen !== "upload"} />
          <Step number="02" label="Review values" active={screen === "review"} done={screen === "explanation"} />
          <Step number="03" label="Read summary" active={screen === "explanation"} />
        </div>
        <div className="privacy-note"><LockKeyhole size={15} /><span>Your report stays in this local prototype.</span></div>
      </aside>
      <section className="content-panel">
        {screen === "upload" && <UploadView onFile={loadReport} error={error} />}
        {screen === "review" && <ReviewView fileName={fileName} results={results} onUpdate={updateResult} onConfirm={confirm} />}
        {screen === "explanation" && <ExplanationView results={results} onRestart={() => { setReportId(null); setResults([]); setScreen("upload"); }} />}
      </section>
    </section>
  </main>;
}

function Step({ number, label, active, done }) {
  return <div className={`step ${active ? "active" : ""}`}><span className={`step-number ${done ? "done" : ""}`}>{done ? <Check size={14} /> : number}</span><span>{label}</span>{active && <ArrowUpRight size={15} />}</div>;
}

function UploadView({ onFile, error }) {
  return <div className="view upload-view">
    <div className="view-header"><div><p className="eyebrow">Start here</p><h2>Bring in a report</h2><p className="lede">Upload a PDF or a clear photo. We’ll pull out the values so you can check them side by side.</p></div><span className="page-index">01 / 03</span></div>
    <label className="dropzone"><input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(event) => onFile(event.target.files?.[0])} /><UploadCloud size={29} strokeWidth={1.4} /><strong>Drop a report here</strong><span>or choose a PDF, JPG, or PNG · up to 15 MB</span><button type="button">Choose file</button></label>
    <button className="demo-link" onClick={() => onFile(null)}>Explore with a sample report <ArrowUpRight size={15} /></button>
    {error && <p className="error-message"><AlertCircle size={15} />{error}</p>}
    <div className="trust-strip"><div><strong>Review first</strong><span>You stay in control of every extracted value.</span></div><div><strong>Plain language</strong><span>Short explanations without a diagnosis.</span></div><div><strong>Traceable</strong><span>Confidence is shown field by field.</span></div></div>
  </div>;
}

function ReviewView({ fileName, results, onUpdate, onConfirm }) {
  return <div className="view review-view">
    <div className="view-header compact"><div><p className="eyebrow">Review & correct</p><h2>Check what we found</h2><p className="lede">Compare the extracted values with your original report. Make any edits before confirming.</p></div><span className="page-index">02 / 03</span></div>
    <div className="review-meta"><span><FileText size={15} />{fileName}</span><span>{results.length} values found</span></div>
    <div className="review-table-wrap"><table><thead><tr><th>Test</th><th>Value</th><th>Unit</th><th>Reference range</th><th>Read quality</th></tr></thead><tbody>{results.map((result) => <tr key={result.id}><td><input value={result.raw_test_name} onChange={(event) => onUpdate(result.id, "raw_test_name", event.target.value)} /></td><td><input className="value-input" type="number" value={result.value ?? ""} onChange={(event) => onUpdate(result.id, "value", event.target.value)} /></td><td><input value={result.unit ?? ""} onChange={(event) => onUpdate(result.id, "unit", event.target.value)} /></td><td><div className="range-inputs"><input type="number" value={result.reference_range_low ?? ""} onChange={(event) => onUpdate(result.id, "reference_range_low", Number(event.target.value))} /><span>to</span><input type="number" value={result.reference_range_high ?? ""} onChange={(event) => onUpdate(result.id, "reference_range_high", Number(event.target.value))} /></div></td><td><span className={`confidence ${result.extraction_confidence < 0.8 ? "low" : ""}`}><span className="confidence-bar"><i style={{ width: `${result.extraction_confidence * 100}%` }} /></span>{confidenceLabel(result.extraction_confidence)}</span></td></tr>)}</tbody></table></div>
    <div className="review-footer"><span><AlertCircle size={15} />Low-confidence fields are highlighted for your attention.</span><button className="primary-button" onClick={onConfirm}>Confirm & explain <ArrowUpRight size={16} /></button></div>
  </div>;
}

function ExplanationView({ results, onRestart }) {
  return <div className="view explanation-view"><div className="view-header compact"><div><p className="eyebrow">Your simplified report</p><h2>A clearer read on the page</h2><p className="lede">These notes describe what each measurement says relative to the range printed on your report.</p></div><span className="page-index">03 / 03</span></div><div className="disclaimer"><AlertCircle size={17} /><span><strong>Important context:</strong> This is an educational summary, not a diagnosis. Discuss your results with a qualified clinician.</span></div><div className="result-grid">{results.map((result) => <article className="result-card" key={result.id}><div className="result-card-top"><span>{result.raw_test_name}</span><span className={`flag ${result.flag === "H" ? "high" : ""}`}>{result.flag === "H" ? "Above range" : "Within range"}</span></div><div className="result-value">{result.value} <small>{result.unit}</small></div><p>{result.explanation_text || explanationFor(result)}</p><div className="result-range">Reported range <strong>{result.reference_range_low} — {result.reference_range_high} {result.unit}</strong></div></article>)}</div><button className="secondary-button" onClick={onRestart}>Review another report <ArrowUpRight size={15} /></button></div>;
}

createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
