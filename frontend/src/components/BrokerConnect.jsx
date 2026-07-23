import React, { useState, useEffect } from 'react';
import './BrokerConnect.css';

export default function BrokerConnect() {
  const [status, setStatus] = useState(null);
  const [accessToken, setAccessToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchStatus = async () => {
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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

  const handleConnect = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/api/broker/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          broker: 'upstox',
          access_token: accessToken,
          api_key: apiKey
        })
      });
      
      const data = await res.json();
      if (data.status === 'success') {
        setMessage('Connected successfully!');
        setAccessToken('');
        setApiKey('');
        fetchStatus();
      } else {
        setMessage('Failed to connect.');
      }
    } catch (err) {
      setMessage('Error connecting to broker.');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/api/broker/disconnect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ broker: 'upstox' })
      });
      if (res.ok) {
        fetchStatus();
        setMessage('Disconnected successfully.');
      }
    } catch (err) {
      setMessage('Error disconnecting.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="broker-connect-container">
      <h2>Broker Connection</h2>
      <p className="broker-desc">Connect your Upstox account for live trading execution.</p>
      
      <div className="broker-status-card">
        <h3>Current Status: 
          <span className={`status-badge ${status?.connected ? 'active' : 'inactive'}`}>
            {status?.connected ? 'CONNECTED' : 'DISCONNECTED'}
          </span>
        </h3>
        
        {status?.connected && (
          <div className="active-connection">
            <p><strong>Broker:</strong> {status.broker}</p>
            <p><strong>Connected At:</strong> {status.connected_at}</p>
            <button className="btn-danger" onClick={handleDisconnect} disabled={loading}>
              {loading ? 'Disconnecting...' : 'Disconnect'}
            </button>
          </div>
        )}
      </div>

      {!status?.connected && (
        <form className="broker-form" onSubmit={handleConnect}>
          <div className="form-group">
            <label>Upstox Access Token</label>
            <textarea 
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              placeholder="eyJ0eXAiOiJKV1QiLCJrZX..."
              required
              rows={4}
            />
          </div>
          <div className="form-group">
            <label>API Key (Optional for some endpoints)</label>
            <input 
              type="text" 
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Your API Key"
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Connecting...' : 'Connect to Upstox'}
          </button>
          {message && <p className="status-message">{message}</p>}
        </form>
      )}
    </div>
  );
}
