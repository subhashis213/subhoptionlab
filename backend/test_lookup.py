import asyncio
from papertrade.upstox_guard import fetch_option_chain

async def check():
    chain_data = await fetch_option_chain("NSE_INDEX|Nifty Bank", "current_month")
    lookup = {}
    for contract in chain_data:
        sp = float(contract.get("strike_price", 0))
        if "call_options" in contract:
            lookup[(sp, "CE")] = contract["call_options"]["instrument_key"]
            
    print("Is (57800.0, 'CE') in lookup?", (57800.0, "CE") in lookup)
    if (57800.0, "CE") in lookup:
        print("Value:", lookup[(57800.0, "CE")])
    else:
        print("Available strikes near 57800:", [k for k in lookup.keys() if abs(k[0] - 57800) < 500])

asyncio.run(check())
