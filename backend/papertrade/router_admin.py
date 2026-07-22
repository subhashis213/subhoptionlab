"""
Admin API endpoints — user management, chip transactions, global overview.
All endpoints require admin role JWT.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from papertrade import db
from papertrade.auth import require_admin
from papertrade.models import (
    UserResponse,
    UserStatusUpdate,
    ChipTransactionCreate,
    ChipTransactionInDB,
    AdminOverview,
)

router = APIRouter(prefix="/api/pt/admin", tags=["admin"])


# ── User Management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """List all users with optional search/filter."""
    query = {"role": "user"}  # Admin only sees user accounts

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    if status_filter and status_filter in ("active", "blocked"):
        query["status"] = status_filter

    cursor = db.users_collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
    users = await cursor.to_list(length=limit)

    total = await db.users_collection.count_documents(query)

    # Attach wallet balance to each user
    result = []
    for u in users:
        wallet = await db.wallets_collection.find_one({"user_id": u["_id"]})
        result.append({
            "_id": u["_id"],
            "name": u["name"],
            "email": u["email"],
            "phone": u.get("phone", ""),
            "role": u["role"],
            "status": u["status"],
            "created_at": u["created_at"],
            "wallet_balance": wallet["virtual_chips_balance"] if wallet else 0.0,
        })

    return {"users": result, "total": total, "skip": skip, "limit": limit}


@router.get("/users/{user_id}")
async def get_user_detail(user_id: str, admin: dict = Depends(require_admin)):
    """Get detailed info for a specific user — profile, wallet, active strategies."""
    user = await db.users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    wallet = await db.wallets_collection.find_one({"user_id": user_id})

    # Active strategies
    strats_cursor = db.strategies_collection.find(
        {"user_id": user_id, "status": "active"}
    )
    active_strategies = await strats_cursor.to_list(length=100)

    # Recent chip transactions
    tx_cursor = (
        db.chip_transactions_collection
        .find({"user_id": user_id})
        .sort("timestamp", -1)
        .limit(50)
    )
    transactions = await tx_cursor.to_list(length=50)

    return {
        "user": {
            "_id": user["_id"],
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "role": user["role"],
            "status": user["status"],
            "created_at": user["created_at"],
        },
        "wallet": wallet if wallet else {"virtual_chips_balance": 0, "total_added": 0, "total_removed": 0},
        "active_strategies": active_strategies,
        "transactions": transactions,
    }


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    req: UserStatusUpdate,
    admin: dict = Depends(require_admin),
):
    """Toggle user active/blocked status."""
    user = await db.users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    if user.get("role") == "admin":
        raise HTTPException(400, "Cannot change admin status")

    await db.users_collection.update_one(
        {"_id": user_id},
        {"$set": {"status": req.status}},
    )

    return {"status": "success", "user_id": user_id, "new_status": req.status}


# ── Chip Transactions ──────────────────────────────────────────────────────────

@router.post("/users/{user_id}/chips/add")
async def add_chips(
    user_id: str,
    req: ChipTransactionCreate,
    admin: dict = Depends(require_admin),
):
    """Add virtual chips to a user's wallet. Logged as audit trail."""
    user = await db.users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    # Update wallet
    result = await db.wallets_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "virtual_chips_balance": req.amount,
                "total_added": req.amount,
            },
            "$set": {"last_updated": datetime.utcnow()},
        },
    )

    if result.matched_count == 0:
        # Wallet doesn't exist yet — create it
        await db.wallets_collection.insert_one({
            "user_id": user_id,
            "virtual_chips_balance": req.amount,
            "total_added": req.amount,
            "total_removed": 0.0,
            "last_updated": datetime.utcnow(),
        })

    # Log transaction
    import uuid
    tx_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "admin_id": admin["_id"],
        "type": "add",
        "amount": req.amount,
        "reason": req.reason,
        "timestamp": datetime.utcnow(),
    }
    await db.chip_transactions_collection.insert_one(tx_doc)

    # Fetch updated wallet
    wallet = await db.wallets_collection.find_one({"user_id": user_id})

    return {
        "status": "success",
        "type": "add",
        "amount": req.amount,
        "new_balance": wallet["virtual_chips_balance"],
        "transaction_id": tx_doc["_id"],
    }


