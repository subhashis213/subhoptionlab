"""
JWT Authentication, password hashing, and role-based access control.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from papertrade import db

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("PT_JWT_SECRET", "paper-trade-secret-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

import hashlib
import hmac

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.warning(f"passlib hash failed, falling back to pbkdf2: {e}")
        salt = os.urandom(16).hex()
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return f"pbkdf2_sha256${salt}${derived}"

def verify_password(plain: str, hashed: str) -> bool:
    try:
        if hashed and hashed.startswith("pbkdf2_sha256$"):
            _, salt, derived = hashed.split("$")
            check = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
            return hmac.compare_digest(check, derived)
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        logger.error(f"verify_password failed: {e}")
        return False


# ── JWT Tokens ─────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str) -> str:
    """Create a JWT token with user_id and role in payload."""
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ── FastAPI Dependencies ───────────────────────────────────────────────────────

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency: extract and validate JWT, return user document from DB.
    Raises 401 if token is invalid or user not found/blocked.
    """
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if user.get("status") == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked. Contact admin.")

    return user


async def require_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency: require the current user to have admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def require_user(
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency: require the current user to have user role."""
    if user.get("role") != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User access required",
        )
    return user
