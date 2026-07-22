import asyncio
from papertrade.upstox_guard import fetch_ltp
from dotenv import load_dotenv

load_dotenv()

async def test():
    res = await fetch_ltp(["NSE_INDEX|Nifty Bank", "NSE_FO|BANKNIFTY24JUL57800CE", "NSE_FO|BANKNIFTY2472457800CE", "NSE_FO|BANKNIFTY24JUL2457800CE"])
    print(res)

asyncio.run(test())
