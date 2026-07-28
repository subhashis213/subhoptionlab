"""
User wallet API — view wallet, transaction history.
Users CANNOT add their own chips — that's admin-only.
"""

from fastapi import APIRouter, Depends

from papertrade import db
from papertrade.auth import require_user
from papertrade.models import WalletResponse

router = APIRouter(prefix="/api/pt/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
async def get_wallet(user: dict = Depends(require_user)):
    """Get current user's wallet with balance and unrealized P&L."""
    user_id = user["_id"]

    wallet = await db.wallets_collection.find_one({"user_id": user_id})
    if not wallet:
        wallet = {
            "user_id": user_id,
            "virtual_chips_balance": 0.0,
            "total_added": 0.0,
            "total_removed": 0.0,
            "last_updated": None,
        }

    # Calculate unrealized P&L from open strategy legs
    active_strats_cursor = db.strategies_collection.find(
        {"user_id": user_id, "status": "active"}
    )
    active_strats = await active_strats_cursor.to_list(length=100)
    active_strat_ids = [s["_id"] for s in active_strats]

    unrealized_pnl = 0.0
    used_margin = 0.0
    if active_strats:
        from papertrade.router_strategy import calc_strategy_metrics
        for s in active_strats:
            legs_cursor = db.strategy_legs_collection.find({"strategy_id": s["_id"]})
            legs = await legs_cursor.to_list(length=50)
            strat_margin, _, strat_pnl = await calc_strategy_metrics(legs)
            used_margin += strat_margin
            unrealized_pnl += strat_pnl

    balance = wallet["virtual_chips_balance"]
    available_margin = max(0.0, balance - used_margin + unrealized_pnl) # Incorporate PnL in margin

    return WalletResponse(
        user_id=user_id,
        virtual_chips_balance=balance,
        total_added=wallet["total_added"],
        total_removed=wallet["total_removed"],
        unrealized_pnl=round(unrealized_pnl, 2),
        net_worth=round(balance + unrealized_pnl, 2),
        used_margin=round(used_margin, 2),
        available_margin=round(available_margin, 2),
        last_updated=wallet.get("last_updated"),
    )


@router.get("/transactions")
async def get_transactions(
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(require_user),
):
    """Get user's chip transaction history (admin add/remove + trade P&L)."""
    user_id = user["_id"]

    cursor = (
        db.chip_transactions_collection
        .find({"user_id": user_id})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    transactions = await cursor.to_list(length=limit)
    total = await db.chip_transactions_collection.count_documents({"user_id": user_id})

    return {"transactions": transactions, "total": total}
