import sys
sys.path.append('backend')
import asyncio
from papertrade.upstox_guard import fetch_quotes, fetch_ltp
async def main():
    quotes = await fetch_quotes(["NSE_INDEX|Nifty Bank"])
    print("QUOTES:", quotes)
    ltp = await fetch_ltp(["NSE_INDEX|Nifty Bank"])
    print("LTP:", ltp)
asyncio.run(main())
