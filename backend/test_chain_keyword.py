import asyncio
from papertrade.upstox_guard import fetch_option_chain
from dotenv import load_dotenv
import json

load_dotenv()

async def test():
    res = await fetch_option_chain("NSE_INDEX|Nifty Bank", "current_week")
    print(len(res))
    if len(res) > 0:
        print(json.dumps(res[0]))

asyncio.run(test())
