import React, { useState, useEffect } from 'react';
import { fetchSourceFileBlob } from '../services/api';

export default function ReviewDashboard({ reportId, sourceType, results: initialResults, onConfirm, onCancel }) {
  const [results, setResults] = useState(initialResults);
  const [isConfirming, setIsConfirming] = useState(false);
  const [sourceUrl, setSourceUrl] = useState(null);
  const [sourceError, setSourceError] = useState(false);

  // Fetch the source file with an authenticated request and expose it as a blob URL,
  // since <img>/<iframe> src attributes cannot send an Authorization header.
  useEffect(() => {
    if (!reportId) return undefined;
    let objectUrl;
    setSourceError(false);
    fetchSourceFileBlob(reportId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setSourceUrl(objectUrl);
      })
      .catch(() => setSourceError(true));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [reportId]);

  const handleUpdate = (id, field, value) => {
    setResults(prev => prev.map(item => 
      item.id === id ? { ...item, [field]: value, user_corrected: true } : item
    ));
  };



  const handleConfirmClick = async () => {
    setIsConfirming(true);
    await onConfirm(results);
    setIsConfirming(false);
  };

  return (
    <div style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <div>
          <h3 className="pixel-font" style={{ fontSize: '1.5rem', margin: 0, color: '#eab308' }}>STEP 1: REVIEW & CORRECT</h3>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Review OCR extraction against original document.</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn-retro" onClick={onCancel} disabled={isConfirming}>CANCEL</button>
          <button className="btn-retro primary" onClick={handleConfirmClick} disabled={isConfirming}>
            {isConfirming ? 'SAVING...' : 'CONFIRM_DATA'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '2rem', height: '600px' }}>
        {/* Document Viewer */}
        <div className="retro-box" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ backgroundColor: 'var(--bg-card)', borderBottom: '2px solid var(--border-color)', padding: '0.5rem', color: 'var(--text-secondary)' }} className="pixel-font">
            SOURCE_DOCUMENT
          </div>
          <div style={{ flex: 1, backgroundColor: '#000', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {reportId && sourceUrl && (
              sourceType === 'image' ? (
                <img 
                  src={sourceUrl} 
                  alt="Source Document"
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              ) : (
                <iframe 
                  src={sourceUrl} 
                  title="Source Document"
                  style={{ width: '100%', height: '100%', border: 'none' }}
                />
              )
            )}
            {reportId && !sourceUrl && sourceError && (
              <span style={{ color: 'var(--text-secondary)' }}>Could not load source document.</span>
            )}
          </div>
        </div>

        {/* Data Table */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem' }}>
          {results.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }} className="retro-box">
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-color)', backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>TEST_NAME</th>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>VALUE</th>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>UNIT</th>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>REF LOW</th>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>REF HIGH</th>
                  <th className="pixel-font" style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>FLAG</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item, idx) => (
                  <tr key={item.id || idx} style={{ borderBottom: '1px solid #27272a' }}>
                    <td style={{ padding: '0.5rem' }}>
                      <input 
                        type="text" 
                        value={item.raw_test_name || ''} 
                        onChange={(e) => handleUpdate(item.id, 'raw_test_name', e.target.value)}
                        style={{ width: '100%', background: 'transparent', border: '1px solid transparent', color: 'var(--text-primary)', fontWeight: 'bold', outline: 'none', padding: '0.25rem' }}
                        onFocus={(e) => e.target.style.border = '1px solid var(--border-color)'}
                        onBlur={(e) => e.target.style.border = '1px solid transparent'}
                      />
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      <input 
                        type="number" 
                        value={item.value ?? ''} 
                        onChange={(e) => handleUpdate(item.id, 'value', e.target.value === '' ? null : parseFloat(e.target.value))}
                        style={{ width: '80px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', padding: '0.25rem', fontFamily: 'var(--font-retro)', fontSize: '1.25rem', outline: 'none' }}
                      />
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      <input 
                        type="text" 
                        value={item.unit || ''} 
                        onChange={(e) => handleUpdate(item.id, 'unit', e.target.value)}
                        style={{ width: '80px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--accent-neon)', padding: '0.25rem', fontFamily: 'var(--font-retro)', fontSize: '1.25rem', outline: 'none' }}
                      />
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      <input 
                        type="number" 
                        value={item.reference_range_low ?? ''} 
                        onChange={(e) => handleUpdate(item.id, 'reference_range_low', e.target.value === '' ? null : parseFloat(e.target.value))}
                        style={{ width: '60px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', padding: '0.25rem', fontFamily: 'var(--font-retro)', fontSize: '1rem', outline: 'none' }}
                      />
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      <input 
                        type="number" 
                        value={item.reference_range_high ?? ''} 
                        onChange={(e) => handleUpdate(item.id, 'reference_range_high', e.target.value === '' ? null : parseFloat(e.target.value))}
                        style={{ width: '60px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', padding: '0.25rem', fontFamily: 'var(--font-retro)', fontSize: '1rem', outline: 'none' }}
                      />
                    </td>
                    <td style={{ padding: '0.5rem' }}>
                      <select 
                        value={item.flag || ''} 
                        onChange={(e) => handleUpdate(item.id, 'flag', e.target.value || null)}
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: item.flag && item.flag !== 'normal' ? 'var(--accent-red)' : 'var(--text-primary)', padding: '0.25rem', outline: 'none' }}
                      >
                        <option value="" style={{ background: '#18181b', color: 'var(--text-primary)' }}>--</option>
                        <option value="normal" style={{ background: '#18181b', color: 'var(--text-primary)' }}>normal</option>
                        <option value="H" style={{ background: '#18181b', color: 'var(--text-primary)' }}>H</option>
                        <option value="L" style={{ background: '#18181b', color: 'var(--text-primary)' }}>L</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '2rem' }}>All metrics deleted.</p>
          )}
        </div>
      </div>
    </div>
  );
}
