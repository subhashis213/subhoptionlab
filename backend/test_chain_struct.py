import asyncio
from papertrade.upstox_guard import fetch_option_chain

async def check():
    chain = await fetch_option_chain("NSE_INDEX|Nifty 50", "2026-07-28")
    print("Chain len:", len(chain))
    if chain:
        c = chain[0]
        print("Keys:", c.keys())
        print("Strike price:", c.get("strike_price"))
        if "call_options" in c:
            print("Call keys:", c["call_options"].keys())
            print("Call market_data:", c["call_options"].get("market_data"))
        # Check spot price or underlying price in response if available
        for k, v in c.items():
            if "spot" in k.lower() or "underlying" in k.lower() or "price" in k.lower():
                print(f"Key {k}: {v}")

asyncio.run(check())