@router.post("/users/{user_id}/chips/remove")
async def remove_chips(
    user_id: str,
    req: ChipTransactionCreate,
    admin: dict = Depends(require_admin),
):
    """Remove virtual chips from a user's wallet. Logged as audit trail."""
    user = await db.users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(404, "User not found")

    wallet = await db.wallets_collection.find_one({"user_id": user_id})
    if not wallet:
        raise HTTPException(400, "User has no wallet")

    if wallet["virtual_chips_balance"] < req.amount:
        raise HTTPException(
            400,
            f"Insufficient balance. Current: {wallet['virtual_chips_balance']}, "
            f"Requested removal: {req.amount}",
        )

    # Update wallet
    await db.wallets_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "virtual_chips_balance": -req.amount,
                "total_removed": req.amount,
            },
            "$set": {"last_updated": datetime.utcnow()},
        },
    )

    # Log transaction
    import uuid
    tx_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "admin_id": admin["_id"],
        "type": "remove",
        "amount": req.amount,
        "reason": req.reason,
        "timestamp": datetime.utcnow(),
    }
    await db.chip_transactions_collection.insert_one(tx_doc)

    wallet = await db.wallets_collection.find_one({"user_id": user_id})

    return {
        "status": "success",
        "type": "remove",
        "amount": req.amount,
        "new_balance": wallet["virtual_chips_balance"],
        "transaction_id": tx_doc["_id"],
    }


# ── Global Overview ────────────────────────────────────────────────────────────

@router.get("/overview", response_model=AdminOverview)
async def get_overview(admin: dict = Depends(require_admin)):
    """Global platform stats for admin dashboard."""
    total_users = await db.users_collection.count_documents({"role": "user"})
    active_users = await db.users_collection.count_documents({"role": "user", "status": "active"})
    blocked_users = await db.users_collection.count_documents({"role": "user", "status": "blocked"})

    # Total capital distributed
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$total_added"}}}
    ]
    agg = await db.wallets_collection.aggregate(pipeline).to_list(length=1)
    total_capital = agg[0]["total"] if agg else 0.0

    # Total capital in play (sum of all wallet balances)
    pipeline2 = [
        {"$group": {"_id": None, "total": {"$sum": "$virtual_chips_balance"}}}
    ]
    agg2 = await db.wallets_collection.aggregate(pipeline2).to_list(length=1)
    capital_in_play = agg2[0]["total"] if agg2 else 0.0

    active_strategies = await db.strategies_collection.count_documents({"status": "active"})

    return AdminOverview(
        total_users=total_users,
        active_users=active_users,
        blocked_users=blocked_users,
        total_capital_distributed=total_capital,
        total_capital_in_play=capital_in_play,
        active_strategies_count=active_strategies,
    )


@router.get("/strategies")
async def get_all_strategies(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
):
    """List all strategies across all users (admin global view)."""
    query = {}
    if status_filter:
        query["status"] = status_filter

    cursor = (
        db.strategies_collection
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    strategies = await cursor.to_list(length=limit)

    # Attach user info and leg count
    result = []
    for s in strategies:
        user = await db.users_collection.find_one({"_id": s["user_id"]})
        leg_count = await db.strategy_legs_collection.count_documents({"strategy_id": s["_id"]})
        open_legs = await db.strategy_legs_collection.count_documents(
            {"strategy_id": s["_id"], "current_status": "open"}
        )
        result.append({
            **s,
            "user_name": user["name"] if user else "Unknown",
            "user_email": user["email"] if user else "",
            "leg_count": leg_count,
            "open_legs": open_legs,
        })

    total = await db.strategies_collection.count_documents(query)

    return {"strategies": result, "total": total, "skip": skip, "limit": limit}
