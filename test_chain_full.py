import asyncio
from backend.papertrade.upstox_guard import fetch_option_chain
import json

async def main():
    chain = await fetch_option_chain("NSE_INDEX|Nifty Bank", "2026-07-28")
    if chain:
        print(json.dumps(chain[0], indent=2))
        
asyncio.run(main())
