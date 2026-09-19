import React from "react";
import { AlertTriangle, Trash2, X } from "lucide-react";

export function DeleteModal({ isOpen, onClose, onConfirm, isDeleting }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <AlertTriangle className="warning-icon" size={20} />
            <h3>Delete Patient Data</h3>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <p>
            This action will permanently purge all uploaded lab reports, candidate values, user corrections, and generated explanations from this session.
          </p>
          <p className="modal-subtext">This action cannot be undone.</p>
        </div>
        <div className="modal-actions">
          <button className="secondary-button" onClick={onClose} disabled={isDeleting}>
            Cancel
          </button>
          <button className="danger-button" onClick={onConfirm} disabled={isDeleting}>
            <Trash2 size={15} />
            {isDeleting ? "Deleting..." : "Delete All Data"}
          </button>
        </div>
      </div>
    </div>
  );
}
