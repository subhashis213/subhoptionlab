import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def create():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.option_backtester
    user = await db.pt_users.find_one({})
    
    # Generate token (mock for local testing)
    import jwt
    from datetime import datetime, timedelta
    token = jwt.encode(
        {"user_id": user["_id"], "email": user["email"], "exp": datetime.utcnow() + timedelta(days=1)},
        os.getenv("JWT_SECRET", "supersecret"), algorithm="HS256"
    )
    
    url = "http://127.0.0.1:8000/api/pt/strategies"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "API Test",
        "underlying": "BANKNIFTY",
        "move_sl_to_cost": False,
        "legs": [
            {
                "symbol": "BANKNIFTY",
                "expiry": "2026-07-28",
                "strike": "58000",
                "option_type": "CE",
                "side": "SELL",
                "qty": 1,
                "order_type": "MARKET"
            }
        ]
    }
    res = requests.post(url, json=payload, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.json())
    
    if res.status_code == 200:
        s_id = res.json()["strategy_id"]
        legs = await db.pt_strategy_legs.find({"strategy_id": s_id}).to_list(10)
        print("Inserted leg keys:", [l["instrument_key"] for l in legs])

asyncio.run(create())
