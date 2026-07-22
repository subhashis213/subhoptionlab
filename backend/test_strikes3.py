import asyncio
from papertrade.upstox_guard import fetch_option_chain

async def check():
    chain_data = await fetch_option_chain("NSE_INDEX|Nifty Bank", "current_month")
    if not chain_data:
        print("CHAIN DATA IS EMPTY")
    else:
        print("Got", len(chain_data), "items")
        for contract in chain_data:
            sp = float(contract.get("strike_price", 0))
            if sp == 57800.0:
                print("FOUND 57800!", contract)

asyncio.run(check())
