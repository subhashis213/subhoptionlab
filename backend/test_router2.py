import asyncio
from papertrade.upstox_guard import fetch_ltp
from papertrade.router_markets import INDICES

async def main():
    keys = list(INDICES.values())
    live_quotes = await fetch_ltp(keys)
    print("Keys requested:", keys)
    print("Live quotes:", live_quotes)

asyncio.run(main())
