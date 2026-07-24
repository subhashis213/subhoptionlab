"""
Markets API for Live Dashboards — Paper Trading Only.
Provides endpoints for fetching index spot prices and option chains.
"""

from fastapi import APIRouter, HTTPException, Depends
from papertrade.auth import require_user
from papertrade.upstox_guard import fetch_ltp, fetch_quotes, fetch_option_chain
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pt/markets", tags=["markets"])

# Major indices Upstox instrument keys
INDICES = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
    "MIDCAPNIFTY": "NSE_INDEX|NIFTY MID SELECT"
}

@router.get("/indices")
async def get_indices(user: dict = Depends(require_user)):
    """Fetch live spot prices for major indices."""
    keys = list(INDICES.values())
    try:
        live_quotes = await fetch_quotes(keys)
        
        result = []
        for name, key in INDICES.items():
            quote = live_quotes.get(key)
            
            if not quote:
                result.append({
                    "symbol": name,
                    "ltp": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0
                })
                continue

            ltp = float(quote.get("last_price", 0.0))
            change = float(quote.get("net_change", 0.0))
            change_percent = 0.0
            
            # Upstox returns net_change, but sometimes it doesn't return net_change_percent or we calculate it
            # Let's try to get it directly, or calculate from close price
            if "net_change" in quote:
                # Calculate percent if not provided directly
                ohlc = quote.get("ohlc", {})
                close_price = float(ohlc.get("close", 0.0))
                if close_price > 0:
                    change_percent = round((change / close_price) * 100, 2)

            result.append({
                "symbol": name,
                "ltp": ltp,
                "change": round(change, 2),
                "change_percent": change_percent
            })
            
        return result
    except Exception as e:
        logger.error(f"Error fetching indices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch indices")


@router.get("/option-chain")
async def get_option_chain(underlying: str, expiry: str, user: dict = Depends(require_user)):
    """
    Fetch option chain for a given underlying and expiry date.
    Returns realistic mock data if Upstox API fails.
    """
    try:
        instrument_key = INDICES.get(underlying, f"NSE_INDEX|{underlying}")
        
        # Check if stock
        if not instrument_key.startswith("NSE_INDEX"):
            from data.stock_registry import search_stocks
            stocks = search_stocks(underlying, 1)
            if stocks and stocks[0]["symbol"] == underlying.upper():
                instrument_key = f"NSE_EQ|{underlying}"

        upstox_chain = await fetch_option_chain(instrument_key, expiry)
        
        if upstox_chain:
            return upstox_chain
            
        # Return empty if we couldn't fetch real live data
        logger.warning(f"Could not fetch real option chain for {underlying} {expiry}. Returning empty.")
        return []

    except Exception as e:
        logger.error(f"Error fetching option chain: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch option chain")

@router.get("/stocks/search")
async def get_stocks_search(q: str = "", limit: int = 10):
    """Search F&O stocks with autocomplete."""
    from data.stock_registry import search_stocks
    return search_stocks(q, limit)

@router.get("/expiries")
async def get_valid_expiries(underlying: str):
    instrument_key = INDICES.get(underlying, f"NSE_INDEX|{underlying}")
    
    # Check if stock instead
    if not instrument_key.startswith("NSE_INDEX"):
        from data.stock_registry import search_stocks
        stocks = search_stocks(underlying, 1)
        if stocks and stocks[0]["symbol"] == underlying.upper():
            instrument_key = f"NSE_EQ|{underlying}" # Needs actual ISIN or FO key but we can try 
            
    from .upstox_guard import _get_access_token
    token = await _get_access_token()
    if not token:
        return ["2026-07-28", "2026-08-25"] # Fallback
    
    try:
        from .upstox_guard import fetch_option_chain
        expiries = set()
        keywords = ["current_month", "next_month"] if "NSE_EQ" in instrument_key else ["current_week", "next_week", "current_month"]
        for kw in keywords:
            chain_data = await fetch_option_chain(instrument_key, kw)
            if chain_data:
                # The first item has the expiry date for this keyword
                expiries.add(chain_data[0]["expiry"])
        
        if expiries:
            return sorted(list(expiries))
    except Exception as e:
        logger.error(f"Error fetching expiries from keywords: {e}")
        
    return ["2026-07-28", "2026-08-25"] # Fallback
