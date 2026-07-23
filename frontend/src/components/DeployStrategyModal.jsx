import React, { useState } from 'react';
import './DeployStrategyModal.css';

export default function DeployStrategyModal({ strategy, onClose, onDeploy }) {
  const [mode, setMode] = useState('paper');
  const [maxLoss, setMaxLoss] = useState(0);
  const [maxLots, setMaxLots] = useState(1);
  const [confirmText, setConfirmText] = useState('');
  const [loading, setLoading] = useState(false);

  if (!strategy) return null;

  const handleDeploy = async () => {
    if (mode === 'live' && confirmText !== 'I_CONFIRM_LIVE_TRADING') {
      alert("You must type the exact confirmation string for LIVE trading.");
      return;
    }

    setLoading(true);
    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      const res = await fetch(`${API_BASE}/api/live/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_id: strategy.id,
          mode: mode,
          max_daily_loss: Number(maxLoss),
          max_lots: Number(maxLots),
          confirm: confirmText
        })
      });
      
      const data = await res.json();
      if (data.status === 'success') {
        onDeploy(data.live_strategy_id);
      } else {
        alert("Deployment failed: " + JSON.stringify(data));
      }
    } catch (err) {
      alert("Network error during deployment");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content deploy-modal">
        <h2>Deploy Strategy: {strategy.name}</h2>
        <p className="subtitle">Execute this strategy in the Live/Paper engine.</p>
        
        <div className="form-group">
          <label>Execution Mode</label>
          <div className="mode-toggle">
            <button 
              className={`mode-btn ${mode === 'paper' ? 'active paper' : ''}`}
              onClick={() => setMode('paper')}
            >
              📄 Paper Trading
            </button>
            <button 
              className={`mode-btn ${mode === 'live' ? 'active live' : ''}`}
              onClick={() => setMode('live')}
            >
              🔥 Live Trading
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>Optional Global Max Daily Loss (Points/₹)</label>
          <input 
            type="number" 
            value={maxLoss} 
            onChange={e => setMaxLoss(e.target.value)} 
          />
          <small>Leave as 0 to rely purely on your strategy's individual leg Stop Losses. This is just an extra global kill-switch.</small>
        </div>

        <div className="form-group">
          <label>Number of Lots</label>
          <input 
            type="number" 
            value={maxLots} 
            min="1"
            onChange={e => setMaxLots(e.target.value)} 
          />
        </div>

        {mode === 'live' && (
          <div className="warning-box">
            <h4>⚠️ LIVE TRADING WARNING ⚠️</h4>
            <p>This will place REAL orders using your broker account with REAL MONEY. You are fully responsible for any financial losses.</p>
            <label>Type <strong>I_CONFIRM_LIVE_TRADING</strong> to unlock:</label>
            <input 
              type="text" 
              value={confirmText} 
              onChange={e => setConfirmText(e.target.value)} 
              placeholder="I_CONFIRM_LIVE_TRADING"
            />
          </div>
        )}

        <div className="modal-actions">
          <button className="btn-cancel" onClick={onClose} disabled={loading}>Cancel</button>
          <button 
            className={`btn-deploy ${mode}`} 
            onClick={handleDeploy}
            disabled={loading || (mode === 'live' && confirmText !== 'I_CONFIRM_LIVE_TRADING')}
          >
            {loading ? 'Deploying...' : `Deploy to ${mode.toUpperCase()}`}
          </button>
        </div>
      </div>
    </div>
  );
}
