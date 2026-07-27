import asyncio
from backend.papertrade.upstox_guard import fetch_option_chain

async def main():
    chain = await fetch_option_chain("NSE_INDEX|Nifty Bank", "2026-07-28")
    if chain:
        print("Chain length:", len(chain))
        print("First item:", chain[0])
    else:
        print("Chain empty")

asyncio.run(main())
