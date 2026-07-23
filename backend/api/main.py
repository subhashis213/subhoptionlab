"""
FastAPI Application — Options Backtester API.

Endpoints:
  POST /api/strategies          — Save a strategy config
  GET  /api/strategies          — List all strategies
  GET  /api/strategies/{id}     — Get a specific strategy
  DELETE /api/strategies/{id}   — Delete a strategy

  POST /api/backtest/run        — Run a backtest (async background task)
  GET  /api/backtest/{run_id}/status   — Check backtest status
  GET  /api/backtest/{run_id}/results  — Get backtest results

  GET  /api/instruments/expiries — Available expiry dates
  GET  /api/instruments/strikes  — Available strikes for an expiry
  GET  /api/instruments/data-range — Available data date range

  POST /api/data/download       — Download bhavcopy data for a date range
"""

import asyncio
import json
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PARQUET_DIR, RAW_DIR, SYMBOLS, DATA_DIR
from engine.schemas import StrategyConfig, BacktestRequest
from engine.backtest import run_backtest
from metrics.calculator import compute_metrics
from data.queries import (
    get_available_expiries,
    get_available_trade_dates,
    get_available_strikes,
    resolve_atm_strike,
    get_underlying_price,
)
from data.parquet_store import get_parquet_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Options Backtester API",
    description="StockMock-style options strategy backtesting tool for Indian indices",
    version="1.0.0",
)

# CORS — allow frontend dev server and all Vercel subdomains
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*|https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Ensure real bhavcopy CSVs and historical data are ready, then background-download Upstox minute data. Also connect to Mongo for live trading and paper trading."""
    import threading
    from live.db import connect_to_mongo
    from live.feed import feed_manager
    from live.runner import runner_service
    await connect_to_mongo()
    feed_manager.start()
    runner_service.start()

    # ── Paper Trading Platform Init ────────────────────────────────────────────
    from live.db import db as mongo_db
    from papertrade.db import init_papertrade_collections
    from papertrade.monitor import monitor_service
    from papertrade.websocket_manager import ws_manager

    await init_papertrade_collections(mongo_db)
    monitor_service.set_ws_manager(ws_manager)
    monitor_service.start()
    logger.info("Paper trading platform initialized (monitor + WebSocket manager).")

    try:
        # Step 1: Parse real raw bhavcopy CSVs into Parquet (exact NSE prices) — fast
        from config import RAW_DIR
        if RAW_DIR.exists() and any(RAW_DIR.glob("*.csv")):
            logger.info("Step 1/2: Parsing real raw_bhavcopies CSVs from %s...", RAW_DIR)
            from data.parser import parse_all_bhavcopies
            from data.parquet_store import write_options_parquet, write_underlying_parquet
            options_df, futures_df = parse_all_bhavcopies(RAW_DIR)
            if not options_df.is_empty():
                write_options_parquet(options_df)
            if not futures_df.is_empty():
                write_underlying_parquet(futures_df)
            logger.info("Step 1/2 complete: Real bhavcopies parsed into Parquet store.")

        # Step 2: Fill in any missing historical dates with synthetic data — fast
        from data.queries import get_available_trade_dates
        dates = get_available_trade_dates("BANKNIFTY")
        if not dates or len(dates) < 50:
            logger.info("Step 2/2: Running historical data auto-population for missing dates...")
            from scripts.populate_history import main as populate_main
            populate_main()
            logger.info("Step 2/2 complete: Historical data populated.")

    except Exception as e:
        logger.error("Failed to auto-populate data on startup: %s", e)

    # Step 3 (background): Auto-sync missing daily NSE bhavcopies & Upstox 1-minute candle data up to today
    try:
        from data.auto_sync import start_auto_sync_background
        start_auto_sync_background()
        logger.info("Server ready. Market data auto-sync started in background...")
    except Exception as e:
        logger.warning("Background market data auto-sync failed to start: %s", e)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    from live.db import close_mongo_connection
    from live.feed import feed_manager
    from live.runner import runner_service
    from papertrade.monitor import monitor_service
    
    monitor_service.stop()
    runner_service.stop()
    feed_manager.stop()
    await close_mongo_connection()


# ── Storage (`JSON Persistent Store`) ─────────────────────────────────────────
STRATEGIES_FILE = DATA_DIR / "saved_strategies.json"
_strategies: dict[str, dict] = {}
if STRATEGIES_FILE.exists():
    try:
        with open(STRATEGIES_FILE, "r", encoding="utf-8") as f:
            _strategies = json.load(f)
    except Exception as e:
        logger.error("Failed to load saved_strategies.json: %s", e)

def _persist_strategies():
    try:
        with open(STRATEGIES_FILE, "w", encoding="utf-8") as f:
            json.dump(_strategies, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to persist saved_strategies.json: %s", e)

_backtest_runs: dict[str, dict] = {}


# ── Request/Response Models ────────────────────────────────────────────────────

class SaveStrategyRequest(BaseModel):
    name: str
    config: StrategyConfig


class SaveStrategyResponse(BaseModel):
    id: str
    name: str
    created_at: str


class RunBacktestRequest(BaseModel):
    strategy_config: StrategyConfig
    date_from: date
    date_to: date
    strategy_id: Optional[str] = None


class RunBacktestResponse(BaseModel):
    run_id: str
    status: str


class DownloadDataRequest(BaseModel):
    from_date: date
    to_date: date
    delay: float = 1.5


# ── Strategy Endpoints ─────────────────────────────────────────────────────────

@app.post("/api/strategies", response_model=SaveStrategyResponse)
async def save_strategy(req: SaveStrategyRequest):
    """Save a strategy configuration."""
    strategy_id = str(uuid.uuid4())[:8]
    _strategies[strategy_id] = {
        "id": strategy_id,
        "name": req.name,
        "config": req.config.model_dump(),
        "created_at": datetime.now().isoformat(),
    }
    _persist_strategies()
    return SaveStrategyResponse(
        id=strategy_id,
        name=req.name,
        created_at=_strategies[strategy_id]["created_at"],
    )


@app.get("/api/strategies")
async def list_strategies():
    """List all saved strategies."""
    return list(_strategies.values())


@app.get("/api/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get a specific strategy by ID."""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _strategies[strategy_id]


