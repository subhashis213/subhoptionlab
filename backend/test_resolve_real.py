import asyncio
from papertrade.upstox_guard import fetch_option_chain, fetch_ltp, resolve_instrument_keys

async def check():
    legs = [
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": 24000.0, "option_type": "CE"},
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": 24000.0, "option_type": "PE"},
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": 24200.0, "option_type": "CE"},
        {"symbol": "NIFTY", "expiry": "2026-07-28", "strike": 24200.0, "option_type": "PE"},
    ]
    await resolve_instrument_keys(legs)
    print("Resolved legs:", legs)
    
    keys = [l["instrument_key"] for l in legs]
    ltps = await fetch_ltp(keys)
    print("Live LTPs for resolved keys:", ltps)

asyncio.run(check())
