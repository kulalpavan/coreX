import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

import { Topbar } from "./components/Topbar";
import { Sidebar } from "./components/Sidebar";
import { UploadView } from "./components/UploadView";
import { ReviewView } from "./components/ReviewView";
import { ExplanationView } from "./components/ExplanationView";
import { TrendsView } from "./components/TrendsView";
import { LoadingOverlay } from "./components/LoadingOverlay";
import { DeleteModal } from "./components/DeleteModal";

import {
  confirmReport,
  deletePatientData,
  exportPdf,
  getExtraction,
  sampleDemoResults,
  uploadReport,
} from "./services/api";

function App() {
  const [screen, setScreen] = useState("upload");
  const [fileName, setFileName] = useState("");
  const [results, setResults] = useState([]);
  const [reportId, setReportId] = useState(null);
  const [patientId] = useState("p_demo");
  const [disclaimer, setDisclaimer] = useState("");

  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [error, setError] = useState("");

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  function localExplanationFor(result) {
    const val = result.value;
    const low = result.reference_range_low;
    const high = result.reference_range_high;
    const name = result.raw_test_name || "Test";
    const unit = result.unit || "";

    if (low !== null && low !== undefined && high !== null && high !== undefined && val !== null && val !== undefined) {
      const position = val >= low && val <= high ? "within" : val > high ? "above" : "below";
      return `${name} is recorded as ${val} ${unit}. This is ${position} the reported range of ${low}-${high} ${unit}. Discuss this result with your clinician for personal context.`;
    }
    return `${name} is recorded as ${val ?? "N/A"} ${unit}. The report does not include enough reference range information for a comparison. Discuss this result with your clinician.`;
  }

  async function handleLoadReport(file) {
    setError("");
    if (!file) {
      // Demo mode fallback
      setFileName("demo-lab-report.pdf");
      setResults(sampleDemoResults);
      setReportId(null);
      setScreen("review");
      return;
    }

    setLoading(true);
    setLoadingMsg("Uploading and processing document with OCR engine...");
    setFileName(file.name);

    try {
      const uploadRes = await uploadReport(file);
      const repId = uploadRes.report_id;
      setReportId(repId);

      setLoadingMsg("Extracting candidate test values and confidence scores...");
      const extractionRes = await getExtraction(repId);

      setResults(extractionRes.results || []);
      setScreen("review");
    } catch (err) {
      console.error("Upload error:", err);
      setError(err.message || "Could not process this report. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  }

  function handleUpdateResult(id, field, value) {
    setResults((current) =>
      current.map((item) =>
        item.id === id
          ? {
              ...item,
              [field]: value,
              user_corrected: true,
            }
          : item
      )
    );
  }

  function handleAddRow() {
    const newId = `custom_${Date.now()}`;
    const newRow = {
      id: newId,
      raw_test_name: "New Test",
      value: 0,
      unit: "",
      reference_range_low: 0,
      reference_range_high: 100,
      flag: "normal",
      report_date: new Date().toISOString().split("T")[0],
      extraction_confidence: 1.0,
      user_corrected: true,
      explanation_text: null,
    };
    setResults((current) => [...current, newRow]);
  }

  function handleDeleteRow(id) {
    setResults((current) => current.filter((item) => item.id !== id));
  }

  async function handleConfirm() {
    setError("");
    if (!reportId) {
      // Demo mode confirmation
      setResults((current) =>
        current.map((res) => ({
          ...res,
          explanation_text: localExplanationFor(res),
        }))
      );
      setDisclaimer(
        "Prototype education only. This summary is not a diagnosis. Discuss your results with a qualified clinician."
      );
      setScreen("explanation");
      return;
    }

    setLoading(true);
    setLoadingMsg("Verifying confirmations and generating safe plain-language explanations...");

    try {
      const confirmRes = await confirmReport(reportId, results);
      setResults(confirmRes.results || []);
      if (confirmRes.disclaimer) {
        setDisclaimer(confirmRes.disclaimer);
      }
      setScreen("explanation");
    } catch (err) {
      console.error("Confirmation error:", err);
      setError(err.message || "Failed to confirm report.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExportPdf() {
    setLoading(true);
    setLoadingMsg("Generating summary PDF with disclaimers...");

    try {
      const blob = await exportPdf(reportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ClarifyLabs_Summary_${reportId || "demo"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF Export error:", err);
      alert("Failed to export PDF summary.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deletePatientData(patientId);
      setResults([]);
      setReportId(null);
      setFileName("");
      setError("");
      setScreen("upload");
      setDeleteModalOpen(false);
    } catch (err) {
      console.error("Delete error:", err);
      alert("Failed to purge data.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <main className="app-shell">
      <Topbar onDeleteClick={() => setDeleteModalOpen(true)} />

      <section className="workspace">
        <Sidebar screen={screen} setScreen={setScreen} hasResults={results.length > 0} />

        <section className="content-panel">
          {screen === "upload" && <UploadView onFileSelect={handleLoadReport} error={error} />}

          {screen === "review" && (
            <ReviewView
              fileName={fileName}
              results={results}
              onUpdate={handleUpdateResult}
              onAddRow={handleAddRow}
              onDeleteRow={handleDeleteRow}
              onConfirm={handleConfirm}
              error={error}
            />
          )}

          {screen === "explanation" && (
            <ExplanationView
              results={results}
              disclaimer={disclaimer}
              onExportPdf={handleExportPdf}
              onViewTrends={() => setScreen("trends")}
              onRestart={() => {
                setReportId(null);
                setResults([]);
                setFileName("");
                setScreen("upload");
              }}
            />
          )}

          {screen === "trends" && (
            <TrendsView results={results} onBackToExplanation={() => setScreen("explanation")} />
          )}
        </section>
      </section>

      {loading && <LoadingOverlay message={loadingMsg} />}

      <DeleteModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
        isDeleting={isDeleting}
      />
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