@app.delete("/api/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """Delete a strategy."""
    if strategy_id not in _strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    del _strategies[strategy_id]
    _persist_strategies()
    return {"message": "Strategy deleted"}


# ── Backtest Endpoints ─────────────────────────────────────────────────────────

def _run_backtest_task(run_id: str, config: StrategyConfig, date_from: date, date_to: date):
    """Background task to run a backtest."""
    try:
        _backtest_runs[run_id]["status"] = "running"

        result = run_backtest(config, date_from, date_to)

        # Compute metrics
        metrics = compute_metrics(result.daily_results)
        result.metrics = metrics

        _backtest_runs[run_id]["status"] = "completed"
        _backtest_runs[run_id]["result"] = {
            "strategy": config.model_dump(),
            "date_from": str(date_from),
            "date_to": str(date_to),
            "total_trading_days": result.total_trading_days,
            "metrics": metrics,
            "daily_results": [d.model_dump() for d in result.daily_results],
        }
    except Exception as e:
        logger.error("Backtest failed for run %s: %s", run_id, e)
        _backtest_runs[run_id]["status"] = "failed"
        _backtest_runs[run_id]["error"] = str(e)


@app.post("/api/backtest/run", response_model=RunBacktestResponse)
async def start_backtest(req: RunBacktestRequest, background_tasks: BackgroundTasks):
    """Start a backtest as a background task."""
    run_id = str(uuid.uuid4())[:8]

    _backtest_runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "strategy": req.strategy_config.model_dump(),
        "date_from": str(req.date_from),
        "date_to": str(req.date_to),
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        _run_backtest_task, run_id,
        req.strategy_config, req.date_from, req.date_to,
    )

    return RunBacktestResponse(run_id=run_id, status="queued")


@app.get("/api/backtest/{run_id}/status")
async def get_backtest_status(run_id: str):
    """Check the status of a backtest run."""
    if run_id not in _backtest_runs:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    run = _backtest_runs[run_id]
    return {
        "run_id": run_id,
        "status": run["status"],
        "error": run.get("error"),
    }


@app.get("/api/backtest/{run_id}/results")
async def get_backtest_results(run_id: str):
    """Get the results of a completed backtest."""
    if run_id not in _backtest_runs:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    run = _backtest_runs[run_id]
    if run["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Backtest not completed. Current status: {run['status']}",
        )
    return run["result"]


@app.get("/api/backtest/runs")
async def list_backtest_runs():
    """List all backtest runs."""
    return [
        {
            "run_id": r["run_id"],
            "status": r["status"],
            "date_from": r["date_from"],
            "date_to": r["date_to"],
            "created_at": r["created_at"],
        }
        for r in _backtest_runs.values()
    ]


# ── Instrument Endpoints ──────────────────────────────────────────────────────

@app.get("/api/instruments/expiries")
async def get_expiries(
    symbol: str = Query(..., description="Index symbol (BANKNIFTY, NIFTY, FINNIFTY)"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
):
    """Get available expiry dates for a symbol."""
    expiries = get_available_expiries(symbol.upper(), from_date, to_date)
    return {"symbol": symbol, "expiries": [str(e) for e in expiries]}


@app.get("/api/instruments/strikes")
async def get_strikes(
    symbol: str = Query(...),
    expiry: date = Query(...),
    trade_date: date = Query(...),
    option_type: Optional[str] = None,
):
    """Get available strikes for a symbol/expiry/date."""
    strikes = get_available_strikes(
        symbol.upper(), expiry, trade_date, option_type
    )
    return {"symbol": symbol, "expiry": str(expiry), "strikes": strikes}


@app.get("/api/instruments/data-range")
async def get_data_range(
    symbol: str = Query(...),
):
    """Get the available date range for a symbol's data."""
    trade_dates = get_available_trade_dates(symbol.upper())
    if not trade_dates:
        return {"symbol": symbol, "from_date": None, "to_date": None, "total_days": 0}
    return {
        "symbol": symbol,
        "from_date": str(trade_dates[0]),
        "to_date": str(trade_dates[-1]),
        "total_days": len(trade_dates),
    }


@app.get("/api/instruments/atm")
async def get_atm(
    symbol: str = Query(...),
    trade_date: date = Query(...),
):
    """Get ATM strike for a symbol on a date."""
    price = get_underlying_price(symbol.upper(), trade_date)
    if price is None:
        raise HTTPException(status_code=404, detail="No underlying price data")
    atm = resolve_atm_strike(symbol.upper(), price)
    return {"symbol": symbol, "date": str(trade_date), "underlying_price": price, "atm_strike": atm}


# ── Data Management ────────────────────────────────────────────────────────────

@app.get("/api/data/stats")
async def data_stats():
    """Get Parquet data store statistics."""
    return get_parquet_stats()


@app.post("/api/data/download")
async def download_data(req: DownloadDataRequest, background_tasks: BackgroundTasks):
    """Download bhavcopy data for a date range (background task)."""
    run_id = str(uuid.uuid4())[:8]

    def _download_task():
        from data.downloader import download_date_range
        from data.parquet_store import ingest_bhavcopies
        try:
            _backtest_runs[f"dl-{run_id}"] = {"status": "downloading", "run_id": f"dl-{run_id}"}
            download_date_range(req.from_date, req.to_date, delay_seconds=req.delay)
            _backtest_runs[f"dl-{run_id}"]["status"] = "ingesting"
            ingest_bhavcopies(RAW_DIR)
            _backtest_runs[f"dl-{run_id}"]["status"] = "completed"
        except Exception as e:
            _backtest_runs[f"dl-{run_id}"] = {"status": "failed", "error": str(e), "run_id": f"dl-{run_id}"}

    background_tasks.add_task(_download_task)
    return {"run_id": f"dl-{run_id}", "status": "started"}


# ── Health Check ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    stats = get_parquet_stats()
    return {
        "status": "healthy",
        "symbols": SYMBOLS,
        "data_stats": stats,
    }


# ── Live Trading Routers (existing backtester) ─────────────────────────────────
from live.broker_router import router as broker_router
from live.live_router import router as live_router
app.include_router(broker_router)
app.include_router(live_router)

# ── Paper Trading Platform Routers ─────────────────────────────────────────────
from papertrade.router_auth import router as pt_auth_router
from papertrade.router_admin import router as pt_admin_router
from papertrade.router_strategy import router as pt_strategy_router
from papertrade.router_wallet import router as pt_wallet_router
from papertrade.router_history import router as pt_history_router
from papertrade.router_markets import router as pt_markets_router
app.include_router(pt_auth_router)
app.include_router(pt_admin_router)
app.include_router(pt_strategy_router)
app.include_router(pt_wallet_router)
app.include_router(pt_history_router)
app.include_router(pt_markets_router)


# ── Paper Trading WebSocket Endpoint ───────────────────────────────────────────
from fastapi import WebSocket as WS, WebSocketDisconnect as WSDisconnect
import json as _json

@app.websocket("/ws/pt/{token}")
async def papertrade_websocket(websocket: WS, token: str):
    """WebSocket endpoint for real-time paper trading updates.
    Connect with JWT token in the URL path."""
    from papertrade.auth import decode_token
    from papertrade.websocket_manager import ws_manager
    from papertrade import db as pt_db

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        role = payload.get("role", "user")

        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user = await pt_db.users_collection.find_one({"_id": user_id})
        if not user or user.get("status") == "blocked":
            await websocket.close(code=4003, reason="User not found or blocked")
            return

        is_admin = role == "admin"
        await ws_manager.connect(user_id, websocket, is_admin=is_admin)

        try:
            while True:
                data = await websocket.receive_text()
                # Client can send pings or subscription requests
                try:
                    msg = _json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception:
                    pass
        except WSDisconnect:
            ws_manager.disconnect(user_id, websocket)

    except Exception as e:
        try:
            await websocket.close(code=4001, reason=str(e))
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
