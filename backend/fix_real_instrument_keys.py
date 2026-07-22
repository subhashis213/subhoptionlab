import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from papertrade.upstox_guard import resolve_instrument_keys, fetch_ltp
import logging

logging.basicConfig(level=logging.INFO)

async def update_all_open_strategies():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    
    # Get all open legs across all strategies
    legs = await db.pt_strategy_legs.find({"current_status": "open"}).to_list(100)
    print(f"Found {len(legs)} open legs to resolve real Upstox instrument keys for...")
    
    if legs:
        # Resolve exact Upstox numerical instrument keys from live option chain
        await resolve_instrument_keys(legs)
        
        keys = [l["instrument_key"] for l in legs if l.get("instrument_key")]
        print("Resolved real keys:", keys)
        
        # Fetch live LTPs for all resolved keys directly from Upstox API
        live_ltps = await fetch_ltp(keys)
        print("Live Upstox LTPs:", live_ltps)
        
        for leg in legs:
            key = leg.get("instrument_key")
            live_price = live_ltps.get(key)
            
            update_fields = {"instrument_key": key}
            if live_price is not None:
                update_fields["current_ltp"] = live_price
                # If entry_price was previously the dummy 145.25 or 0.0, set real entry_price
                if leg.get("entry_price") in (0.0, 145.25):
                    update_fields["entry_price"] = live_price
                    
            await db.pt_strategy_legs.update_one(
                {"_id": leg["_id"]},
                {"$set": update_fields}
            )
            print(f"Updated leg {leg['_id']} ({leg['symbol']} {leg['strike']} {leg['option_type']}) -> key: {key}, entry: {update_fields.get('entry_price', leg.get('entry_price'))}, ltp: {live_price}")

asyncio.run(update_all_open_strategies())
