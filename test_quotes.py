import sys
sys.path.append('backend')
import asyncio
from papertrade.upstox_guard import fetch_quotes, fetch_ltp, fetch_option_chain
async def main():
    quotes = await fetch_quotes(["NSE_INDEX|Nifty Bank"])
    print("QUOTES:", quotes)
    ltp = await fetch_ltp(["NSE_INDEX|Nifty Bank"])
    print("LTP:", ltp)
    oc = await fetch_option_chain("NSE_INDEX|Nifty Bank", "2026-07-28")
    print("OC:", len(oc))
asyncio.run(main())
