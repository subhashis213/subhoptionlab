import asyncio
from papertrade.upstox_guard import resolve_instrument_keys, fetch_option_chain
import logging
logging.basicConfig(level=logging.INFO)

async def check():
    legs = [
        {"symbol": "BANKNIFTY", "expiry": "current_month", "strike": 57800, "option_type": "CE", "instrument_key": "OLD_KEY"}
    ]
    await resolve_instrument_keys(legs)
    print("Final legs:", legs)

asyncio.run(check())
