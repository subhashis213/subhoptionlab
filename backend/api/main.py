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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
