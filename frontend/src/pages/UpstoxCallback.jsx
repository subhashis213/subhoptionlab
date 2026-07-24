import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { API_BASE } from '../api/client';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export default function UpstoxCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing'); // processing | success | error
  const [message, setMessage] = useState('Exchanging authorization code with Upstox...');

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setStatus('error');
      setMessage('No authorization code provided by Upstox.');
      return;
    }

    const exchangeCode = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/broker/callback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            redirect_uri: `${window.location.origin}/broker/callback`
          })
        });

        const data = await res.json();
        if (res.ok && data.status === 'success') {
          setStatus('success');
          setMessage(data.message || 'Upstox connected successfully!');
          setTimeout(() => {
            navigate('/profile');
          }, 2500);
        } else {
          setStatus('error');
          setMessage(data.detail || 'Failed to exchange authorization code.');
        }
      } catch (err) {
        setStatus('error');
        setMessage('Network error connecting to platform backend.');
      }
    };

    exchangeCode();
  }, [searchParams, navigate]);

  return (
    <div style={{
      minHeight: '80vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      <div style={{
        background: 'var(--card-bg, #1a1e29)',
        border: '1px solid var(--border-color, #2a2f3d)',
        borderRadius: '16px',
        padding: '40px',
        maxWidth: '460px',
        width: '100%',
        textAlign: 'center',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
      }}>
        {status === 'processing' && (
          <>
            <Loader2 size={56} style={{ color: '#3b82f6', animation: 'spin 1.5s linear infinite', marginBottom: '16px' }} />
            <h2 style={{ marginBottom: '8px' }}>Connecting to Upstox</h2>
            <p style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.95rem' }}>{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 size={56} style={{ color: '#10b981', marginBottom: '16px' }} />
            <h2 style={{ marginBottom: '8px', color: '#10b981' }}>Connection Successful!</h2>
            <p style={{ color: 'var(--text-muted, #94a3b8)', marginBottom: '20px' }}>{message}</p>
            <p style={{ fontSize: '0.85rem', color: '#64748b' }}>Redirecting to profile...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <AlertCircle size={56} style={{ color: '#ef4444', marginBottom: '16px' }} />
            <h2 style={{ marginBottom: '8px', color: '#ef4444' }}>Connection Failed</h2>
            <p style={{ color: 'var(--text-muted, #94a3b8)', marginBottom: '24px' }}>{message}</p>
            <button 
              className="btn-primary" 
              onClick={() => navigate('/profile')}
              style={{ width: '100%' }}
            >
              Return to Settings
            </button>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
