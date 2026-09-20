import React, { useRef } from 'react';

export default function Hero({ onFileSelect, isUploading }) {
  const fileInputRef = useRef(null);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  };

  return (
    <section className="scanlines" style={{ padding: '4rem 0', position: 'relative' }}>
      


      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <span className="pixel-font" style={{ background: 'var(--accent-neon)', color: 'var(--bg-dark)', padding: '4px 8px', fontWeight: 'bold' }}>
          [NEW] // OCR V2.0 LIVE
        </span>
        <h2 className="pixel-font" style={{ fontSize: '3.5rem', marginTop: '1rem', lineHeight: 1.1 }}>
          UPLOAD WITHOUT LIMITS.<br/>
          <span style={{ color: 'var(--accent-neon)' }}>PIXEL-PERFECT.</span>
        </h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '1rem', maxWidth: '600px', margin: '1rem auto' }}>
          Industrial-grade medical report parsing. Drag and drop your lab results below to initiate extraction sequence.
        </p>
      </div>

      <div className="retro-box" style={{ maxWidth: '600px', margin: '0 auto', padding: '1rem' }}>
        <div className="dropzone" onClick={handleClick}>
          <input 
            type="file" 
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/*,application/pdf"
          />
          <div className="pixel-font" style={{ fontSize: '2rem', color: 'var(--accent-neon)' }}>
            +
          </div>
          <p className="pixel-font" style={{ fontSize: '1.25rem' }}>
            {isUploading ? "PROCESSING DATA..." : "CLICK OR DROP FILE HERE"}
          </p>
          {!isUploading && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              SUPPORTS PDF, PNG, JPG
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
