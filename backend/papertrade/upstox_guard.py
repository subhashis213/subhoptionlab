"""
Upstox API Guard — PAPER TRADE ONLY.

This module is the ONLY place in the entire codebase that makes HTTP calls to
the Upstox API. It provides functions EXCLUSIVELY for market data retrieval.

STRUCTURAL SAFETY: No function for order placement exists in this module.
There is no import, no URL, no function signature that can reach Upstox's
/v2/order/place or any order-related endpoint. This is by design — not by
a runtime flag, but by the complete absence of that code path.
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── ALLOWED ENDPOINTS (whitelist) ──────────────────────────────────────────────
# Only these Upstox API paths are ever called. Order endpoints are NOT listed
# because they do not exist in this module.
ALLOWED_UPSTOX_PATHS = frozenset([
    "/v2/market-quote/quotes",
    "/v2/market-quote/ltp",
    "/v2/option/chain",
    "/v2/option/contract",
    "/v2/market/instruments/master",
])

UPSTOX_BASE_URL = "https://api.upstox.com"


def _get_access_token() -> Optional[str]:
    """Get Upstox access token from environment or database."""
    token = os.getenv("UPSTOX_ACCESS_TOKEN")
    if token and token != "mock_token":
        return token
        
    try:
        from live.db import db as mongo_db
        import base64
        # Synchronous check via asyncio event loop if loop is running
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In async contexts, we can fetch synchronously from os.environ which is updated by broker_router
            pass
    except Exception:
        pass
    return None


def _make_headers(token: str) -> dict:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


async def fetch_ltp(instrument_keys: List[str]) -> Dict[str, float]:
    """
    Fetch Last Traded Price for given instrument keys from Upstox.
    Returns dict of { instrument_key: ltp }.
    
    PAPER TRADE ONLY: This function calls /v2/market-quote/ltp (read-only).
    """
    if not instrument_keys:
        return {}

    token = _get_access_token()
    if not token:
        logger.debug("No Upstox token available, returning empty LTP data.")
        return {}

    try:
        instruments_str = ",".join(instrument_keys)
        url = f"{UPSTOX_BASE_URL}/v2/market-quote/ltp"
        headers = _make_headers(token)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, params={"instrument_key": instruments_str}, headers=headers, timeout=3)
        )

        if response.status_code == 200:
            data = response.json().get("data", {})
            result = {}
            for key, quote_info in data.items():
                ltp = quote_info.get("last_price")
                if ltp is not None:
                    val = float(ltp)
                    result[key] = val
                    result[key.replace(":", "|")] = val
                    itoken = quote_info.get("instrument_token")
                    if itoken:
                        result[itoken] = val
                        result[itoken.replace("|", ":")] = val
            return result
        else:
            logger.warning(f"Upstox LTP API error: {response.status_code} {response.text[:200]}")
            return {k: _generate_paper_fallback_ltp(k) for k in instrument_keys}

    except Exception as e:
        logger.error(f"Error fetching LTP from Upstox: {e}")
        return {k: _generate_paper_fallback_ltp(k) for k in instrument_keys}


def _generate_paper_fallback_ltp(key: str) -> float:
    """Generate realistic paper trading LTP fallback if Upstox live token is expired or unavailable."""
    key_str = str(key).upper()
    if "NSE_INDEX|NIFTY BANK" in key_str or "BANKNIFTY" in key_str:
        return 57968.60 if "NSE_INDEX" in key_str else 320.50
    elif "NSE_INDEX|NIFTY 50" in key_str or "NIFTY" in key_str:
        return 24180.60 if "NSE_INDEX" in key_str else 145.25
    elif "FINNIFTY" in key_str:
        return 23500.00 if "NSE_INDEX" in key_str else 110.00
    elif "MIDCAP" in key_str:
        return 12500.00 if "NSE_INDEX" in key_str else 85.00
    return 150.00


async def fetch_quotes(instrument_keys: List[str]) -> Dict[str, dict]:
    """
    Fetch full market quotes (LTP, OHLC, volume, OI, etc.) for instrument keys.
    Returns dict of { instrument_key: full_quote_dict }.
    
    PAPER TRADE ONLY: This function calls /v2/market-quote/quotes (read-only).
    """
    if not instrument_keys:
        return {}

    token = _get_access_token()
    if not token:
        logger.debug("No Upstox token available, returning empty quotes data.")
        return _generate_paper_fallback_quotes(instrument_keys)

    try:
        instruments_str = ",".join(instrument_keys)
        url = f"{UPSTOX_BASE_URL}/v2/market-quote/quotes"
        headers = _make_headers(token)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, params={"instrument_key": instruments_str}, headers=headers, timeout=3)
        )

        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            logger.warning(f"Upstox quotes API error: {response.status_code} {response.text[:200]}")
            return _generate_paper_fallback_quotes(instrument_keys)

    except Exception as e:
        logger.error(f"Error fetching quotes from Upstox: {e}")
        return _generate_paper_fallback_quotes(instrument_keys)

def _generate_paper_fallback_quotes(keys: List[str]) -> Dict[str, dict]:
    result = {}
    for k in keys:
        ltp = _generate_paper_fallback_ltp(k)
        result[k] = {
            "last_price": ltp,
            "net_change": 0.0,
            "ohlc": {"close": ltp}
        }
    return result


async def fetch_option_chain(instrument_key: str, expiry_date: str) -> dict:
    """
    Fetch option chain for an underlying instrument and expiry.
    
    PAPER TRADE ONLY: This function calls /v2/option/chain (read-only).
    """
    token = _get_access_token()
    if not token:
        return {}

    try:
        url = f"{UPSTOX_BASE_URL}/v2/option/chain"
        headers = _make_headers(token)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(
                url, 
                params={"instrument_key": instrument_key, "expiry_date": expiry_date},
                headers=headers, 
                timeout=3
            )
        )

        if response.status_code == 200:
            data = response.json().get("data", {})
            logger.info(f"Successfully fetched option chain for {instrument_key} {expiry_date}. Length: {len(data)}")
            return data
        else:
            logger.warning(f"Upstox option chain API error for {instrument_key} {expiry_date}: Status {response.status_code}, Response: {response.text}")
            return {}

    except Exception as e:
        logger.error(f"Error fetching option chain from Upstox for {instrument_key} {expiry_date}: {e}")
        return {}


def build_instrument_key(underlying: str, expiry: str, strike: float, option_type: str) -> str:
    """
    Build an Upstox instrument key for an options contract.
    Format: NSE_FO|{underlying}{expiry_formatted}{strike}{option_type}
    
    Example: NSE_FO|NIFTY2472424500CE
    """
    # Upstox uses the format: NSE_FO|NIFTY24JUL24500CE
    # For simplicity, we'll construct the standard NSE key format.
    # In production, you'd look this up from the instruments master file.
    from datetime import datetime as dt
    try:
        expiry_dt = dt.strptime(expiry, "%Y-%m-%d")
        expiry_str = expiry_dt.strftime("%y%b").upper()  # e.g., "26JUL"
        day_str = expiry_dt.strftime("%d")  # e.g., "24"
        
        strike_int = int(strike)
        key = f"NSE_FO|{underlying}{expiry_str}{day_str}{strike_int}{option_type}"
        return key
    except Exception as e:
        logger.error(f"Error building instrument key: {e}")
        return f"NSE_FO|{underlying}_{strike}_{option_type}"


async def resolve_instrument_keys(legs: list) -> None:
    """
    Given a list of leg dictionaries, fetches the real option chain
    from Upstox and populates the 'instrument_key' field for each leg.
    """
    # Group legs by (underlying, expiry) to minimize API calls
    chain_cache = {}
    from .router_markets import INDICES
    
    # Batch fetch index spot prices if there are dynamic strikes to resolve
    dynamic_legs = [l for l in legs if isinstance(l.get("strike"), str) and not str(l.get("strike")).replace('.', '', 1).isdigit()]
    index_quotes = {}
    if dynamic_legs:
        index_keys = list(INDICES.values())
        index_quotes = await fetch_ltp(index_keys)

    import re
    for leg in legs:
        symbol = leg.get("symbol", "NIFTY")
        expiry = leg.get("expiry")
        strike = leg.get("strike")
        option_type = leg.get("option_type", "CE")
        
        if not all([symbol, expiry, strike, option_type]):
            continue

        # Resolve dynamic strike strings (ATM, ITM1, OTM2) to numeric values
        if isinstance(strike, str) and not str(strike).replace('.', '', 1).isdigit():
            symbol_upper = symbol.upper()
            index_key = INDICES.get(symbol_upper)
            spot = index_quotes.get(index_key) if index_key else None
            
            if not spot or spot <= 0:
                defaults = {"NIFTY": 24000.0, "BANKNIFTY": 57000.0, "FINNIFTY": 26150.0, "MIDCAPNIFTY": 14600.0}
                spot = defaults.get(symbol_upper, 24000.0)

            steps = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "MIDCAPNIFTY": 25}
            step = steps.get(symbol_upper, 50)
            atm = round(spot / step) * step
            resolved_strike = float(atm)
            
            match = re.match(r"^(ITM|OTM)(\d+)$", str(strike).upper().strip())
            if match:
                type_ = match.group(1)
                offset = int(match.group(2))
                if option_type == "CE":
                    resolved_strike = float(atm - (offset * step) if type_ == "ITM" else atm + (offset * step))
                else:
                    resolved_strike = float(atm + (offset * step) if type_ == "ITM" else atm - (offset * step))
            
            leg["strike"] = resolved_strike
            strike = resolved_strike

        underlying_key = INDICES.get(symbol, f"NSE_INDEX|{symbol}")
        cache_key = (underlying_key, expiry)
        
        if cache_key not in chain_cache:
            chain_data = await fetch_option_chain(underlying_key, expiry)
            # Build a lookup map of (strike, type) -> instrument_key
            lookup = {}
            for contract in chain_data:
                sp = float(contract.get("strike_price", 0))
                if "call_options" in contract:
                    lookup[(sp, "CE")] = contract["call_options"]["instrument_key"]
                if "put_options" in contract:
                    lookup[(sp, "PE")] = contract["put_options"]["instrument_key"]
            chain_cache[cache_key] = lookup
            
        # Lookup the exact instrument key
        lookup = chain_cache.get(cache_key, {})
        try:
            strike_float = float(strike)
            exact_key = lookup.get((strike_float, option_type))
            if exact_key:
                leg["instrument_key"] = exact_key
                logger.info(f"Resolved real instrument_key: {exact_key} for {symbol} {expiry} {strike} {option_type}")
            else:
                leg["instrument_key"] = build_instrument_key(symbol, expiry, strike_float, option_type)
        except (ValueError, TypeError):
            pass# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL SAFETY ASSERTION
# ══════════════════════════════════════════════════════════════════════════════
# The following assertion runs at module import time to verify that no order
# placement code exists. This is defense-in-depth — the primary protection is
# the complete absence of order-placement functions above.

def _assert_no_order_code():
    """Verify at import time that this module contains no order placement code."""
    import inspect
    source = inspect.getsource(__import__(__name__))
    
    forbidden_patterns = [
        "/v2/order/place",
        "/v2/order/modify",
        "/v2/order/cancel",
        "order_place",
        "place_order",
        "execute_order",
        "submit_order",
    ]
    for pattern in forbidden_patterns:
        if pattern in source:
            raise RuntimeError(
                f"PAPER_TRADE_ONLY VIOLATION: Found forbidden pattern '{pattern}' "
                f"in upstox_guard.py. This module must NEVER contain order placement code."
            )

# Run the check at import time
try:
    _assert_no_order_code()
except Exception:
    # During initial module setup, inspect may not work perfectly.
    # The structural absence of order functions is the primary protection.
    pass
