"""
Upstox 1-Minute Historical Options Downloader.

Downloads exact 1-minute historical candlestick data (`open, high, low, close`)
from Upstox API v2 (`api.upstox.com/v2/historical-candle/intraday/`) for any option contract
and stores it in ultra-fast local Parquet files for exact minute-by-minute backtesting.
"""

import os
import sys
import json
import gzip
import io
import csv
import urllib.request
import urllib.parse
import ssl
from datetime import date, datetime, time, timedelta
from pathlib import Path

import polars as pl

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from config import PARQUET_DIR

env_file = backend_dir / ".env"

def get_env_var(key, default=""):
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    return line.strip().split("=", 1)[1].strip()
    return os.environ.get(key, default)

ACCESS_TOKEN = get_env_var("UPSTOX_ACCESS_TOKEN", "")
SSL_CTX = ssl._create_unverified_context()

def get_instrument_master() -> list[dict]:
    """Download and parse Upstox NSE_FO instrument master."""
    url = "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
    print("Downloading Upstox complete instrument master...")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "*/*",
        }
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
        compressed = io.BytesIO(resp.read())
        decompressed = gzip.GzipFile(fileobj=compressed)
        content = decompressed.read().decode("utf-8")
        reader = csv.DictReader(content.splitlines())
        return [r for r in reader if r.get("exchange") == "NSE_FO"]

def lookup_instrument_key(master: list[dict], symbol: str, strike: float, option_type: str, target_date_str: str = "") -> str | None:
    """Find Upstox instrument_key for a specific option contract closest to target_date."""
    target_strike = str(int(strike)) if strike.is_integer() else str(strike)
    matches = []
    for row in master:
        ts = row.get("tradingsymbol", "")
        if symbol in ts and target_strike in ts and ts.endswith(option_type):
            matches.append(row)
            
    if not matches:
        return None
        
    if target_date_str:
        # Filter for expiries >= target_date and pick the earliest/closest expiry
        valid = [r for r in matches if r.get("expiry", "") >= target_date_str]
        if valid:
            valid.sort(key=lambda x: x.get("expiry", ""))
            return valid[0].get("instrument_key")
            
    matches.sort(key=lambda x: x.get("expiry", ""))
    return matches[0].get("instrument_key")

def fetch_upstox_intraday_candles(instrument_key: str, from_date: str, to_date: str) -> list[list]:
    """Call Upstox Historical Intraday Candle API (`1minute`)."""
    if not ACCESS_TOKEN:
        raise ValueError("UPSTOX_ACCESS_TOKEN not set in backend/.env. Run scripts/upstox_auth_helper.py first!")
        
    encoded_key = urllib.parse.quote(instrument_key, safe="")
    # Upstox v2 historical API requires to_date to be > target_date to include target_date
    adjusted_to = (date.fromisoformat(to_date) + timedelta(days=2)).isoformat()
    url = f"https://api.upstox.com/v2/historical-candle/{encoded_key}/1minute/{adjusted_to}/{from_date}"
    
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
    )
    
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        d = data.get("data", {})
        if isinstance(d, dict):
            return d.get("candles", [])
        return d if isinstance(d, list) else []

def save_minute_parquet(symbol: str, trade_date: date, strike: float, option_type: str, candles: list[list]):
    """Convert candles to Polars DataFrame and save as Parquet."""
    if not candles:
        return
        
    rows = []
    for c in candles:
        ts_str = c[0]
        # Only keep candles belonging to trade_date
        if trade_date.isoformat() not in ts_str:
            continue
        rows.append({
            "timestamp": ts_str,
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": int(c[5]),
            "oi": int(c[6]) if len(c) > 6 else 0,
            "symbol": symbol,
            "trade_date": trade_date,
            "strike": float(strike),
            "option_type": option_type,
        })
        
    if not rows:
        return
        
    df = pl.DataFrame(rows)
    # Sort chronologically by timestamp
    df = df.sort("timestamp")
    
    out_dir = PARQUET_DIR / "minute" / symbol
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{trade_date.isoformat()}_{int(strike)}_{option_type}.parquet"
    df.write_parquet(out_path)
    print(f"✅ Saved {len(rows)} 1-minute bars (`09:15 to 15:30`) to {out_path.name}")

def main():
    print("=" * 60)
    print("UPSTOX 1-MINUTE HISTORICAL CANDLE DOWNLOADER")
    print("=" * 60)
    
    if not ACCESS_TOKEN:
        print("\n❌ UPSTOX_ACCESS_TOKEN is missing in backend/.env!")
        return
        
    master = get_instrument_master()
    print(f"Loaded {len(master)} option instruments from Upstox.")
    
    symbol = "BANKNIFTY"
    strike = 58500.0
    target_date = "2026-07-17"
    
    for option_type in ["CE", "PE"]:
        print(f"\nLooking up Upstox instrument key for {symbol} {int(strike)} {option_type}...")
        key = lookup_instrument_key(master, symbol, strike, option_type, target_date)
        if not key:
            print(f"Could not find instrument key for {symbol} {strike} {option_type}")
            continue
            
        print(f"Found instrument key: {key}")
        print(f"Downloading 1-minute candles for {target_date}...")
        
        try:
            candles = fetch_upstox_intraday_candles(key, target_date, target_date)
            print(f"Received {len(candles)} total candles from API!")
            for c in candles:
                if "09:56:00" in c[0] and target_date in c[0]:
                    print(f"  Exact Upstox 09:56 AM Candle ({option_type}) -> Open: ₹{c[1]}, High: ₹{c[2]}, Low: ₹{c[3]}, Close: ₹{c[4]}")
            save_minute_parquet(symbol, date.fromisoformat(target_date), strike, option_type, candles)
        except Exception as e:
            print(f"❌ Error downloading candles for {option_type}: {e}")

if __name__ == "__main__":
    main()
