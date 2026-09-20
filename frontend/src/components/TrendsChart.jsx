import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getTrends } from '../services/api';

export default function TrendsChart({ results, onBack }) {
  const [selectedTest, setSelectedTest] = useState(results[0]?.raw_test_name || '');
  const [trendData, setTrendData] = useState(null);
  const [trendSummary, setTrendSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!selectedTest) return;
    let active = true;
    
    async function fetchTrends() {
      setLoading(true);
      setError('');
      try {
        const data = await getTrends("p_demo", selectedTest);
        if (active) {
          setTrendData(data.data);
          setTrendSummary(data.trend_description);
        }
      } catch (err) {
        if (active) setError(err.message || 'Failed to load trends');
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchTrends();
    
    return () => { active = false; };
  }, [selectedTest]);

  // Use a customized tooltip to fit the retro theme
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="retro-box" style={{ padding: '0.5rem', backgroundColor: '#000', border: '1px solid var(--accent-neon)' }}>
          <p className="pixel-font" style={{ margin: 0, color: 'var(--text-secondary)' }}>{label}</p>
          <p className="pixel-font" style={{ margin: 0, color: 'var(--accent-neon)' }}>
            VALUE: {payload[0].value} {payload[0].payload.unit}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '2px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <div>
          <h3 className="pixel-font" style={{ fontSize: '1.5rem', margin: 0, color: 'var(--accent-blue)' }}>STEP 3: HISTORICAL TRENDS</h3>
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Cross-report value tracking over time.</p>
        </div>
        <button className="btn-retro" onClick={onBack}>&lt; BACK TO EXPLANATIONS</button>
      </div>

      <div className="retro-box" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'center' }}>
          <label className="pixel-font" style={{ color: 'var(--text-secondary)' }}>SELECT METRIC:</label>
          <select 
            value={selectedTest} 
            onChange={(e) => setSelectedTest(e.target.value)}
            style={{ 
              background: 'var(--bg-dark)', 
              color: 'var(--text-primary)', 
              border: '2px solid var(--border-color)', 
              padding: '0.5rem', 
              fontFamily: 'var(--font-retro)', 
              fontSize: '1.25rem',
              outline: 'none'
            }}
          >
            {results.map(r => (
              <option key={r.id} value={r.raw_test_name}>{r.raw_test_name}</option>
            ))}
          </select>
        </div>

        {loading && <div className="pixel-font" style={{ color: 'var(--accent-blue)' }}>LOADING TREND DATA...</div>}
        {error && <div className="pixel-font" style={{ color: 'var(--accent-red)' }}>ERROR: {error}</div>}

        {!loading && !error && trendData && trendData.length > 0 && (
          <>
            <div style={{ height: '400px', width: '100%', marginBottom: '2rem' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="date" stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontFamily: 'monospace' }} />
                  <YAxis stroke="#a1a1aa" tick={{ fill: '#a1a1aa', fontFamily: 'monospace' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="value" stroke="var(--accent-neon)" strokeWidth={3} activeDot={{ r: 8, fill: 'var(--accent-neon)' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid var(--accent-blue)', padding: '1rem' }}>
              <strong className="pixel-font" style={{ color: 'var(--accent-blue)', display: 'block', marginBottom: '0.5rem' }}>TREND_ANALYSIS:</strong>
              <p style={{ margin: 0, color: 'var(--text-primary)' }}>{trendSummary}</p>
            </div>
          </>
        )}
        
        {!loading && !error && (!trendData || trendData.length === 0) && (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            Not enough historical data points to chart a trend for this test.
          </div>
        )}
      </div>
    </div>
  );
}
