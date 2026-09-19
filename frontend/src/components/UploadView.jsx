import React, { useState } from "react";
import { AlertCircle, ArrowUpRight, UploadCloud } from "lucide-react";

export function UploadView({ onFileSelect, error }) {
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState("");

  const MAX_BYTES = 15 * 1024 * 1024; // 15MB
  const ALLOWED_EXT = [".pdf", ".jpg", ".jpeg", ".png"];

  function validateAndSubmit(file) {
    setLocalError("");
    if (!file) {
      onFileSelect(null); // Demo mode
      return;
    }

    const name = file.name.toLowerCase();
    const isAllowed = ALLOWED_EXT.some((ext) => name.endsWith(ext));

    if (!isAllowed) {
      setLocalError("Please select a valid PDF, JPG, or PNG document.");
      return;
    }

    if (file.size > MAX_BYTES) {
      setLocalError("Files must be 15 MB or smaller.");
      return;
    }

    onFileSelect(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      validateAndSubmit(files[0]);
    }
  }

  const activeError = localError || error;

  return (
    <div className="view upload-view">
      <div className="view-header">
        <div>
          <p className="eyebrow">Start here</p>
          <h2>Bring in a report</h2>
          <p className="lede">
            Upload a PDF or a clear photo of your report. We'll pull out the values so you can review them side by side.
          </p>
        </div>
        <span className="page-index">01 / 03</span>
      </div>

      <label
        className={`dropzone ${isDragging ? "dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(event) => validateAndSubmit(event.target.files?.[0])}
        />
        <UploadCloud size={32} strokeWidth={1.4} />
        <strong>{isDragging ? "Drop file to upload" : "Drop a report here"}</strong>
        <span>or choose a PDF, JPG, or PNG · up to 15 MB</span>
        <button type="button" tabIndex={-1}>
          Choose file
        </button>
      </label>

      <button className="demo-link" onClick={() => validateAndSubmit(null)}>
        Explore with a sample report <ArrowUpRight size={15} />
      </button>

      {activeError && (
        <p className="error-message" role="alert">
          <AlertCircle size={15} />
          {activeError}
        </p>
      )}

      <div className="trust-strip">
        <div>
          <strong>Review first</strong>
          <span>You stay in control of every extracted value before it is saved.</span>
        </div>
        <div>
          <strong>Plain language</strong>
          <span>Short, clear explanations without diagnostic assertions.</span>
        </div>
        <div>
          <strong>Traceable</strong><span>Field-by-field confidence scores guide your review.</span>
        </div>
      </div>
    </div>
  );
}
