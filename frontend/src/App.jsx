import React, { useState } from 'react';
import Header from './components/Header';
import Hero from './components/Hero';
import ReviewDashboard from './components/ReviewDashboard';
import ExplanationDashboard from './components/ExplanationDashboard';
import TrendsChart from './components/TrendsChart';
import ChatInterface from './components/ChatInterface';
import PreviousRecords from './components/PreviousRecords';
import AuthModal from './components/AuthModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { uploadReport, getExtraction, confirmReport, exportPdf } from './services/api';

function MainApp() {
  const { isAuthenticated, loading } = useAuth();
  const [screen, setScreen] = useState('upload'); // 'upload', 'review', 'explanation', 'trends', 'previous_records'
  const [results, setResults] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [sourceType, setSourceType] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [disclaimer, setDisclaimer] = useState('');

  const handleFileSelect = async (file) => {
    setIsUploading(true);
    setError(null);
    setResults(null);
    setReportId(null);
    try {
      const uploadData = await uploadReport(file);
      const repId = uploadData.report_id;
      
      if (!repId) {
        throw new Error("Upload succeeded but no report_id was returned.");
      }
      
      setReportId(repId);
      
      const extractionData = await getExtraction(repId);
      
      if (extractionData.results && extractionData.results.length > 0) {
        setResults(extractionData.results);
        setSourceType(extractionData.source_type);
        setScreen('review');
      } else {
        setError('Extraction completed but no results were found. Try a clearer scan.');
      }
    } catch (err) {
      setError(err.message || "Failed to process the report.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirm = async (confirmedResults) => {
    setIsUploading(true);
    setError(null);
    try {
      const confirmRes = await confirmReport(reportId, confirmedResults);
      setResults(confirmRes.results || []);
      if (confirmRes.disclaimer) {
        setDisclaimer(confirmRes.disclaimer);
      }
      setScreen('explanation');
    } catch (err) {
      setError(err.message || "Failed to confirm report.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleExportPdf = async () => {
    setIsUploading(true);
    try {
      const blob = await exportPdf(reportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `PixelCraft_Summary_${reportId || "export"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Failed to export PDF summary.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleRestart = () => {
    setResults(null);
    setReportId(null);
    setError(null);
    setScreen('upload');
  };

  const handleViewPreviousRecord = async (report) => {
    setIsUploading(true);
    setError(null);
    try {
      setReportId(report.id);
      const extractionData = await getExtraction(report.id);
      setResults(extractionData.results || []);
      setSourceType(extractionData.source_type);
      if (extractionData.status === 'confirmed') {
        setScreen('explanation');
      } else {
        setScreen('review');
      }
    } catch (err) {
      setError(err.message || "Could not open selected report.");
    } finally {
      setIsUploading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <h2 className="pixel-font" style={{ color: 'var(--accent-neon)' }}>INITIALIZING CLARIFY LABS...</h2>
      </div>
    );
  }

  return (
    <div className="App">
      <Header currentScreen={screen} setScreen={setScreen} onRestart={handleRestart} />
      
      <main className="industrial-container">
        {!isAuthenticated ? (
          <AuthModal />
        ) : (
          <>
            {screen === 'upload' && !isUploading && (
              <Hero onFileSelect={handleFileSelect} isUploading={isUploading} />
            )}
            
            {screen === 'previous_records' && !isUploading && (
              <PreviousRecords
                onViewReport={handleViewPreviousRecord}
                onNewReport={handleRestart}
              />
            )}
            
            {isUploading && (
              <div style={{ textAlign: 'center', padding: '4rem' }}>
                <h2 className="pixel-font" style={{ color: 'var(--accent-neon)' }}>INITIATING PROTOCOL...</h2>
                <p style={{ color: 'var(--text-secondary)' }}>Please hold. Neural engine is processing document.</p>
              </div>
            )}

            {error && (
              <div className="retro-box" style={{ borderColor: 'var(--accent-red)', padding: '1rem', marginTop: '2rem', textAlign: 'center' }}>
                <h3 className="pixel-font" style={{ color: 'var(--accent-red)' }}>CRITICAL ERROR</h3>
                <p>{error}</p>
                <button className="btn-retro" style={{ marginTop: '1rem' }} onClick={() => setError(null)}>DISMISS</button>
              </div>
            )}

            {screen === 'review' && results && !isUploading && (
              <ReviewDashboard 
                reportId={reportId}
                sourceType={sourceType}
                results={results} 
                onConfirm={handleConfirm} 
                onCancel={handleRestart}
              />
            )}

            {screen === 'explanation' && results && !isUploading && (
              <>
                <ExplanationDashboard 
                  results={results} 
                  disclaimer={disclaimer}
                  onExportPdf={handleExportPdf}
                  onViewTrends={() => setScreen('trends')}
                  onRestart={handleRestart}
                />
                <ChatInterface reportId={reportId} />
              </>
            )}

            {screen === 'trends' && results && (
              <TrendsChart 
                results={results} 
                onBack={() => setScreen('explanation')}
              />
            )}
          </>
        )}
      </main>

      <footer style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        <p className="pixel-font">PIXELCRAFT LAB SCANNER // v2.0</p>
      </footer>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;

