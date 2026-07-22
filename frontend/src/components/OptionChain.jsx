import React, { useState, useEffect } from 'react';
import './OptionChain.css';

const MOCK_STRIKES = [
  58000, 58100, 58200, 58300, 58400, 58500, 58600, 58700, 58800, 58900, 59000
];

const ATM_STRIKE = 58500;

export default function OptionChain({ deployedPositions = [] }) {
  const [quotes, setQuotes] = useState({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Determine WebSocket URL based on current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/api/live/feed`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket Connected");
      setConnected(true);
      
      // Subscribe to mocked instruments
      const subs = MOCK_STRIKES.map(strike => [
        `BANKNIFTY_MOCK_TOKEN_CE_${strike}`,
        `BANKNIFTY_MOCK_TOKEN_PE_${strike}`
      ]).flat();
      
      // We'll also just subscribe to the generic token for now
      ws.send(JSON.stringify({ action: "subscribe", instrument: "BANKNIFTY_MOCK_TOKEN" }));
      subs.forEach(token => {
        ws.send(JSON.stringify({ action: "subscribe", instrument: token }));
      });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "initial" || msg.type === "quotes") {
          setQuotes(prev => ({...prev, ...msg.data}));
        }
      } catch (err) {
        console.error("WebSocket message parsing error:", err);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket Disconnected");
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  // Helper to check if a strike has an active position
  const getPositionForStrike = (strike, optionType) => {
    return deployedPositions.find(p => p.strike === strike && p.option_type === optionType && p.status === 'open');
  };

  return (
    <div className="option-chain-container">
      <div className="chain-header">
        <h3>Live Option Chain (BANKNIFTY)</h3>
        <span className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '🟢 Live Feed Active' : '🔴 Disconnected'}
        </span>
      </div>

      <div className="chain-table-wrapper">
        <table className="chain-table">
          <thead>
            <tr>
              <th colSpan="3" className="ce-header">CALLS (CE)</th>
              <th className="strike-header">STRIKE</th>
              <th colSpan="3" className="pe-header">PUTS (PE)</th>
            </tr>
            <tr>
              <th>Bid</th>
              <th>Ask</th>
              <th>LTP</th>
              <th></th>
              <th>LTP</th>
              <th>Bid</th>
              <th>Ask</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_STRIKES.map((strike) => {
              const cePos = getPositionForStrike(strike, 'CE');
              const pePos = getPositionForStrike(strike, 'PE');
              const isAtm = strike === ATM_STRIKE;
              
              // Mock fetching specific instrument tokens
              const ceToken = `BANKNIFTY_MOCK_TOKEN_CE_${strike}`;
              const peToken = `BANKNIFTY_MOCK_TOKEN_PE_${strike}`;
              
              // Fallback to the generic mock token if specific is unavailable
              const ceLtp = quotes[ceToken] || quotes["BANKNIFTY_MOCK_TOKEN"] || 100.0;
              const peLtp = quotes[peToken] || quotes["BANKNIFTY_MOCK_TOKEN"] || 100.0;

              return (
                <tr key={strike} className={isAtm ? 'atm-row' : ''}>
                  <td className="bid-ask">{(ceLtp - 0.5).toFixed(2)}</td>
                  <td className="bid-ask">{(ceLtp + 0.5).toFixed(2)}</td>
                  <td className={`ltp ce-ltp ${cePos ? 'active-position' : ''}`}>
                    {ceLtp.toFixed(2)}
                    {cePos && <span className="pos-badge">{cePos.action === 'SELL' ? 'S' : 'B'}</span>}
                  </td>
                  
                  <td className="strike-cell">
                    {isAtm && <span className="atm-indicator">ATM</span>}
                    {strike}
                  </td>
                  
                  <td className={`ltp pe-ltp ${pePos ? 'active-position' : ''}`}>
                    {peLtp.toFixed(2)}
                    {pePos && <span className="pos-badge">{pePos.action === 'SELL' ? 'S' : 'B'}</span>}
                  </td>
                  <td className="bid-ask">{(peLtp - 0.5).toFixed(2)}</td>
                  <td className="bid-ask">{(peLtp + 0.5).toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
