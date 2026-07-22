import asyncio
from papertrade.upstox_guard import fetch_option_chain
from dotenv import load_dotenv

load_dotenv()

async def test():
    res = await fetch_option_chain("NSE_INDEX|Nifty Bank", "2024-07-24") # Try a recent date? We don't know the valid expiry date
    print(res)

asyncio.run(test())
