import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import resolve_instrument_keys
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def fix_all():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    # Find all legs that have an instrument key containing 'JUL' or 'AUG' etc (bad format)
    # The bad format is NSE_FO|BANKNIFTY...
    # The good format is NSE_FO|61889
    legs = await db.pt_strategy_legs.find({
        "instrument_key": {"$regex": "^NSE_FO|[A-Z]{3,}"}
    }).to_list(None)
    
    # Filter to only bad ones (length > 20 usually means bad format)
    bad_legs = [l for l in legs if len(l.get("instrument_key", "")) > 15]
    print(f"Found {len(bad_legs)} bad legs to fix")
    
    if bad_legs:
        await resolve_instrument_keys(bad_legs)
        
        # Update them in DB
        updates = 0
        for leg in bad_legs:
            if len(leg["instrument_key"]) < 15: # It was successfully resolved
                await db.pt_strategy_legs.update_one(
                    {"_id": leg["_id"]},
                    {"$set": {"instrument_key": leg["instrument_key"]}}
                )
                updates += 1
        print(f"Fixed {updates} legs in DB")

asyncio.run(fix_all())
