import asyncio
from papertrade.upstox_guard import fetch_option_chain
async def main():
    chain = await fetch_option_chain('NSE_INDEX|Nifty Bank', 'current_week')
    if chain:
        print(chain[0]['expiry'])
    else:
        print("None")
asyncio.run(main())
