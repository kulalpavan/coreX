import React, { useState, useEffect } from 'react';
import { listUserReports, deleteReportApi } from '../services/api';

export default function PreviousRecords({ onViewReport, onNewReport }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUserReports();
      setReports(data || []);
    } catch (err) {
      setError(err.message || "Failed to load report history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDelete = async (reportId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }
    setDeletingId(reportId);
    try {
      await deleteReportApi(reportId);
      setReports(prev => prev.filter(r => r.id !== reportId));
    } catch (err) {
      alert(err.message || "Failed to delete report.");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return isoString;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <h3 className="pixel-font" style={{ color: 'var(--accent-neon)' }}>LOADING PREVIOUS RECORDS...</h3>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '960px', margin: '2rem auto', padding: '0 1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 className="pixel-font" style={{ fontSize: '1.5rem', color: 'var(--accent-neon)' }}>
            PREVIOUS RECORDS
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Your saved medical reports and laboratory histories
          </p>
        </div>
        <button className="btn-retro" onClick={onNewReport}>
          + NEW REPORT
        </button>
      </div>

      {error && (
        <div className="retro-box" style={{ borderColor: 'var(--accent-red)', padding: '1rem', marginBottom: '1.5rem', color: 'var(--accent-red)' }}>
          {error}
        </div>
      )}

      {reports.length === 0 ? (
        <div className="retro-box" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
          <h3 className="pixel-font" style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            NO RECORDS FOUND
          </h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            You haven't processed or saved any medical reports yet.
          </p>
          <button className="btn-retro" onClick={onNewReport}>
            UPLOAD A REPORT NOW
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {reports.map((report) => {
            const isConfirmed = report.status === 'confirmed';
            return (
              <div
                key={report.id}
                className="retro-box"
                style={{
                  display: 'flex',
                  justify: 'space-between',
                  alignItems: 'center',
                  padding: '1.25rem',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div style={{ flex: '1 1 300px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-main)' }}>
                      {report.filename}
                    </h3>
                    <span
                      style={{
                        padding: '0.15rem 0.5rem',
                        fontSize: '0.75rem',
                        borderRadius: '3px',
                        border: '1px solid',
                        borderColor: isConfirmed ? 'var(--accent-neon)' : 'var(--accent-amber, #f59e0b)',
                        color: isConfirmed ? 'var(--accent-neon)' : 'var(--accent-amber, #f59e0b)',
                        fontWeight: 'bold',
                      }}
                    >
                      {isConfirmed ? 'Validated' : 'Pending Review'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <span>Uploaded: {formatDate(report.created_at)}</span>
                    {report.report_date && <span>Report Date: {report.report_date}</span>}
                    <span>Parameters: {report.test_count}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button
                    className="btn-retro"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                    onClick={() => onViewReport(report)}
                  >
                    VIEW
                  </button>
                  <button
                    className="btn-retro"
                    disabled={deletingId === report.id}
                    style={{
                      padding: '0.5rem 1rem',
                      fontSize: '0.85rem',
                      borderColor: 'var(--accent-red)',
                      color: 'var(--accent-red)',
                    }}
                    onClick={() => handleDelete(report.id, report.filename)}
                  >
                    {deletingId === report.id ? 'DELETING...' : 'DELETE'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
