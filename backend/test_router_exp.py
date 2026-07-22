import asyncio
from dotenv import load_dotenv
load_dotenv()
from papertrade.router_markets import get_valid_expiries

async def main():
    expiries = await get_valid_expiries("BANKNIFTY")
    print("BANKNIFTY expiries:", expiries)

asyncio.run(main())
