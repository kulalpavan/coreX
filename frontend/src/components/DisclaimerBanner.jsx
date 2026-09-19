import React from "react";
import { AlertCircle } from "lucide-react";

export function DisclaimerBanner({ text }) {
  return (
    <div className="disclaimer" role="note" aria-label="Medical Disclaimer">
      <AlertCircle size={18} />
      <span>
        <strong>Important Context:</strong>{" "}
        {text || "This is an educational summary, not a medical diagnosis. Discuss your lab results directly with a qualified clinician."}
      </span>
    </div>
  );
}
