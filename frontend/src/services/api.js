const API_URL = "http://localhost:8000";

export const sampleDemoResults = [
  {
    id: "demo_1",
    raw_test_name: "Hemoglobin",
    value: 13.8,
    unit: "g/dL",
    reference_range_low: 12.0,
    reference_range_high: 15.5,
    flag: "normal",
    report_date: "2026-08-14",
    extraction_confidence: 0.97,
    user_corrected: false,
    explanation_text: null,
  },
  {
    id: "demo_2",
    raw_test_name: "Total Cholesterol",
    value: 214,
    unit: "mg/dL",
    reference_range_low: 0,
    reference_range_high: 200,
    flag: "H",
    report_date: "2026-08-14",
    extraction_confidence: 0.94,
    user_corrected: false,
    explanation_text: null,
  },
  {
    id: "demo_3",
    raw_test_name: "TSH",
    value: 2.4,
    unit: "mIU/L",
    reference_range_low: 0.4,
    reference_range_high: 4.0,
    flag: "normal",
    report_date: "2026-08-14",
    extraction_confidence: 0.88,
    user_corrected: false,
    explanation_text: null,
  },
  {
    id: "demo_4",
    raw_test_name: "ALT",
    value: 31,
    unit: "U/L",
    reference_range_low: 7,
    reference_range_high: 56,
    flag: "normal",
    report_date: "2026-08-14",
    extraction_confidence: 0.72,
    user_corrected: false,
    explanation_text: null,
  },
];

export async function uploadReport(file) {
  if (!file) throw new Error("No file provided.");
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/reports/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed with status ${response.status}`);
  }
  return response.json();
}

export async function getExtraction(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/extraction`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to retrieve extraction results.");
  }
  return response.json();
}

export async function getSource(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/source`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to retrieve source text.");
  }
  return response.json();
}

export function getSourceFileUrl(reportId) {
  return `${API_URL}/api/reports/${reportId}/source-file`;
}

export async function confirmReport(reportId, results) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Could not confirm this report.");
  }
  return response.json();
}

export async function getExplanations(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/explanations`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch report explanations.");
  }
  return response.json();
}

export async function getTrends(patientId = "p_demo", canonicalTestId = "Hemoglobin") {
  const response = await fetch(`${API_URL}/api/patients/${patientId}/trends/${encodeURIComponent(canonicalTestId)}`);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to load trends with status ${response.status}`);
  }
  return response.json();
}

export async function exportPdf(reportId) {
  if (!reportId) {
    throw new Error("Export is available after a report has been uploaded and confirmed.");
  }
  const response = await fetch(`${API_URL}/api/reports/${reportId}/export`, { method: "POST" });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `PDF export failed with status ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/pdf")) {
    throw new Error("The export service did not return a PDF.");
  }
  return response.blob();
}

export async function deletePatientData(patientId = "p_demo") {
  try {
    const response = await fetch(`${API_URL}/api/patients/${patientId}/data`, {
      method: "DELETE",
    });
    if (response.ok) return await response.json();
  } catch (err) {
    console.warn("Delete endpoint error, clearing locally:", err);
  }
  return { status: "deleted", patient_id: patientId };
}
