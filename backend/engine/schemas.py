"""
Pydantic models for strategy configuration and backtest results.

These models define the JSON schema for strategy configs (what the frontend
sends) and the output format of backtest results.
"""

from datetime import date, time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExpiryMode(str, Enum):
    SAME_DAY = "same_day"
    NEXT_DAY = "next_day"


class TradeMode(str, Enum):
    INTRADAY = "intraday"
    POSITIONAL = "positional"


class ExitReason(str, Enum):
    TIME_EXIT = "time_exit"
    LEG_SL_HIT = "leg_sl_hit"
    LEG_TARGET_HIT = "leg_target_hit"
    STRATEGY_SL_HIT = "strategy_sl_hit"
    STRATEGY_TARGET_HIT = "strategy_target_hit"
    PROTECT_PROFIT_EXIT = "protect_profit_exit"


# ── Strategy Config Models ─────────────────────────────────────────────────────

class LegConfig(BaseModel):
    """Configuration for a single leg of a multi-leg options strategy."""

    option_type: OptionType = Field(description="CE or PE")
    action: Action = Field(description="BUY or SELL")
    strike_selection: str = Field(
        default="ATM",
        description=(
            "Strike selection relative to ATM. "
            "Examples: 'ATM', 'ITM-1', 'ITM-2', 'OTM-1', 'OTM-3'"
        ),
    )
    lots: int = Field(default=1, ge=1, description="Number of lots")
    sl_percent: Optional[float] = Field(
        default=None, ge=0, description="Stop loss as % of entry premium"
    )
    target_percent: Optional[float] = Field(
        default=None, ge=0, description="Target profit as % of entry premium"
    )
    trailing_sl: Optional[float] = Field(
        default=None, ge=0,
        description="Trailing stop loss as % — adjusts SL as premium moves favorably",
    )
    move_sl_to_cost: bool = Field(
        default=False,
        description="After target moves in favor, move SL to entry price (breakeven)",
    )


class ProtectProfitsConfig(BaseModel):
    """
    Ratchet/lock-in mechanism for protecting accumulated profits.

    When combined P&L exceeds lock_profit_at, the strategy exits if
    P&L falls back below lock_exit_at.
    """
    lock_profit_at: float = Field(
        description="Lock profits when combined P&L reaches this value (in points)"
    )
    lock_exit_at: float = Field(
        description="Exit if P&L drops to this value after locking (in points)"
    )


class StrategyConfig(BaseModel):
    """Full strategy configuration — defines what to trade and how."""

    symbol: str = Field(
        description="Index symbol: BANKNIFTY, NIFTY, or FINNIFTY"
    )
    legs: list[LegConfig] = Field(
        min_length=1,
        description="List of option legs (at least one required)",
    )
    entry_time: str = Field(
        default="09:20:00",
        description="Entry time in HH:MM:SS format",
    )
    exit_time: str = Field(
        default="15:15:00",
        description="Exit time in HH:MM:SS format",
    )
    expiry_mode: ExpiryMode = Field(
        default=ExpiryMode.SAME_DAY,
        description="'same_day' = current weekly expiry, 'next_day' = next week's",
    )
    use_futures_for_atm: bool = Field(
        default=False,
        description="Use futures price (instead of spot) for ATM calculation",
    )
    strategy_sl_percent: Optional[float] = Field(
        default=None, ge=0,
        description="Strategy-level stop loss as % of estimated margin",
    )
    strategy_target_percent: Optional[float] = Field(
        default=None, ge=0,
        description="Strategy-level target profit as % of estimated margin",
    )
    strategy_sl_points: Optional[float] = Field(
        default=None,
        description="Strategy-level stop loss in absolute points",
    )
    strategy_target_points: Optional[float] = Field(
        default=None,
        description="Strategy-level target profit in absolute points",
    )
    protect_profits: Optional[ProtectProfitsConfig] = Field(
        default=None,
        description="Profit protection / ratchet config",
    )
    mode: TradeMode = Field(
        default=TradeMode.INTRADAY,
        description="'intraday' = exit same day, 'positional' = carry overnight",
    )


class BacktestRequest(BaseModel):
    """Request to run a backtest — strategy config + date range."""

    strategy: StrategyConfig
    date_from: date
    date_to: date


# ── Result Models ──────────────────────────────────────────────────────────────

class LegResult(BaseModel):
    """Result for a single leg on a single day."""

    option_type: str
    action: str
    strike: float
    entry_price: float
    exit_price: float
    pnl_points: float
    lots: int
    lot_size: int
    pnl_value: float  # pnl_points * lots * lot_size
    exit_reason: str


class DailyResult(BaseModel):
    """Result for a single trading day."""

    trade_date: date
    expiry_date: date
    atm_strike: int
    underlying_price: float
    legs: list[LegResult]
    total_pnl_points: float
    total_pnl_value: float
    exit_reason: str  # The primary exit reason for the day


class BacktestResult(BaseModel):
    """Complete backtest output."""

    strategy: StrategyConfig
    date_from: date
    date_to: date
    daily_results: list[DailyResult]
    total_trading_days: int
    metrics: Optional[dict] = None  # Filled by Phase 3 metrics module
