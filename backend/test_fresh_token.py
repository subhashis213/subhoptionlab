import asyncio
from papertrade.upstox_guard import fetch_ltp, fetch_option_chain

async def check():
    ltp = await fetch_ltp(["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"])
    print("Live Index Spot LTPs:", ltp)
    
    chain = await fetch_option_chain("NSE_INDEX|Nifty 50", "2026-07-28")
    print("Option Chain contracts count:", len(chain))
    if chain:
        c = chain[0]
        print("Sample contract strike:", c.get("strike_price"))
        if "call_options" in c:
            print("Call instrument_key:", c["call_options"].get("instrument_key"))
            print("Call market_data LTP:", c["call_options"].get("market_data", {}).get("ltp"))

asyncio.run(check())
