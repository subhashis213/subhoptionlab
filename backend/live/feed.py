"""
Market feed manager.
Provides real-time price updates for the runner and frontend.
In a full production environment, this would connect to Upstox's Protobuf WebSocket.
For simplicity and reliability in this version, we use an async polling loop on the REST API
to fetch current option prices and broadcast them via FastAPI WebSockets.
"""

import asyncio
import logging
import os
import random
from typing import Dict, List, Any
import requests
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MarketFeed:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscribed_instruments: set[str] = set()
        self.latest_quotes: Dict[str, float] = {}
        self._running = False
        self._task = None

    async def connect_client(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial state
        await websocket.send_json({"type": "initial", "data": self.latest_quotes})

    def disconnect_client(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.disconnect_client(connection)

    def subscribe(self, instrument_token: str):
        """Add an instrument to the polling list."""
        self.subscribed_instruments.add(instrument_token)

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_market_data())
            logger.info("Market feed started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("Market feed stopped.")

    async def _poll_market_data(self):
        """Polls Upstox REST API for quotes of subscribed instruments."""
        while self._running:
            try:
                if not self.subscribed_instruments:
                    await asyncio.sleep(2)
                    continue

                token = os.getenv("UPSTOX_ACCESS_TOKEN")
                if token and token != "mock_token":
                    # Fetch real data
                    instruments_str = ",".join(self.subscribed_instruments)
                    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={instruments_str}"
                    headers = {
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
                    }
                    
                    # Run synchronous request in thread pool
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: requests.get(url, headers=headers, timeout=5)
                    )
                    
                    if response.status_code == 200:
                        data = response.json().get("data", {})
                        updates = {}
                        for key, quote_info in data.items():
                            ltp = quote_info.get("last_price")
                            if ltp:
                                self.latest_quotes[key] = ltp
                                updates[key] = ltp
                        
                        if updates:
                            await self.broadcast({"type": "quotes", "data": updates})
                    else:
                        logger.warning(f"Upstox quote API error: {response.status_code} {response.text}")
                else:
                    # Simulated mock data for paper trading when no API key is provided
                    updates = {}
                    for inst in self.subscribed_instruments:
                        # Random walk around 100 for mock
                        current = self.latest_quotes.get(inst, 100.0)
                        mock_ltp = round(max(0.05, current + random.uniform(-1, 1)), 2)
                        self.latest_quotes[inst] = mock_ltp
                        updates[inst] = mock_ltp
                        
                    await self.broadcast({"type": "quotes", "data": updates})
                    
            except Exception as e:
                logger.error(f"Error in market feed polling loop: {e}")
                
            await asyncio.sleep(1)  # Poll every 1 second


# Global singleton feed instance
feed_manager = MarketFeed()
