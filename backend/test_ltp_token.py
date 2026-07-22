import asyncio
from papertrade.upstox_guard import fetch_ltp

async def check():
    ltp = await fetch_ltp(["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"])
    print("LTP:", ltp)

asyncio.run(check())
