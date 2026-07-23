import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb+srv://subhashis213:o2a3O4D162YdJ1S7@cluster0.kavok.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") + "&tlsAllowInvalidCertificates=true")
    db = client.backtester
    user = await db.users_collection.find_one({"email": "subhashis213@gmail.com"})
    print("User ID:", user["_id"])
    
    # Check strategies collection
    strategies = await db.strategies_collection.find({"user_id": user["_id"]}).to_list(10)
    print("Recent strategies:", len(strategies))
    for s in strategies[-3:]:
        print(s.get("name"), s.get("status"))

if __name__ == "__main__":
    asyncio.run(main())
