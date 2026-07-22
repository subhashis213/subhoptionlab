import asyncio
from papertrade.upstox_guard import fetch_ltp
from papertrade.router_markets import INDICES

async def check():
    keys = list(INDICES.values())
    print("Request keys:", keys)
    quotes = await fetch_ltp(keys)
    print("Returned quotes:", quotes)
    
    for symbol, index_key in INDICES.items():
        spot = quotes.get(index_key)
        print(f"Symbol: {symbol}, index_key: {index_key}, spot_price: {spot}")

asyncio.run(check())
