import React from "react";
import { MessageCircle, Trash2 } from "lucide-react";

export function Topbar({ onDeleteClick, onChatClick, apiStatus, ocrAvailable }) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark">C</span>
        <span>
          clarify<span className="brand-accent">/</span>labs
        </span>
      </div>
      <div className="topbar-actions">
        <div className="prototype-tag">
          <span className={`status-dot ${apiStatus}`} />
          {apiStatus === "online"
            ? ocrAvailable === false
              ? "API online · OCR unavailable"
              : "API online"
            : apiStatus === "offline"
              ? "API offline"
              : "Checking API"}
        </div>
        {onChatClick && (
          <button className="chat-trigger-btn" onClick={onChatClick} title="Ask about this report">
            <MessageCircle size={14} />
            <span>Ask about report</span>
          </button>
        )}
        {onDeleteClick && (
          <button className="delete-trigger-btn" onClick={onDeleteClick} title="Purge patient data">
            <Trash2 size={14} />
            <span>Delete Session Data</span>
          </button>
        )}
      </div>
    </header>
  );
}
