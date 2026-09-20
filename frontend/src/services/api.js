const API_URL = "http://localhost:8000";

function getAuthHeaders(additionalHeaders = {}) {
  const token = localStorage.getItem("token");
  const headers = { ...additionalHeaders };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function checkHealth() {
  const response = await fetch(`${API_URL}/api/health`);
  if (!response.ok) throw new Error("Backend unavailable");
  return response.json();
}

// --- Auth API ---

export async function registerApi(email, password) {
  const response = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Registration failed.");
  return data;
}

export async function loginApi(email, password) {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Login failed.");
  return data;
}

export async function meApi() {
  const response = await fetch(`${API_URL}/api/auth/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Session expired or invalid.");
  return response.json();
}

export async function logoutApi() {
  await fetch(`${API_URL}/api/auth/logout`, {
    method: "POST",
    headers: getAuthHeaders(),
  }).catch(() => {});
}

// --- Reports API ---

export async function listUserReports() {
  const response = await fetch(`${API_URL}/api/reports`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load user reports.");
  }
  return response.json();
}

export async function uploadReport(file) {
  if (!file) throw new Error("No file provided.");
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/api/reports/upload`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed with status ${response.status}`);
  }
  return response.json();
}

export async function getExtraction(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/extraction`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to retrieve extraction results.");
  }
  return response.json();
}

export async function getSource(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/source`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to retrieve source text.");
  }
  return response.json();
}

export function getSourceFileUrl(reportId) {
  const token = localStorage.getItem("token") || "";
  return `${API_URL}/api/reports/${reportId}/source-file`;
}

export async function fetchSourceFileBlob(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/source-file`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Could not fetch source document.");
  return response.blob();
}

export async function confirmReport(reportId, results) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/confirm`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ results }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Could not confirm this report.");
  }
  return response.json();
}

export async function getExplanations(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/explanations`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch report explanations.");
  }
  return response.json();
}

export async function askReportQuestion(reportId, question, history = []) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}/chat`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question, history }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "Could not ask about this report.");
  return payload;
}

export async function deleteReportApi(reportId) {
  const response = await fetch(`${API_URL}/api/reports/${reportId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete report.");
  }
  return response.json();
}

export async function getTrends(patientId = "p_demo", canonicalTestId = "Hemoglobin") {
  const response = await fetch(
    `${API_URL}/api/patients/${patientId}/trends/${encodeURIComponent(canonicalTestId)}`,
    { headers: getAuthHeaders() }
  );
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
  const response = await fetch(`${API_URL}/api/reports/${reportId}/export`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
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
      headers: getAuthHeaders(),
    });
    if (response.ok) return await response.json();
  } catch (err) {
    console.warn("Delete endpoint error, clearing locally:", err);
  }
  return { status: "deleted", patient_id: patientId };
}

