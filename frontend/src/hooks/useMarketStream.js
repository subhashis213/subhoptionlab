import { useEffect, useRef, useState, useCallback } from 'react'

let globalWs = null;
let reconnectTimeout = null;
let connectionCount = 0;
let subscriptionKeys = new Set();
let subscribers = new Set();
let isConnecting = false;

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

function connectWs() {
  if (globalWs || isConnecting) return;
  isConnecting = true;

  try {
    globalWs = new WebSocket(`${WS_URL}/ws/live-market`);
    
    globalWs.onopen = () => {
      console.log("Connected to Live Market WebSocket.");
      isConnecting = false;
      // Resubscribe to all active keys
      if (subscriptionKeys.size > 0) {
        globalWs.send(JSON.stringify({ action: "subscribe", keys: Array.from(subscriptionKeys) }));
      }
    };
    
    globalWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "pong") return;
        
        // Notify all hooked components
        for (const cb of subscribers) {
          cb(msg);
        }
      } catch (err) {
        console.error("WS Parse error", err);
      }
    };
    
    globalWs.onclose = () => {
      globalWs = null;
      isConnecting = false;
      console.log("Live Market WebSocket closed. Reconnecting...");
      clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectWs, 2000);
    };
    
    globalWs.onerror = (err) => {
      console.error("Live Market WebSocket Error:", err);
      globalWs.close();
    };
    
  } catch (err) {
    console.error("Live Market WebSocket setup error:", err);
    isConnecting = false;
    reconnectTimeout = setTimeout(connectWs, 2000);
  }
}

function disconnectWs() {
  if (globalWs && connectionCount <= 0) {
    globalWs.close();
    globalWs = null;
    isConnecting = false;
  }
}

export default function useMarketStream(keysToSubscribe = []) {
  const [marketData, setMarketData] = useState({});
  const bufferRef = useRef({});
  const animationFrameRef = useRef(null);

  const handleMessage = useCallback((msg) => {
    // If it's a raw protobuf dictionary
    let instrumentKey = msg.instrument_key;
    let ltp = null;
    
    // Upstox Protobuf structure can vary, typically:
    if (msg.ff) {
      if (msg.ff.indexFF && msg.ff.indexFF.ltpc) {
        ltp = msg.ff.indexFF.ltpc.ltp;
      } else if (msg.ff.marketFF && msg.ff.marketFF.ltpc) {
        ltp = msg.ff.marketFF.ltpc.ltp;
      }
    }
    
    // If it's an API fallback dictionary from the backend
    if (msg.last_price !== undefined) {
      ltp = msg.last_price;
    }

    if (ltp !== null && instrumentKey) {
      bufferRef.current[instrumentKey] = msg;
    }
    
    // Throttle rendering at 60 FPS using requestAnimationFrame
    if (!animationFrameRef.current) {
      animationFrameRef.current = requestAnimationFrame(() => {
        setMarketData(prev => ({...prev, ...bufferRef.current}));
        bufferRef.current = {}; // flush buffer
        animationFrameRef.current = null;
      });
    }
  }, []);

  useEffect(() => {
    // Register global listener
    subscribers.add(handleMessage);
    
    connectionCount++;
    if (connectionCount === 1) {
      connectWs();
    }
    
    // Subscribe to new keys
    if (keysToSubscribe.length > 0) {
      const newKeys = keysToSubscribe.filter(k => !subscriptionKeys.has(k));
      newKeys.forEach(k => subscriptionKeys.add(k));
      
      if (globalWs && globalWs.readyState === WebSocket.OPEN && newKeys.length > 0) {
        globalWs.send(JSON.stringify({ action: "subscribe", keys: newKeys }));
      }
    }
    
    return () => {
      subscribers.delete(handleMessage);
      
      connectionCount--;
      if (connectionCount <= 0) {
        disconnectWs();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [keysToSubscribe.join(","), handleMessage]);

  return marketData;
}
