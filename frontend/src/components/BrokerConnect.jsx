import React, { useState, useEffect } from 'react';
import { API_BASE } from '../api/client';
import { 
  Key, Zap, CheckCircle2, XCircle, ExternalLink, Copy, Check, 
  HelpCircle, ShieldCheck, ChevronDown, ChevronUp, RefreshCw 
} from 'lucide-react';
import './BrokerConnect.css';

export default function BrokerConnect() {
  const [status, setStatus] = useState(null);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [manualToken, setManualToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [savingKeys, setSavingKeys] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [copied, setCopied] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [showGuide, setShowGuide] = useState(true);

  const redirectUri = `${window.location.origin}/broker/callback`;

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/broker/status?broker=upstox`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch broker status:", err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleCopyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveKeys = async (e) => {
    e.preventDefault();
    setSavingKeys(true);
    setMessage({ text: '', type: '' });

    try {
      const res = await fetch(`${API_BASE}/api/broker/save-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: apiKey,
          api_secret: apiSecret,
          redirect_uri: redirectUri,
          broker: 'upstox'
        })
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setMessage({ text: 'API Key & Secret saved successfully!', type: 'success' });
        setApiKey('');
        setApiSecret('');
        fetchStatus();
      } else {
        setMessage({ text: data.detail || 'Failed to save keys.', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Error saving keys.', type: 'error' });
    } finally {
      setSavingKeys(false);
    }
  };

  const handleOneClickLogin = async () => {
    setLoading(true);
    setMessage({ text: '', type: '' });

    try {
      const res = await fetch(`${API_BASE}/api/broker/login-url?redirect_uri=${encodeURIComponent(redirectUri)}&broker=upstox`);
      const data = await res.json();

      if (res.ok && data.login_url) {
        // Redirect user to Upstox official login dialog
        window.location.href = data.login_url;
      } else {
        setMessage({ text: data.detail || 'Please configure your API Key first.', type: 'error' });
        setLoading(false);
      }
    } catch (err) {
      setMessage({ text: 'Failed to initiate 1-Click Login.', type: 'error' });
      setLoading(false);
    }
  };

  const handleManualConnect = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ text: '', type: '' });

    try {
      const res = await fetch(`${API_BASE}/api/broker/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          broker: 'upstox',
          access_token: manualToken,
        })
      });

      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setMessage({ text: 'Access Token saved & connected successfully!', type: 'success' });
        setManualToken('');
        fetchStatus();
      } else {
        setMessage({ text: data.detail || 'Failed to save token.', type: 'error' });
      }
    } catch (err) {
      setMessage({ text: 'Error connecting to broker.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/broker/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ broker: 'upstox' })
      });
      if (res.ok) {
        fetchStatus();
        setMessage({ text: 'Disconnected successfully.', type: 'success' });
      }
    } catch (err) {
      setMessage({ text: 'Error disconnecting.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="broker-connect-container">
      <div className="broker-header">
        <div className="broker-title">
          <Zap size={24} className="icon-gold" />
          <div>
            <h2>Upstox Broker Integration</h2>
            <p className="broker-desc">Automated 1-Click daily login & live market data connection</p>
          </div>
        </div>
        <span className={`status-pill ${status?.connected ? 'connected' : 'disconnected'}`}>
          {status?.connected ? (
            <><CheckCircle2 size={14} /> CONNECTED</>
          ) : (
            <><XCircle size={14} /> DISCONNECTED</>
          )}
        </span>
      </div>

      {message.text && (
        <div className={`alert-banner ${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Connection Quick Actions */}
      <div className="connection-card">
        {status?.connected ? (
          <div className="connected-info">
            <div className="connected-details">
              <div>
                <span className="label">Active Broker</span>
                <strong>Upstox API v2</strong>
              </div>
              <div>
                <span className="label">Last Authorized</span>
                <strong>{status.connected_at || 'Active'}</strong>
              </div>
            </div>
            <div className="connected-actions">
              <button className="btn-secondary" onClick={handleOneClickLogin} disabled={loading}>
                <RefreshCw size={16} className={loading ? 'spin' : ''} />
                Renew Token (1-Click)
              </button>
              <button className="btn-danger" onClick={handleDisconnect} disabled={loading}>
                Disconnect
              </button>
            </div>
          </div>
        ) : (
          <div className="connect-prompt">
            <div className="prompt-text">
              <h3>Ready to Connect?</h3>
              <p>Once your API Key is saved below, click 1-Click Login to authorize daily in seconds.</p>
            </div>
            <button className="btn-success-large" onClick={handleOneClickLogin} disabled={loading}>
              <Zap size={20} />
              {loading ? 'Redirecting to Upstox...' : 'Connect Upstox (1-Click Login)'}
            </button>
          </div>
        )}
      </div>

      {/* Interactive Step-by-Step Upstox App Guide */}
      <div className="guide-card">
        <div className="guide-header" onClick={() => setShowGuide(!showGuide)}>
          <div className="guide-title">
            <HelpCircle size={20} className="icon-blue" />
            <h3>📖 How to Create Upstox Developer App & API Key</h3>
          </div>
          <button className="btn-icon">
            {showGuide ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>

        {showGuide && (
          <div className="guide-body">
            <p className="guide-intro">
              Upstox requires a free Developer App to generate API keys. Follow these 5 quick steps (takes 2 minutes):
            </p>

            <div className="guide-steps">
              <div className="step-item">
                <div className="step-number">1</div>
                <div className="step-content">
                  <h4>Open Upstox Developer Portal</h4>
                  <p>Log in to your Upstox account at the developer apps portal.</p>
                  <a 
                    href="https://account.upstox.com/developer/apps" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="guide-link-btn"
                  >
                    Open Developer Console <ExternalLink size={14} />
                  </a>
                </div>
              </div>

              <div className="step-item">
                <div className="step-number">2</div>
                <div className="step-content">
                  <h4>Click "Create New App"</h4>
                  <p>In the apps dashboard, click the <strong>New App</strong> button.</p>
                </div>
              </div>

              <div className="step-item">
                <div className="step-number">3</div>
                <div className="step-content">
                  <h4>Fill App Details & Paste Redirect URI</h4>
                  <p>Set App Name (e.g. <code>MyTradingBot</code>) and copy-paste this Redirect URI into the <strong>Redirect URL</strong> field:</p>
                  <div className="copy-box">
                    <code>{redirectUri}</code>
                    <button type="button" onClick={handleCopyRedirectUri} className="btn-copy">
                      {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                      {copied ? 'Copied!' : 'Copy URI'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="step-item">
                <div className="step-number">4</div>
                <div className="step-content">
                  <h4>Copy API Key & API Secret</h4>
                  <p>After creating the app, click on your app to reveal the <strong>API Key</strong> and <strong>API Secret</strong>.</p>
                </div>
              </div>

              <div className="step-item">
                <div className="step-number">5</div>
                <div className="step-content">
                  <h4>Save API Keys Below & Click 1-Click Login!</h4>
                  <p>Paste your API Key and Secret into the form below and click Save. That's it! You never need to edit server files again.</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* API Key & Secret Form */}
      <div className="credentials-card">
        <h3><Key size={18} /> Configure App Credentials</h3>
        <p className="card-sub">Save your Upstox API Key & Secret once so 1-Click Login works anytime.</p>

        <form onSubmit={handleSaveKeys} className="keys-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Upstox API Key (Client ID)</label>
              <input 
                type="text" 
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={status?.api_key_masked ? `Current: ${status.api_key_masked}` : 'e.g. 9b8c2d1e-xxxx-xxxx'}
                required={!status?.has_keys}
              />
            </div>

            <div className="form-group">
              <label>Upstox API Secret (Client Secret)</label>
              <input 
                type="password" 
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder={status?.has_keys ? '••••••••••••••••' : 'Your App Secret'}
                required={!status?.has_keys}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={savingKeys}>
            <ShieldCheck size={18} />
            {savingKeys ? 'Saving Credentials...' : 'Save App Credentials'}
          </button>
        </form>
      </div>

      {/* Manual Access Token Option */}
      <div className="manual-section">
        <button 
          className="manual-toggle-btn" 
          type="button" 
          onClick={() => setShowManual(!showManual)}
        >
          <span>Advanced: Paste Raw Access Token Manually</span>
          {showManual ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showManual && (
          <form className="manual-form" onSubmit={handleManualConnect}>
            <p className="field-hint">If you already have a 24h JWT token, paste it here directly.</p>
            <div className="form-group">
              <textarea 
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="eyJ0eXAiOiJKV1QiLCJrZX..."
                rows={3}
                required
              />
            </div>
            <button type="submit" className="btn-secondary" disabled={loading}>
              Save Raw Access Token
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
