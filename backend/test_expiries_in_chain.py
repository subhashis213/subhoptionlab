import asyncio
from papertrade.upstox_guard import fetch_option_chain

async def check():
    chain_data = await fetch_option_chain("NSE_INDEX|Nifty Bank", "current_month")
    expiries = set(d.get("expiry") for d in chain_data)
    print("Expiries in current_month:", expiries)

asyncio.run(check())
