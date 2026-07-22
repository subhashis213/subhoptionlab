"""
Broker connection API endpoints.
Handles storing, retrieving, and validating Upstox API credentials.
"""

from datetime import datetime
import uuid
import os
import base64
from fastapi import APIRouter, HTTPException, Body
from live.models import BrokerCredentials
from live import db

router = APIRouter(prefix="/api/broker", tags=["broker"])


# In a real production app, we would use a strong symmetric encryption key (like Fernet).
# For this demonstration, we'll implement a simple base64 "encryption" placeholder,
# but ideally this would use an environment variable like ENCRYPTION_KEY.
def _encrypt(raw: str) -> str:
    if not raw:
        return raw
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def _decrypt(encrypted: str) -> str:
    if not encrypted:
        return encrypted
    try:
        return base64.b64decode(encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        return encrypted


@router.post("/connect")
async def connect_broker(
    broker: str = Body("upstox"),
    access_token: str = Body(...),
    api_key: str = Body(None),
):
    """
    Encrypt and store broker credentials. 
    In paper trading, these might not be required, but for live trading they are essential.
    """
    user_id = "default_user"
    
    # Check if exists
    existing = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    
    doc = {
        "_id": existing["_id"] if existing else str(uuid.uuid4()),
        "user_id": user_id,
        "broker": broker,
        "encrypted_access_token": _encrypt(access_token),
        "encrypted_api_key": _encrypt(api_key) if api_key else None,
        "connected_at": datetime.utcnow(),
        "is_active": True,
    }
    
    await db.broker_credentials_collection.replace_one(
        {"user_id": user_id, "broker": broker},
        doc,
        upsert=True
    )
    
    # Optionally update the .env or global memory for local execution
    os.environ["UPSTOX_ACCESS_TOKEN"] = access_token
    
    return {"status": "success", "message": f"{broker} connected successfully"}


@router.get("/status")
async def broker_status(broker: str = "upstox"):
    """Check if the user has an active broker connection."""
    user_id = "default_user"
    
    existing = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    
    if not existing or not existing.get("is_active"):
        # Fallback to checking os.environ for local test mode
        if broker == "upstox" and os.getenv("UPSTOX_ACCESS_TOKEN"):
            return {
                "connected": True,
                "broker": broker,
                "connected_at": "Environment Variable",
                "is_active": True
            }
            
        return {"connected": False, "broker": broker}
        
    return {
        "connected": True,
        "broker": broker,
        "connected_at": existing.get("connected_at"),
        "is_active": existing.get("is_active"),
    }


@router.post("/disconnect")
async def disconnect_broker(broker: str = Body("upstox")):
    """Disconnect the broker by setting is_active to False."""
    user_id = "default_user"
    
    await db.broker_credentials_collection.update_one(
        {"user_id": user_id, "broker": broker},
        {"$set": {"is_active": False}}
    )
    
    return {"status": "success", "message": f"{broker} disconnected successfully"}
