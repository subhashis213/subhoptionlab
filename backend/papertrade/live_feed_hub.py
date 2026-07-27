import asyncio
import threading
import logging
import json
from typing import Set, Dict, Any, Optional
from collections import defaultdict
import upstox_client
from upstox_client.feeder import MarketDataStreamerV3
from .upstox_guard import _get_access_token
from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)


def _extract_feeds_from_message(message) -> Dict[str, Any]:
    """
    Parse an Upstox protobuf FeedResponse into a flat dict of:
      { instrument_key: { ltp, cp, instrument_key, ... } }
    
    The Upstox FeedResponse protobuf structure is:
      FeedResponse.feeds = Map<instrument_key, Feed>
      Feed.ff.indexFF.ltpc.ltp  (for indices)
      Feed.ff.marketFF.ltpc.ltp  (for equities/options)
    """
    try:
        if hasattr(message, "DESCRIPTOR"):
            msg_dict = MessageToDict(message, preserving_proto_field_name=True)
        elif isinstance(message, dict):
            msg_dict = message
        else:
            return {}
        
        feeds_map = msg_dict.get("feeds", {})
        result = {}
        
        for instrument_key, feed_data in feeds_map.items():
            ff = feed_data.get("ff", {})
            
            ltp = None
            cp = None   # close/previous price
            vol = None
            oi = None
            
            if ff.get("indexFF"):
                idx = ff["indexFF"]
                ltpc = idx.get("ltpc", {})
                ltp = ltpc.get("ltp")
                cp = ltpc.get("cp")  # close price (prev day)
                mf = idx.get("marketOHLC", {})
            elif ff.get("marketFF"):
                mkt = ff["marketFF"]
                ltpc = mkt.get("ltpc", {})
                ltp = ltpc.get("ltp")
                cp = ltpc.get("cp")
                vol = mkt.get("volTraded")
                oi = mkt.get("openInterest")
            
            if ltp is not None:
                norm_key = instrument_key.replace(":", "|") if ":" in instrument_key else instrument_key
                item = {
                    "instrument_key": norm_key,
                    "last_price": float(ltp),
                    "ltp": float(ltp),
                }
                if cp is not None:
                    item["close_price"] = float(cp)
                    change = float(ltp) - float(cp)
                    item["net_change"] = round(change, 2)
                    item["change_percent"] = round((change / float(cp)) * 100, 2) if float(cp) > 0 else 0.0
                if vol is not None:
                    item["volume"] = int(vol)
                if oi is not None:
                    item["oi"] = int(oi)
                    
                result[norm_key] = item
                
        return result
    except Exception as e:
        logger.error(f"Error extracting feeds: {e}")
        return {}


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
        self.upgraded_keys: Set[str] = set()
        
        # We track how many clients are subscribed to each key so we can unsubscribe when 0
        self.key_subscribers = defaultdict(int)
        
        # Connected FastAPI websocket clients (we just store their queues)
        self.client_queues: Set[asyncio.Queue] = set()
        
        self.loop = None
        self._thread = None
        self.connected = False
        
        # Polling fallback
        self._poll_task: Optional[asyncio.Task] = None
        
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
        
        # Stop existing polling task
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            
        configuration = upstox_client.Configuration()
        configuration.access_token = token
        api_client = upstox_client.ApiClient(configuration)
        
        self.streamer = MarketDataStreamerV3(
            api_client=api_client,
            instrumentKeys=list(self.active_keys),
            mode="full"
        )
        self.streamer.on("message", self._on_message)
        self.streamer.on("open", self._on_open)
        self.streamer.on("error", self._on_error)
        self.streamer.on("close", self._on_close)
        
        self.streamer.auto_reconnect(True)
        
        self._thread = threading.Thread(target=self.streamer.connect, daemon=True)
        self._thread.start()
        logger.info("LiveFeedHub Upstox WebSocket thread started.")
        
        # Start polling fallback — ensures data keeps flowing even if WS has gaps
        self._poll_task = asyncio.create_task(self._polling_loop())

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

    def _subscribe_chunked(self, keys: list):
        if not keys or not self.streamer or not self.connected:
            return
            
        chunk_size = 100
        for i in range(0, len(keys), chunk_size):
            chunk = keys[i:i + chunk_size]
            try:
                self.streamer.subscribe(chunk, mode="full")
                logger.info(f"LiveFeedHub subscribed to chunk of {len(chunk)} keys.")
            except Exception as e:
                logger.error(f"Error subscribing to chunk in LiveFeedHub: {e}")

    async def _polling_loop(self):
        """
        REST API polling — fetches live quotes every 1s.
        fetch_quotes() handles pipe/colon normalization and deduplication.
        We broadcast under ALL known aliases so the frontend always finds a match.
        """
        from .upstox_guard import fetch_quotes
        logger.info("LiveFeedHub: Polling loop started (1s interval).")
        
        while True:
            try:
                await asyncio.sleep(1.0)
                
                if not self.active_keys or not self.client_queues:
                    continue
                
                from papertrade.key_cache import NUMERIC_TO_STRING, STRING_TO_NUMERIC
                
                # Upgrade WebSocket subscriptions if we discovered new string aliases
                if self.connected and self.streamer:
                    keys_to_subscribe = []
                    for k in list(self.active_keys):
                        norm = k.replace(":", "|") if ":" in k else k
                        alias = NUMERIC_TO_STRING.get(norm)
                        if alias and alias not in self.active_keys and alias not in self.upgraded_keys:
                            keys_to_subscribe.append(alias)
                            self.upgraded_keys.add(alias)
                    if keys_to_subscribe:
                        self._subscribe_chunked(keys_to_subscribe)
                
                # Batch all active_keys (fetch_quotes normalizes and deduplicates internally)
                keys_list = list(self.active_keys)[:500]
                batch_size = 50  # smaller batches = shorter URLs = no 414 errors
                
                for i in range(0, len(keys_list), batch_size):
                    batch = keys_list[i:i + batch_size]
                    if i > 0:
                        await asyncio.sleep(0.3)
                    
                    quotes = await fetch_quotes(batch)
                    if not quotes:
                        continue
                    
                    for instrument_key, quote in quotes.items():
                        if not quote or not isinstance(quote, dict):
                            continue
                        
                        ltp = quote.get("last_price", 0)
                        if not ltp:
                            continue
                            
                        ohlc = quote.get("ohlc", {})
                        close_price = float(ohlc.get("close", 0))
                        net_change = float(quote.get("net_change", 0))
                        change_pct = round((net_change / close_price) * 100, 2) if close_price > 0 else 0.0
                        
                        norm_key = instrument_key.replace(":", "|") if ":" in instrument_key else instrument_key
                        
                        base_msg = {
                            "ltp": float(ltp),
                            "last_price": float(ltp),
                            "net_change": round(net_change, 2),
                            "change_percent": change_pct,
                            "close_price": close_price,
                            "volume": int(quote.get("volume") or 0),
                            "oi": int(quote.get("oi") or 0),
                        }
                        
                        # Broadcast under all known aliases for this instrument
                        all_keys: set = {norm_key, instrument_key}
                        a1 = STRING_TO_NUMERIC.get(norm_key)
                        a2 = NUMERIC_TO_STRING.get(norm_key)
                        if a1: all_keys.add(a1)
                        if a2: all_keys.add(a2)
                        # Also add colon variant (some frontend lookups use colon form)
                        all_keys.add(norm_key.replace("|", ":"))
                        
                        # Also check instrument_token from quote data
                        itoken = quote.get("instrument_token")
                        if itoken:
                            ikey = str(itoken).replace(":", "|")
                            all_keys.add(ikey)
                            alias = NUMERIC_TO_STRING.get(ikey)
                            if alias: all_keys.add(alias)
                        
                        for key in all_keys:
                            msg = base_msg.copy()
                            msg["instrument_key"] = key
                            self._broadcast(msg)
                    
            except asyncio.CancelledError:
                logger.info("LiveFeedHub: Polling loop cancelled.")
                break
            except Exception as e:
                logger.error(f"LiveFeedHub polling error: {e}")
                await asyncio.sleep(2)

    def _on_open(self):
        self.connected = True
        logger.info("LiveFeedHub Upstox WebSocket CONNECTED.")
        if self.active_keys and self.streamer:
            self._subscribe_chunked(list(self.active_keys))
            
    def _on_close(self):
        self.connected = False
        logger.warning("LiveFeedHub Upstox WebSocket CLOSED.")
        
    def _on_error(self, error):
        logger.error(f"LiveFeedHub Upstox WebSocket ERROR: {error}")
        
    def _on_message(self, message):
        """
        Receive a FeedResponse from the Upstox streaming SDK.
        Parse it into per-instrument messages and broadcast to all frontend clients.
        """
        try:
            # Parse protobuf FeedResponse into flat { instrument_key: {...} } dict
            feeds = _extract_feeds_from_message(message)
            
            if not feeds:
                return
                
            # Broadcast each instrument separately so the frontend can map by key
            if self.loop and not self.loop.is_closed():
                for instrument_key, feed_data in feeds.items():
                    self.loop.call_soon_threadsafe(self._broadcast, feed_data)
                    
                    # Also broadcast for both STRING_TO_NUMERIC and NUMERIC_TO_STRING aliases
                    from papertrade.key_cache import STRING_TO_NUMERIC, NUMERIC_TO_STRING
                    norm_key = feed_data.get("instrument_key", instrument_key)
                    alias1 = STRING_TO_NUMERIC.get(norm_key)
                    alias2 = NUMERIC_TO_STRING.get(norm_key)
                    
                    for alias in (alias1, alias2):
                        if alias and alias != norm_key:
                            alias_data = feed_data.copy()
                            alias_data["instrument_key"] = alias
                            self.loop.call_soon_threadsafe(self._broadcast, alias_data)
                    
        except Exception as e:
            logger.error(f"LiveFeedHub message parse error: {e}")

    def _broadcast(self, msg: Dict[str, Any]):
        """Push a single instrument's data to all connected frontend clients."""
        dead_queues = set()
        for q in list(self.client_queues):
            try:
                if q.qsize() < 500:  # Increased buffer for fast data
                    q.put_nowait(msg)
                else:
                    # Queue full - drop oldest to keep up with live data
                    try:
                        q.get_nowait()
                    except Exception:
                        pass
                    q.put_nowait(msg)
            except Exception:
                dead_queues.add(q)
        
        # Clean up dead queues
        for q in dead_queues:
            self.client_queues.discard(q)

    def subscribe_keys(self, instrument_keys: list):
        new_keys_to_subscribe = []
        from papertrade.key_cache import NUMERIC_TO_STRING, STRING_TO_NUMERIC
        
        for k in instrument_keys:
            if self.key_subscribers[k] == 0:
                # Subscribe both the original key AND any known alias
                alias = NUMERIC_TO_STRING.get(k) or STRING_TO_NUMERIC.get(k)
                new_keys_to_subscribe.append(k)
                if alias and alias != k:
                    new_keys_to_subscribe.append(alias)
            self.key_subscribers[k] += 1
            self.active_keys.add(k)
            
        if new_keys_to_subscribe and self.connected and self.streamer:
            # Deduplicate
            unique = list(set(new_keys_to_subscribe))
            self._subscribe_chunked(unique)
            
    def unsubscribe_keys(self, instrument_keys: list):
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
        q = asyncio.Queue(maxsize=1000)
        self.client_queues.add(q)
        return q
        
    def unregister_client(self, q: asyncio.Queue):
        self.client_queues.discard(q)

live_feed_hub = LiveFeedHub()
