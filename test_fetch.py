import asyncio
from backend.papertrade.upstox_guard import fetch_quotes

async def main():
    quotes = await fetch_quotes(["NSE_INDEX|Nifty Bank"])
    print(quotes)

asyncio.run(main())
