import asyncio
import threading
import logging
import json
from typing import Set, Dict, Any
from collections import defaultdict
import upstox_client
from upstox_client.feeder import MarketDataStreamerV3
from .upstox_guard import _get_access_token
from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)

class LiveFeedHub:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LiveFeedHub, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
        
    def __init__(self):
        if self.initialized:
            return
            
        self.streamer = None
        self.active_keys: Set[str] = set()
        
        # We track how many clients are subscribed to each key so we can unsubscribe when 0
        self.key_subscribers = defaultdict(int)
        
        # Connected FastAPI websocket clients (we just store their queues)
        self.client_queues: Set[asyncio.Queue] = set()
        
        self.loop = None
        self._thread = None
        self.connected = False
        self.initialized = True


    async def start(self):
        self.loop = asyncio.get_event_loop()
        token = await _get_access_token()
        if not token:
            logger.warning("No Upstox token available for LiveFeedHub. Will retry when token is saved.")
            return
        
        await self._start_with_token(token)
    
    async def _start_with_token(self, token: str):
        """Internal method to (re)start the streamer with a given token."""
        # Stop existing streamer if running
        if self.streamer:
            try:
                self.streamer.disconnect()
            except Exception:
                pass
            self.streamer = None
            self.connected = False
            
        configuration = upstox_client.Configuration()
        configuration.access_token = token
        api_client = upstox_client.ApiClient(configuration)
        
        self.streamer = MarketDataStreamerV3(api_client=api_client, instrumentKeys=list(self.active_keys), mode="full")
        self.streamer.on("message", self._on_message)
        self.streamer.on("open", self._on_open)
        self.streamer.on("error", self._on_error)
        self.streamer.on("close", self._on_close)
        
        self.streamer.auto_reconnect(True)
        
        self._thread = threading.Thread(target=self.streamer.connect, daemon=True)
        self._thread.start()
        logger.info("LiveFeedHub Upstox WebSocket thread started.")

    async def restart_with_new_token(self):
        """Call this after a new token is saved to restart the live data stream."""
        logger.info("LiveFeedHub: Restarting with new token...")
        token = await _get_access_token()
        if not token:
            logger.warning("LiveFeedHub: No token found after restart attempt.")
            return
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        await self._start_with_token(token)
        logger.info("LiveFeedHub: Successfully restarted with new token.")


    def _on_open(self):
        self.connected = True
        logger.info("LiveFeedHub Upstox WebSocket CONNECTED.")
        if self.active_keys and self.streamer:
            self.streamer.subscribe(list(self.active_keys), mode="full")
            
    def _on_close(self):
        self.connected = False
        logger.warning("LiveFeedHub Upstox WebSocket CLOSED.")
        
    def _on_error(self, error):
        logger.error(f"LiveFeedHub Upstox WebSocket ERROR: {error}")
        
    def _on_message(self, message):
        """
        Message is either a parsed dict or a protobuf message object from Upstox SDK.
        """
        # Convert to dict if it's a protobuf message
        try:
            if hasattr(message, "DESCRIPTOR"):
                msg_dict = MessageToDict(message, preserving_proto_field_name=True)
            elif isinstance(message, dict):
                msg_dict = message
            else:
                msg_dict = dict(message)
                
            if not msg_dict:
                return
                
            # Broadcast to all async clients
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self._broadcast, msg_dict)
                
        except Exception as e:
            logger.error(f"LiveFeedHub message parse error: {e}")

    def _broadcast(self, msg_dict: Dict[str, Any]):
        # Push to all connected FastAPI clients
        for q in list(self.client_queues):
            try:
                # Keep queue small to prevent memory leaks if client is slow
                if q.qsize() < 100:
                    q.put_nowait(msg_dict)
            except Exception:
                pass

    def subscribe_keys(self, instrument_keys: list[str]):
        new_keys_to_subscribe = []
        for k in instrument_keys:
            if self.key_subscribers[k] == 0:
                new_keys_to_subscribe.append(k)
            self.key_subscribers[k] += 1
            self.active_keys.add(k)
            
        if new_keys_to_subscribe and self.connected and self.streamer:
            logger.info(f"LiveFeedHub subscribing to Upstox: {new_keys_to_subscribe}")
            self.streamer.subscribe(new_keys_to_subscribe, mode="full")
            
    def unsubscribe_keys(self, instrument_keys: list[str]):
        keys_to_unsubscribe = []
        for k in instrument_keys:
            if self.key_subscribers[k] > 0:
                self.key_subscribers[k] -= 1
                if self.key_subscribers[k] == 0:
                    keys_to_unsubscribe.append(k)
                    if k in self.active_keys:
                        self.active_keys.remove(k)
                        
        if keys_to_unsubscribe and self.connected and self.streamer:
            logger.info(f"LiveFeedHub unsubscribing from Upstox: {keys_to_unsubscribe}")
            self.streamer.unsubscribe(keys_to_unsubscribe)
            
    def register_client(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.client_queues.add(q)
        return q
        
    def unregister_client(self, q: asyncio.Queue):
        if q in self.client_queues:
            self.client_queues.remove(q)

live_feed_hub = LiveFeedHub()
