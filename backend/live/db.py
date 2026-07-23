"""
MongoDB connection initialization for Live/Paper trading.
"""
import os
import re
import logging
import urllib.parse
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def format_mongo_uri(uri: str) -> str:
    """Safely format and URL-encode username and password in MongoDB URI according to RFC 3986."""
    if not uri or not uri.startswith("mongodb"):
        return uri
        
    if "<password>" in uri or "<db_password>" in uri or ("<" in uri and ">" in uri):
        raise ValueError(
            "\n" + "="*80 + "\n"
            "CRITICAL ERROR: Your MONGODB_URI contains placeholder text like <password> or <db_password>.\n"
            "You must replace this with your ACTUAL MongoDB Atlas password in the Render dashboard.\n"
            "Do not include the < and > brackets in your password.\n"
            + "="*80 + "\n"
        )
        
    pattern = r'^(mongodb(?:\+srv)?://)([^:]+):(.+)@([^/@\?]+(?::\d+)?(?:/.*)?)$'
    match = re.match(pattern, uri)
    if match:
        prefix, user, password, rest = match.groups()
        unquoted_user = urllib.parse.unquote(user)
        unquoted_password = urllib.parse.unquote(password)
        quoted_user = urllib.parse.quote_plus(unquoted_user)
        quoted_password = urllib.parse.quote_plus(unquoted_password)
        return f"{prefix}{quoted_user}:{quoted_password}@{rest}"
    return uri

RAW_MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_URI = format_mongo_uri(RAW_MONGODB_URI)
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

    logger.info(f"Connecting to MongoDB (DB: {DB_NAME})...")
    try:
        client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        await db.command("ping")
        logger.info("Successfully authenticated & connected to MongoDB Atlas!")
    except Exception as e:
        logger.error("MongoDB Atlas Authentication/Connection Failed: %s", e)
        raise e
    
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
