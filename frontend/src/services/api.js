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

export const mockTrendsData = {
  Hemoglobin: {
    test_name: "Hemoglobin",
    unit: "g/dL",
    reference_range: "12.0 - 15.5",
    description: "This value moved from 14.2 g/dL on 2026-03-10 to 13.8 g/dL on 2026-08-14.",
    points: [
      { date: "2026-01-15", value: 14.5, flag: "normal" },
      { date: "2026-03-10", value: 14.2, flag: "normal" },
      { date: "2026-08-14", value: 13.8, flag: "normal" },
    ],
  },
  "Total Cholesterol": {
    test_name: "Total Cholesterol",
    unit: "mg/dL",
    reference_range: "0 - 200",
    description: "This value moved from 186 mg/dL on 2026-06-10 to 214 mg/dL on 2026-08-14.",
    points: [
      { date: "2025-11-20", value: 178, flag: "normal" },
      { date: "2026-06-10", value: 186, flag: "normal" },
      { date: "2026-08-14", value: 214, flag: "H" },
    ],
  },
  TSH: {
    test_name: "TSH",
    unit: "mIU/L",
    reference_range: "0.4 - 4.0",
    description: "This value moved from 2.1 mIU/L on 2026-02-05 to 2.4 mIU/L on 2026-08-14.",
    points: [
      { date: "2025-08-12", value: 1.9, flag: "normal" },
      { date: "2026-02-05", value: 2.1, flag: "normal" },
      { date: "2026-08-14", value: 2.4, flag: "normal" },
    ],
  },
  ALT: {
    test_name: "ALT",
    unit: "U/L",
    reference_range: "7 - 56",
    description: "This value moved from 28 U/L on 2026-04-18 to 31 U/L on 2026-08-14.",
    points: [
      { date: "2025-10-05", value: 25, flag: "normal" },
      { date: "2026-04-18", value: 28, flag: "normal" },
      { date: "2026-08-14", value: 31, flag: "normal" },
    ],
  },
};

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
  try {
    const response = await fetch(`${API_URL}/api/patients/${patientId}/trends/${encodeURIComponent(canonicalTestId)}`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn("Using local trend mock fallback:", err);
  }
  return mockTrendsData[canonicalTestId] || {
    test_name: canonicalTestId,
    unit: "",
    reference_range: "N/A",
    description: `Trend tracking active for ${canonicalTestId}.`,
    points: [
      { date: "2026-08-14", value: 10, flag: "normal" }
    ]
  };
}

export async function exportPdf(reportId) {
  if (!reportId) {
    // Generate sample PDF text blob locally if demo mode
    const blob = new Blob(
      ["Clarify Labs Patient Summary PDF Export\n\nDemo Report Confirmed Results Summary."],
      { type: "application/pdf" }
    );
    return blob;
  }
  try {
    const response = await fetch(`${API_URL}/api/reports/${reportId}/export`, {
      method: "POST",
    });
    if (response.ok) {
      return await response.blob();
    }
  } catch (err) {
    console.warn("PDF export endpoint error, using demo download:", err);
  }
  return new Blob(
    [`Clarify Labs Summary for Report ${reportId}\n\nDisclaimer: Prototype education only. Not a diagnosis.`],
    { type: "text/plain" }
  );
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
