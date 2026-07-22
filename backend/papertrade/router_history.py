"""
Trade history & reports API — closed strategies, stats, win rate.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from papertrade import db
from papertrade.auth import require_user

router = APIRouter(prefix="/api/pt/history", tags=["history"])


@router.get("/trades")
async def get_trade_history(
    strategy_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_user),
):
    """Get user's trade history with optional strategy filter."""
    query = {"user_id": user["_id"]}
    if strategy_id:
        query["strategy_id"] = strategy_id

    cursor = (
        db.trade_history_collection
        .find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    trades = await cursor.to_list(length=limit)
    total = await db.trade_history_collection.count_documents(query)

    from datetime import datetime
    for t in trades:
        ts = t.get("timestamp")
        if isinstance(ts, datetime):
            t["timestamp"] = ts.isoformat() + "Z"

    return {"trades": trades, "total": total}


@router.get("/stats")
async def get_stats(user: dict = Depends(require_user)):
    """
    Get trading statistics:
    - Total strategies, win rate
    - Total P&L, best/worst trade
    - Average P&L per strategy
    """
    user_id = user["_id"]

    # Get all closed strategies
    closed_cursor = db.strategies_collection.find({
        "user_id": user_id,
        "status": "closed",
    })
    closed_strategies = await closed_cursor.to_list(length=500)

    # Get all trades
    trades_cursor = db.trade_history_collection.find({"user_id": user_id})
    all_trades = await trades_cursor.to_list(length=5000)

    if not all_trades:
        return {
            "total_strategies": len(closed_strategies),
            "active_strategies": await db.strategies_collection.count_documents(
                {"user_id": user_id, "status": "active"}
            ),
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
        }

    # Calculate strategy-level P&L
    strategy_pnls = {}
    for trade in all_trades:
        sid = trade["strategy_id"]
        if sid not in strategy_pnls:
            strategy_pnls[sid] = 0.0
        strategy_pnls[sid] += trade.get("pnl", 0.0)

    total_pnl = sum(strategy_pnls.values())
    winning = sum(1 for v in strategy_pnls.values() if v > 0)
    total_closed = len(strategy_pnls)
    win_rate = (winning / total_closed * 100) if total_closed > 0 else 0.0

    trade_pnls = [t.get("pnl", 0) for t in all_trades]

    return {
        "total_strategies": len(closed_strategies),
        "active_strategies": await db.strategies_collection.count_documents(
            {"user_id": user_id, "status": "active"}
        ),
        "total_trades": len(all_trades),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(total_pnl / total_closed, 2) if total_closed > 0 else 0.0,
        "best_trade": round(max(trade_pnls), 2) if trade_pnls else 0.0,
        "worst_trade": round(min(trade_pnls), 2) if trade_pnls else 0.0,
        "winning_trades": sum(1 for p in trade_pnls if p > 0),
        "losing_trades": sum(1 for p in trade_pnls if p < 0),
    }


@router.get("/closed-strategies")
async def get_closed_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_user),
):
    """List closed strategies with P&L summary."""
    from config import LOT_SIZES

    cursor = (
        db.strategies_collection
        .find({"user_id": user["_id"], "status": "closed"})
        .sort("closed_at", -1)
        .skip(skip)
        .limit(limit)
    )
    strategies = await cursor.to_list(length=limit)
    total = await db.strategies_collection.count_documents(
        {"user_id": user["_id"], "status": "closed"}
    )

    result = []
    for s in strategies:
        legs_cursor = db.strategy_legs_collection.find({"strategy_id": s["_id"]})
        legs = await legs_cursor.to_list(length=20)

        strategy_pnl = 0.0
        for leg in legs:
            entry = leg.get("entry_price", 0)
            exit_p = leg.get("exit_price", entry)
            lot_size = LOT_SIZES.get(leg.get("symbol", "NIFTY"), 50)
            total_qty = leg.get("qty", 1) * lot_size

            if leg["side"] == "BUY":
                strategy_pnl += (exit_p - entry) * total_qty
            else:
                strategy_pnl += (entry - exit_p) * total_qty

        exit_reasons = list(set(l.get("exit_reason", "unknown") for l in legs if l.get("exit_reason")))

        result.append({
            **s,
            "total_pnl": round(strategy_pnl, 2),
            "total_legs": len(legs),
            "exit_reasons": exit_reasons,
            "legs": legs,
        })

    return {"strategies": result, "total": total}

@router.get("/daily-stats")
async def get_daily_stats(user: dict = Depends(require_user)):
    """Aggregate PnL by day."""
    from collections import defaultdict
    
    trades_cursor = db.trade_history_collection.find({"user_id": user["_id"]})
    all_trades = await trades_cursor.to_list(length=5000)

    daily_pnl = defaultdict(float)
    daily_trades = defaultdict(int)

    for trade in all_trades:
        ts = trade.get("timestamp")
        if not ts:
            continue
        day_str = ts.strftime("%Y-%m-%d")
        daily_pnl[day_str] += trade.get("pnl", 0.0)
        daily_trades[day_str] += 1

    result = []
    for day, pnl in daily_pnl.items():
        result.append({
            "date": day,
            "pnl": round(pnl, 2),
            "trades": daily_trades[day]
        })

    # Sort descending by date
    result.sort(key=lambda x: x["date"], reverse=True)
    return {"daily_stats": result}
