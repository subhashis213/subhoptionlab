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


@router.get("/top-stocks")
async def get_top_stocks():
    """Fetch Top Gainers and Losers across all F&O Stocks."""
    from data.stock_registry import TOP_FO_STOCKS
    
    # Build safe keys — skip symbols with special chars like M&M that break URL params
    safe_stocks = [s for s in TOP_FO_STOCKS if "&" not in s["symbol"] and " " not in s["symbol"]]
    keys = [f"NSE_EQ|{s['symbol']}" for s in safe_stocks]
    
    results = []
    try:
        # Batch in chunks of 50 to avoid URL length issues
        batch_size = 50
        live_quotes = {}
        for i in range(0, len(keys), batch_size):
            batch_quotes = await fetch_quotes(keys[i:i+batch_size])
            live_quotes.update(batch_quotes)
        
        for stock in safe_stocks:
            key = f"NSE_EQ|{stock['symbol']}"
            # Try pipe and colon variants
            quote = live_quotes.get(key) or live_quotes.get(key.replace("|", ":"))
            if not quote:
                continue
            ltp = float(quote.get("last_price", 0.0))
            if ltp <= 0:
                continue
            change = float(quote.get("net_change", 0.0))
            change_percent = 0.0
            ohlc = quote.get("ohlc", {})
            close_price = float(ohlc.get("close", 0.0))
            if close_price > 0:
                change_percent = round((change / close_price) * 100, 2)
                
            results.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "ltp": ltp,
                "change": round(change, 2),
                "change_percent": change_percent,
                "instrument_key": key
            })
            
        results.sort(key=lambda x: x["change_percent"], reverse=True)
        return {
            "gainers": results[:10],
            "losers": list(reversed(results))[:10]
        }
    except Exception as e:
        logger.error(f"Error fetching top stocks: {e}")
        return {"gainers": [], "losers": []}


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
            
    from datetime import date, timedelta
    def get_fallback_expiries():
        today = date.today()
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days_ahead)
        next_month = next_thursday + timedelta(days=28)
        return [next_thursday.strftime("%Y-%m-%d"), next_month.strftime("%Y-%m-%d")]

    from .upstox_guard import _get_access_token
    token = await _get_access_token()
    if not token:
        return get_fallback_expiries()

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
        
    return get_fallback_expiries()
