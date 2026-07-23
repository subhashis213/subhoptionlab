"""
Authentication API endpoints — register, login, profile.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends

from papertrade import db
from papertrade.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from papertrade.models import UserCreate, UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/api/pt/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: UserCreate):
    """Register a new user. Role is always 'user' — admins are created via CLI."""
    if db.users_collection is None:
        from live.db import db as mongo_db
        from papertrade.db import init_papertrade_collections
        await init_papertrade_collections(mongo_db)

    try:
        # Check if email already exists
        existing = await db.users_collection.find_one({"email": req.email.lower().strip()})
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(err)}. Ensure 0.0.0.0/0 is whitelisted in MongoDB Atlas Network Access."
        )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    import uuid
    user_id = str(uuid.uuid4())

    user_doc = {
        "_id": user_id,
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "phone": req.phone.strip() if req.phone else "",
        "password_hash": hash_password(req.password),
        "role": "user",
        "status": "active",
        "created_at": datetime.utcnow(),
    }
    await db.users_collection.insert_one(user_doc)

    # Create empty wallet for the new user
    wallet_doc = {
        "user_id": user_id,
        "virtual_chips_balance": 0.0,
        "total_added": 0.0,
        "total_removed": 0.0,
        "last_updated": datetime.utcnow(),
    }
    await db.wallets_collection.insert_one(wallet_doc)

    # Generate JWT
    token = create_access_token(user_id, "user")

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            _id=user_id,
            name=user_doc["name"],
            email=user_doc["email"],
            phone=user_doc["phone"],
            role="user",
            status="active",
            created_at=user_doc["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin):
    """Authenticate user and return JWT."""
    if db.users_collection is None:
        from live.db import db as mongo_db
        from papertrade.db import init_papertrade_collections
        await init_papertrade_collections(mongo_db)

    try:
        user = await db.users_collection.find_one({"email": req.email.lower().strip()})
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(err)}. Ensure 0.0.0.0/0 is whitelisted in MongoDB Atlas Network Access."
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.get("status") == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked. Contact admin.",
        )

    token = create_access_token(user["_id"], user["role"])

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            _id=user["_id"],
            name=user["name"],
            email=user["email"],
            phone=user.get("phone", ""),
            role=user["role"],
            status=user["status"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return UserResponse(
        _id=user["_id"],
        name=user["name"],
        email=user["email"],
        phone=user.get("phone", ""),
        role=user["role"],
        status=user["status"],
        created_at=user["created_at"],
    )
