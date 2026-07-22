"""
MongoDB connection initialization for Live/Paper trading.
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "option_backtester")

client: AsyncIOMotorClient = None
db = None

# Collection references
broker_credentials_collection = None
live_strategies_collection = None
live_orders_collection = None
live_positions_collection = None
wallet_collection = None


async def connect_to_mongo():
    """Connect to MongoDB and initialize collections."""
    global client, db
    global broker_credentials_collection
    global live_strategies_collection
    global live_orders_collection
    global live_positions_collection
    global wallet_collection

    logger.info(f"Connecting to MongoDB at {MONGODB_URI} (DB: {DB_NAME})...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    broker_credentials_collection = db["broker_credentials"]
    live_strategies_collection = db["live_strategies"]
    live_orders_collection = db["live_orders"]
    live_positions_collection = db["live_positions"]
    wallet_collection = db["wallets"]
    
    logger.info("Connected to MongoDB successfully.")


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")
