import React, { useState, useRef, useEffect } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { askReportQuestion } from "../services/api";

export function ReportChat({ reportId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, busy]);

  if (!isOpen) {
    return (
      <button 
        className="chat-fab-trigger" 
        onClick={() => setIsOpen(true)}
        title="Ask about this report"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  async function submit(event) {
    event.preventDefault();
    if (!question.trim() || !reportId) return;
    
    const userMsg = { role: "user", content: question.trim() };
    const currentHistory = [...messages];
    
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");
    setBusy(true);
    setError("");
    
    try {
      const payload = await askReportQuestion(reportId, userMsg.content, currentHistory);
      const assistantMsg = { role: "assistant", content: payload.answer };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (requestError) {
      setError(requestError.message);
      // Remove the user message if it failed completely
      setMessages((prev) => prev.slice(0, prev.length - 1));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="report-chat-container">
      <section className="report-chat chat-popover" aria-label="Ask about this report">
        <div className="report-chat-heading">
          <MessageCircle size={17} />
          <div>
            <strong>Ask about this report</strong>
            <span>Source-grounded explanations only. No diagnosis.</span>
          </div>
          <button className="chat-close" onClick={() => setIsOpen(false)} title="Close chat"><X size={16} /></button>
        </div>
        
        <div className="report-chat-messages" ref={scrollRef}>
          {!reportId && <p className="report-chat-locked">Upload and confirm a report to ask questions about its contents.</p>}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className="chat-bubble">{msg.content}</div>
            </div>
          ))}
          
          {busy && (
            <div className="chat-message assistant">
              <div className="chat-bubble typing">Thinking...</div>
            </div>
          )}
        </div>

        {error && <p className="error-message" style={{margin: '0 12px 8px'}} role="alert">{error}</p>}
        
        <form onSubmit={submit} className="report-chat-form">
          <input disabled={!reportId || busy} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question..." aria-label="Question about report" />
          <button type="submit" disabled={!reportId || busy || !question.trim()} title="Ask question"><Send size={15} />{busy ? "..." : "Ask"}</button>
        </form>
      </section>
    </div>
  );
}