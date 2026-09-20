import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function AuthModal() {
  const { login, register } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError("Please fill in both email and password.");
      return;
    }
    setSubmitting(true);
    try {
      if (isRegistering) {
        await register(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '440px', margin: '4rem auto', padding: '0 1rem' }}>
      <div className="retro-box" style={{ padding: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <h2 className="pixel-font" style={{ color: 'var(--accent-neon)', fontSize: '1.5rem', marginBottom: '0.5rem' }}>
            AUTHENTICATION REQUIRED
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Sign in to access your secure laboratory records
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
          <button
            type="button"
            className="btn-retro"
            style={{
              flex: 1,
              backgroundColor: !isRegistering ? 'var(--accent-neon)' : 'transparent',
              color: !isRegistering ? 'var(--bg-dark)' : 'var(--text-main)',
              borderColor: 'var(--accent-neon)',
            }}
            onClick={() => { setIsRegistering(false); setError(null); }}
          >
            LOGIN
          </button>
          <button
            type="button"
            className="btn-retro"
            style={{
              flex: 1,
              backgroundColor: isRegistering ? 'var(--accent-neon)' : 'transparent',
              color: isRegistering ? 'var(--bg-dark)' : 'var(--text-main)',
              borderColor: 'var(--accent-neon)',
            }}
            onClick={() => { setIsRegistering(true); setError(null); }}
          >
            REGISTER
          </button>
        </div>

        {error && (
          <div className="retro-box" style={{ borderColor: 'var(--accent-red)', padding: '0.75rem', marginBottom: '1rem', color: 'var(--accent-red)', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
              EMAIL ADDRESS
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                fontFamily: 'inherit',
                borderRadius: '4px',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={6}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                fontFamily: 'inherit',
                borderRadius: '4px',
              }}
            />
          </div>

          <button
            type="submit"
            className="btn-retro"
            disabled={submitting}
            style={{ marginTop: '0.5rem', width: '100%', padding: '0.85rem' }}
          >
            {submitting
              ? "AUTHENTICATING..."
              : isRegistering
              ? "CREATE ACCOUNT"
              : "SIGN IN"}
          </button>
        </form>
      </div>
    </div>
  );
}
