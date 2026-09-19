import React from "react";
import { Loader2 } from "lucide-react";

export function LoadingOverlay({ message = "Processing your request..." }) {
  return (
    <div className="loading-overlay" role="status" aria-live="polite">
      <div className="loading-card">
        <Loader2 className="spinner" size={28} />
        <p className="loading-text">{message}</p>
      </div>
    </div>
  );
}
