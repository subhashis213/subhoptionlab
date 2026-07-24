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
        "encrypted_api_key": _encrypt(api_key) if api_key else (existing.get("encrypted_api_key") if existing else None),
        "encrypted_api_secret": existing.get("encrypted_api_secret") if existing else None,
        "connected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
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


@router.post("/save-keys")
async def save_app_keys(
    api_key: str = Body(...),
    api_secret: str = Body(...),
    redirect_uri: str = Body("https://subhoptionlab.vercel.app/broker/callback"),
    broker: str = Body("upstox")
):
    """Save user's Upstox Developer App API Key & Secret."""
    user_id = "default_user"
    existing = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    
    doc = {
        "_id": existing["_id"] if existing else str(uuid.uuid4()),
        "user_id": user_id,
        "broker": broker,
        "encrypted_api_key": _encrypt(api_key),
        "encrypted_api_secret": _encrypt(api_secret),
        "redirect_uri": redirect_uri,
        "encrypted_access_token": existing.get("encrypted_access_token") if existing else None,
        "connected_at": existing.get("connected_at") if existing else None,
        "is_active": existing.get("is_active", False) if existing else False,
    }
    
    await db.broker_credentials_collection.replace_one(
        {"user_id": user_id, "broker": broker},
        doc,
        upsert=True
    )
    return {"status": "success", "message": "App credentials saved successfully"}


@router.get("/login-url")
async def get_login_url(
    redirect_uri: str = "https://subhoptionlab.vercel.app/broker/callback",
    broker: str = "upstox"
):
    """Generate the 1-Click OAuth login URL for Upstox."""
    user_id = "default_user"
    cred = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    
    api_key = None
    if cred and cred.get("encrypted_api_key"):
        api_key = _decrypt(cred["encrypted_api_key"])
        
    if not api_key:
        api_key = os.getenv("UPSTOX_API_KEY")
        
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key not configured. Please save your API Key first.")
        
    url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"
    return {"status": "success", "login_url": url, "api_key": api_key}


@router.post("/callback")
async def handle_oauth_callback(
    code: str = Body(...),
    redirect_uri: str = Body("https://subhoptionlab.vercel.app/broker/callback"),
    broker: str = Body("upstox")
):
    """Exchange authorization code for an access token with Upstox."""
    import requests
    user_id = "default_user"
    cred = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    
    api_key = _decrypt(cred.get("encrypted_api_key")) if cred and cred.get("encrypted_api_key") else os.getenv("UPSTOX_API_KEY")
    api_secret = _decrypt(cred.get("encrypted_api_secret")) if cred and cred.get("encrypted_api_secret") else os.getenv("UPSTOX_API_SECRET")
    
    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="Missing API Key or API Secret. Please save your App Keys first.")
        
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        "code": code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        resp = requests.post(token_url, data=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("access_token"):
            access_token = data["access_token"]
            
            # Store in DB & Environment
            os.environ["UPSTOX_ACCESS_TOKEN"] = access_token
            doc = {
                "_id": cred["_id"] if cred else str(uuid.uuid4()),
                "user_id": user_id,
                "broker": broker,
                "encrypted_access_token": _encrypt(access_token),
                "encrypted_api_key": _encrypt(api_key),
                "encrypted_api_secret": _encrypt(api_secret),
                "connected_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "is_active": True,
            }
            await db.broker_credentials_collection.replace_one(
                {"user_id": user_id, "broker": broker},
                doc,
                upsert=True
            )
            return {
                "status": "success",
                "message": "Upstox account connected successfully!",
                "user_name": data.get("user_name"),
                "user_id": data.get("user_id")
            }
        else:
            error_msg = data.get("errors", [{}])[0].get("message") if data.get("errors") else data.get("message", "Failed to obtain access token")
            raise HTTPException(status_code=400, detail=f"Upstox Error: {error_msg}")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to communicate with Upstox: {str(e)}")


@router.get("/status")
async def broker_status(broker: str = "upstox"):
    """Check if the user has an active broker connection & configured keys."""
    user_id = "default_user"
    
    existing = await db.broker_credentials_collection.find_one({"user_id": user_id, "broker": broker})
    has_keys = False
    api_key_masked = None
    if existing:
        api_key = _decrypt(existing.get("encrypted_api_key"))
        api_secret = _decrypt(existing.get("encrypted_api_secret"))
        if api_key and api_secret:
            has_keys = True
            api_key_masked = api_key[:4] + "****" + api_key[-2:] if len(api_key) > 6 else "****"
            
    is_connected = False
    connected_at = None
    if existing and existing.get("is_active") and existing.get("encrypted_access_token"):
        is_connected = True
        connected_at = existing.get("connected_at")
    elif os.getenv("UPSTOX_ACCESS_TOKEN"):
        is_connected = True
        connected_at = "Environment Variable"
        
    return {
        "connected": is_connected,
        "broker": broker,
        "connected_at": connected_at,
        "has_keys": has_keys,
        "api_key_masked": api_key_masked,
        "is_active": is_connected,
    }


@router.post("/disconnect")
async def disconnect_broker(broker: str = Body("upstox")):
    """Disconnect the broker by setting is_active to False."""
    user_id = "default_user"
    
    await db.broker_credentials_collection.update_one(
        {"user_id": user_id, "broker": broker},
        {"$set": {"is_active": False}}
    )
    if "UPSTOX_ACCESS_TOKEN" in os.environ:
        del os.environ["UPSTOX_ACCESS_TOKEN"]
        
    return {"status": "success", "message": f"{broker} disconnected successfully"}

