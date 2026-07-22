"""
WebSocket Manager for real-time price/P&L updates.

Manages per-user WebSocket connections. Used by the monitor service
to push SL/target hit notifications and price updates.
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections keyed by user_id.
    Supports per-user messaging and admin broadcast.
    """

    def __init__(self):
        # user_id -> list of active WebSocket connections
        self._user_connections: Dict[str, List[WebSocket]] = {}
        # Admin connections (for global feed)
        self._admin_connections: List[WebSocket] = []

    async def connect(self, user_id: str, websocket: WebSocket, is_admin: bool = False):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if is_admin:
            self._admin_connections.append(websocket)
        if user_id not in self._user_connections:
            self._user_connections[user_id] = []
        self._user_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}, admin={is_admin}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if user_id in self._user_connections:
            if websocket in self._user_connections[user_id]:
                self._user_connections[user_id].remove(websocket)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        if websocket in self._admin_connections:
            self._admin_connections.remove(websocket)
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a specific user."""
        connections = self._user_connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_to_admins(self, message: dict):
        """Send a message to all connected admin WebSockets."""
        dead = []
        for ws in self._admin_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._admin_connections.remove(ws)

    async def broadcast_price_updates(self, updates: Dict[str, dict]):
        """
        Broadcast price updates to relevant users.
        updates: { user_id: { leg_id: { ltp, unrealized_pnl, ... } } }
        """
        for user_id, leg_updates in updates.items():
            await self.send_to_user(user_id, {
                "type": "price_update",
                "data": leg_updates,
                "timestamp": datetime.utcnow().isoformat(),
            })

    @property
    def connected_users_count(self) -> int:
        return len(self._user_connections)

    @property
    def connected_admins_count(self) -> int:
        return len(self._admin_connections)


# Global singleton
ws_manager = WebSocketManager()
