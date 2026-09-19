import React from "react";
import { Trash2 } from "lucide-react";

export function Topbar({ onDeleteClick }) {
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
          <span className="status-dot" />
          Prototype workspace
        </div>
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
