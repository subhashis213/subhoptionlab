import asyncio
from papertrade.upstox_guard import fetch_ltp

async def check():
    ltp = await fetch_ltp(["NSE_FO|63947", "NSE_FO|63948"])
    print("Live Ticks from Upstox API right now:", ltp)

asyncio.run(check())
