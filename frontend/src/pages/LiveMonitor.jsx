import React, { useState, useEffect } from 'react';
import OptionChain from '../components/OptionChain';
import './LiveMonitor.css';

export default function LiveMonitor() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [walletBalance, setWalletBalance] = useState(null);

  const getNextTriggerString = (entryTimeStr) => {
    if (!entryTimeStr) return "Unknown";
    const [h, m, s] = entryTimeStr.split(':').map(Number);
    let targetDate = new Date();
    targetDate.setHours(h, m, s || 0, 0);

    if (new Date() > targetDate) {
        targetDate.setDate(targetDate.getDate() + 1);
    }
    while (targetDate.getDay() === 0 || targetDate.getDay() === 6) {
        targetDate.setDate(targetDate.getDate() + 1);
    }

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let dayStr = `${days[targetDate.getDay()]}, ${targetDate.getDate()} ${months[targetDate.getMonth()]} ${targetDate.getFullYear()}`;
    
    if (targetDate.toDateString() === new Date().toDateString()) {
        dayStr = `Today (${dayStr})`;
    }

    return `${dayStr} at ${entryTimeStr.substring(0,5)}`;
  };

  const fetchDeployed = async () => {
    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      const [stratRes, walletRes] = await Promise.all([
        fetch(`${API_BASE}/api/live/deployed`),
        fetch(`${API_BASE}/api/live/wallet`)
      ]);
      const stratData = await stratRes.json();
      setStrategies(stratData);
      
      const walletData = await walletRes.json();
      if (walletData.status === 'success') {
        setWalletBalance(walletData);
      }
    } catch (err) {
      console.error("Failed to fetch LiveMonitor data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployed();
    // Poll every 2 seconds for status updates
    const interval = setInterval(fetchDeployed, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleKill = async (id, status) => {
    const msg = status === 'waiting' ? "Are you sure you want to CANCEL this deployment?" : "Are you sure you want to SQUARE OFF this active strategy?";
    if(!window.confirm(msg)) return;
    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      await fetch(`${API_BASE}/api/live/${id}/kill`, { method: 'POST' });
      fetchDeployed();
    } catch (err) {
      console.error(err);
    }
  };

  const handleKillAll = async () => {
    if(!window.confirm("PANIC BUTTON: Are you sure you want to SQUARE OFF ALL strategies immediately?")) return;
    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      await fetch(`${API_BASE}/api/live/kill-all`, { method: 'POST' });
      fetchDeployed();
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetWallet = async () => {
    if(!window.confirm("Are you sure you want to reset your paper trading wallet back to ₹250,000?")) return;
    try {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      await fetch(`${API_BASE}/api/live/wallet/reset`, { method: 'POST' });
      fetchDeployed();
    } catch (err) {
      console.error(err);
    }
  };

  // Build a list of all open positions across strategies to pass to the OptionChain
  // For demo, we are mocking this based on the active strategy configurations
  // In reality we would fetch /api/live/{id}/status for positions.
  const activeStrategies = strategies.filter(s => s.status === 'active');
  const hasActive = activeStrategies.length > 0;

  return (
    <div className="live-monitor-container">
      <div className="live-header">
        <div className="header-left">
            <h2>🔴 Live & Paper Trading Monitor</h2>
        </div>
        
        <div className="header-right-actions">
            <div className="wallet-widget">
                <div className="wallet-details">
                    <span className="wallet-label">Paper Net Worth</span>
                    <span className={`wallet-amount ${walletBalance?.net_worth >= 250000 ? 'profit' : 'loss'}`}>
                        {walletBalance ? `₹${walletBalance.net_worth.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '₹---'}
                    </span>
                    {walletBalance && walletBalance.unrealized_pnl !== 0 && (
                        <div className={`wallet-unrealized ${walletBalance.unrealized_pnl >= 0 ? 'profit' : 'loss'}`} style={{fontSize: '0.8rem', marginTop: '2px'}}>
                            {walletBalance.unrealized_pnl >= 0 ? '+' : ''}₹{walletBalance.unrealized_pnl.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} Open PnL
                        </div>
                    )}
                </div>
                <button className="btn-wallet-reset" onClick={handleResetWallet} title="Reset to ₹250,000">↺</button>
            </div>
            
            <button 
            className="btn-panic" 
            onClick={handleKillAll}
            disabled={!hasActive}
            >
            🚨 KILL ALL POSITIONS 🚨
            </button>
        </div>
      </div>

      <div className="monitor-dashboard">
        <div className="left-panel">
          <div className="strategies-list-container">
            <h3>Deployed Strategies</h3>
            {loading && <p>Loading...</p>}
            {!loading && strategies.length === 0 && (
              <div className="empty-state">No deployed strategies. Go to Saved Strategies to deploy one.</div>
            )}
            
            <div className="deployed-strategies-grid">
              {strategies.map(strat => (
                <div key={strat._id} className={`deployed-card ${strat.mode} ${strat.status}`}>
                  <div className="card-top">
                    <h4>{strat.strategy_name || "Strategy"}</h4>
                    <span className={`status-badge ${strat.status}`}>{strat.status.toUpperCase()}</span>
                  </div>
                  
                  <div className="card-details">
                    <p><strong>Mode:</strong> {strat.mode.toUpperCase()}</p>
                    <p><strong>Max Daily Loss:</strong> {strat.max_daily_loss > 0 ? `₹${strat.max_daily_loss}` : 'Disabled'}</p>
                    <p><strong>Lots:</strong> {strat.max_lots}</p>
                    {strat.status === 'waiting' && (
                      <p className="trigger-time"><strong>Triggers:</strong> {getNextTriggerString(strat.entry_time)}</p>
                    )}
                    <p><strong>Exits:</strong> {strat.exit_time ? strat.exit_time.substring(0,5) : '15:15'}</p>
                    <p className="timestamp">Deployed: {new Date(strat.deployed_at).toLocaleTimeString()}</p>
                  </div>
                  
                  {(strat.status === 'active' || strat.status === 'waiting') && (
                    <button className="btn-square-off" onClick={() => handleKill(strat._id, strat.status)}>
                      {strat.status === 'waiting' ? 'Cancel Deployment' : 'Square Off'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="right-panel">
          {/* We pass empty positions for now, to be populated by real positions endpoint in full version */}
          <OptionChain deployedPositions={[]} />
        </div>
      </div>
    </div>
  );
}
