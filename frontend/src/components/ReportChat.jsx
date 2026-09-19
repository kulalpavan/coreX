import React, { useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { askReportQuestion } from "../services/api";

export function ReportChat({ reportId, onClose }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    if (!question.trim() || !reportId) return;
    setBusy(true);
    setError("");
    try {
      const payload = await askReportQuestion(reportId, question);
      setAnswer(payload.answer);
      setQuestion("");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="report-chat chat-modal" aria-label="Ask about this report" onClick={(event) => event.stopPropagation()}>
        <div className="report-chat-heading"><MessageCircle size={17} /><div><strong>Ask about this report</strong><span>Source-grounded explanations only. No diagnosis or treatment decisions.</span></div><button className="chat-close" onClick={onClose} title="Close chat"><X size={16} /></button></div>
        {!reportId && <p className="report-chat-locked">Upload and confirm a report to ask questions about its contents.</p>}
        {answer && <div className="report-chat-answer">{answer}</div>}
        {error && <p className="error-message" role="alert">{error}</p>}
        <form onSubmit={submit} className="report-chat-form">
          <input disabled={!reportId} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What does Hemoglobin mean here?" aria-label="Question about report" />
          <button type="submit" disabled={!reportId || busy || !question.trim()} title="Ask question"><Send size={15} />{busy ? "Asking" : "Ask"}</button>
        </form>
      </section>
    </div>
  );
}