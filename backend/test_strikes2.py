import asyncio
from papertrade.upstox_guard import fetch_option_chain

async def check():
    chain_data = await fetch_option_chain("NSE_INDEX|Nifty Bank", "current_month")
    for contract in chain_data:
        sp = float(contract.get("strike_price", 0))
        if abs(sp - 57800) < 500:
            print(f"Found strike: {sp}, keys: {list(contract.keys())}")
            if "call_options" in contract:
                print(f"  Call instrument: {contract['call_options'].get('instrument_key')}")
            if "put_options" in contract:
                print(f"  Put instrument: {contract['put_options'].get('instrument_key')}")

asyncio.run(check())
