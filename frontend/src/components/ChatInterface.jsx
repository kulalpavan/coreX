import React, { useState, useRef, useEffect } from 'react';
import { askReportQuestion } from '../services/api';

export default function ChatInterface({ reportId }) {
  const [messages, setMessages] = useState([
    { role: 'model', text: 'CONNECTION ESTABLISHED. INITIALIZING AI ASSISTANT...' },
    { role: 'model', text: 'READY FOR INQUIRY.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || !reportId) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      // Build history excluding the intro text
      const history = messages
        .filter(m => !m.text.includes('CONNECTION ESTABLISHED'))
        .map(m => ({ role: m.role, content: m.text }));

      const res = await askReportQuestion(reportId, userMsg, history);
      setMessages(prev => [...prev, { role: 'model', text: res.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'model', text: `ERROR: ${err.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!reportId) return null;

  return (
    <div style={{ marginTop: '4rem', marginBottom: '4rem' }}>
      <h3 className="pixel-font" style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>TERMINAL // AI_ASSISTANT</h3>
      
      <div className="terminal-window">
        <div className="terminal-header">
          <div className="terminal-dot dot-red"></div>
          <div className="terminal-dot dot-yellow"></div>
          <div className="terminal-dot dot-green"></div>
          <div className="pixel-font" style={{ marginLeft: '1rem', color: 'var(--text-secondary)' }}>
            session_id: {reportId.substring(0, 8)}
          </div>
        </div>

        <div className="terminal-body">
          {messages.map((m, idx) => (
            <div key={idx} className={`terminal-msg ${m.role === 'user' ? 'msg-user' : 'msg-bot'}`}>
              <span style={{ fontSize: '0.875rem', color: m.role === 'user' ? 'var(--text-secondary)' : 'var(--accent-neon)', display: 'block', marginBottom: '0.25rem' }}>
                {m.role === 'user' ? 'USER_INPUT' : 'SYS_RESPONSE'}&gt;
              </span>
              {m.text}
            </div>
          ))}
          {isLoading && (
            <div className="terminal-msg msg-bot">
              <span style={{ fontSize: '0.875rem', color: 'var(--accent-neon)', display: 'block', marginBottom: '0.25rem' }}>SYS_RESPONSE&gt;</span>
              <span className="pixel-font" style={{ animation: 'pulse 1.5s infinite' }}>PROCESSING...</span>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form onSubmit={handleSubmit} className="terminal-input">
          <input 
            type="text" 
            placeholder="ENTER COMMAND..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            autoComplete="off"
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? 'WAIT' : 'EXECUTE'}
          </button>
        </form>
      </div>
    </div>
  );
}
