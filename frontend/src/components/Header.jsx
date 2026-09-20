import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Header({ currentScreen, setScreen, onRestart }) {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <header style={{ padding: '1.25rem 2rem', borderBottom: '2px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', cursor: 'pointer' }} onClick={() => isAuthenticated && setScreen && setScreen('upload')}>
        <div style={{ width: '32px', height: '32px', backgroundColor: 'var(--accent-neon)', display: 'grid', placeItems: 'center' }}>
          <span style={{ color: 'var(--bg-dark)', fontWeight: 'bold' }}>PC</span>
        </div>
        <h1 className="pixel-font" style={{ fontSize: '1.5rem', margin: 0 }}>PIXELCRAFT <span style={{ color: 'var(--text-secondary)' }}>// LAB SCANNER</span></h1>
      </div>

      {isAuthenticated && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <button
            className="btn-retro"
            style={{
              padding: '0.4rem 0.85rem',
              fontSize: '0.8rem',
              backgroundColor: currentScreen === 'upload' ? 'var(--accent-neon)' : 'transparent',
              color: currentScreen === 'upload' ? 'var(--bg-dark)' : 'var(--text-main)',
            }}
            onClick={() => {
              if (onRestart) onRestart();
              if (setScreen) setScreen('upload');
            }}
          >
            NEW REPORT
          </button>
          
          <button
            className="btn-retro"
            style={{
              padding: '0.4rem 0.85rem',
              fontSize: '0.8rem',
              backgroundColor: currentScreen === 'previous_records' ? 'var(--accent-neon)' : 'transparent',
              color: currentScreen === 'previous_records' ? 'var(--bg-dark)' : 'var(--text-main)',
            }}
            onClick={() => setScreen && setScreen('previous_records')}
          >
            PREVIOUS RECORDS
          </button>

          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', padding: '0.2rem 0.6rem', border: '1px solid var(--border-color)', borderRadius: '3px' }}>
            {user?.email}
          </span>

          <button
            className="btn-retro"
            style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem', borderColor: 'var(--accent-red)', color: 'var(--accent-red)' }}
            onClick={() => logout()}
          >
            LOGOUT
          </button>
        </div>
      )}
    </header>
  );
}

