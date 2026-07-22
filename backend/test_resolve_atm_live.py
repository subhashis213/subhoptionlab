import asyncio
from papertrade.upstox_guard import resolve_instrument_keys, fetch_ltp

async def check():
    legs = [
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": "ATM", "option_type": "CE"},
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": "ATM", "option_type": "PE"},
        {"symbol": "BANKNIFTY", "expiry": "2026-07-28", "strike": "ATM", "option_type": "CE"},
    ]
    await resolve_instrument_keys(legs)
    print("Resolved dynamic ATM legs:", legs)
    
    keys = [l["instrument_key"] for l in legs]
    ltps = await fetch_ltp(keys)
    print("Live LTPs for resolved ATM keys:", ltps)

asyncio.run(check())
