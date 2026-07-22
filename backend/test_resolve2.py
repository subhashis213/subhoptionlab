import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import resolve_instrument_keys
import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv

load_dotenv()

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    legs = await db.pt_strategy_legs.find({"strategy_id": "5bad1dd0-34c7-4192-8517-fe6016b7ab63"}).to_list(10)
    print("Found legs:", len(legs))
    print("Before:", [l.get("instrument_key") for l in legs])
    await resolve_instrument_keys(legs)
    print("After:", [l.get("instrument_key") for l in legs])

asyncio.run(check())
