import React from 'react';

export default function ExplanationDashboard({ results, disclaimer, onExportPdf, onViewTrends, onRestart }) {
  if (!results || results.length === 0) return null;

  return (
    <div style={{ marginTop: '2rem' }}>
      
      {/* Medical Disclaimer Banner */}
      <div className="retro-box" style={{ borderColor: 'var(--accent-red)', padding: '1rem', marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div style={{ background: 'var(--accent-red)', color: '#000', padding: '4px 8px', fontWeight: 'bold' }} className="pixel-font">WARNING</div>
        <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
          {disclaimer || "Prototype education only. This summary is not a diagnosis. Discuss your results with a qualified clinician."}
        </p>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <div>
          <h3 className="pixel-font" style={{ fontSize: '1.5rem', margin: 0, color: 'var(--accent-neon)' }}>STEP 2: EXPLANATIONS</h3>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>AI-generated, guardrail-verified summaries.</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn-retro" onClick={onViewTrends}>VIEW_TRENDS</button>
          <button className="btn-retro primary" onClick={onExportPdf}>EXPORT_PDF</button>
        </div>
      </div>

      <div className="data-grid">
        {results.map((item, idx) => (
          <div key={idx} className="retro-box data-card" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div className="metric-name">{item.raw_test_name}</div>
              {item.flag && item.flag.toLowerCase() !== 'normal' && (
                <div className="flag-badge flag-high">
                  FLAG: {item.flag}
                </div>
              )}
            </div>
            
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', margin: '0.5rem 0' }}>
              <span className="metric-value">{item.value ?? '--'}</span>
              <span style={{ color: 'var(--accent-neon)' }} className="pixel-font">{item.unit}</span>
            </div>
            
            {(item.reference_range_low !== null || item.reference_range_high !== null) && (
              <div className="metric-range" style={{ marginBottom: '1rem' }}>
                RANGE: {item.reference_range_low ?? 0} - {item.reference_range_high ?? 'N/A'}
              </div>
            )}
            
            <div style={{ borderTop: '1px dashed var(--border-color)', paddingTop: '1rem', color: 'var(--text-primary)', fontSize: '0.875rem', lineHeight: 1.6 }}>
              {item.explanation_text ? item.explanation_text : "No explanation generated."}
            </div>
          </div>
        ))}
      </div>

      <div style={{ textAlign: 'center', marginTop: '4rem' }}>
        <button className="btn-retro" onClick={onRestart}>SCAN_ANOTHER_DOCUMENT</button>
      </div>
    </div>
  );
}
