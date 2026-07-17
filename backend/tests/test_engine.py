"""
Tests for the engine and metrics modules (Phase 2 & Phase 3).
"""

import sys
from datetime import date
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.strike_resolver import resolve_strike
from engine.expiry_resolver import get_weekly_expiry_day
from engine.schemas import StrategyConfig, LegConfig, OptionType, Action, DailyResult, LegResult
from metrics.calculator import compute_metrics


class TestStrikeResolver:
    def test_atm_strike(self):
        assert resolve_strike(48000, "ATM", "CE", "BANKNIFTY") == 48000
        assert resolve_strike(24000, "ATM", "PE", "NIFTY") == 24000

    def test_ce_itm_otm(self):
        # CE ITM = lower strike, OTM = higher strike
        assert resolve_strike(48000, "ITM-1", "CE", "BANKNIFTY") == 47900
        assert resolve_strike(48000, "OTM-2", "CE", "BANKNIFTY") == 48200
        assert resolve_strike(24000, "ITM-2", "CE", "NIFTY") == 23900
        assert resolve_strike(24000, "OTM-1", "CE", "NIFTY") == 24050

    def test_pe_itm_otm(self):
        # PE ITM = higher strike, OTM = lower strike
        assert resolve_strike(48000, "ITM-1", "PE", "BANKNIFTY") == 48100
        assert resolve_strike(48000, "OTM-2", "PE", "BANKNIFTY") == 47800
        assert resolve_strike(24000, "ITM-2", "PE", "NIFTY") == 24100
        assert resolve_strike(24000, "OTM-1", "PE", "NIFTY") == 23950

    def test_invalid_selection_raises(self):
        with pytest.raises(ValueError, match="Invalid strike selection"):
            resolve_strike(48000, "INVALID-1", "CE", "BANKNIFTY")


class TestExpiryResolver:
    def test_banknifty_expiry_days(self):
        # Wednesday before Apr 2024
        assert get_weekly_expiry_day("BANKNIFTY", date(2023, 10, 10)) == 2
        # Tuesday on/after Apr 2024
        assert get_weekly_expiry_day("BANKNIFTY", date(2024, 5, 10)) == 1

    def test_nifty_expiry_days(self):
        assert get_weekly_expiry_day("NIFTY", date(2024, 5, 10)) == 3

    def test_finnifty_expiry_days(self):
        assert get_weekly_expiry_day("FINNIFTY", date(2024, 5, 10)) == 1


class TestMetricsCalculator:
    def test_compute_metrics_empty(self):
        m = compute_metrics([])
        assert m["total_trading_days"] == 0
        assert m["overall_profit"] == 0

    def test_compute_metrics_with_data(self):
        days = [
            DailyResult(
                trade_date=date(2024, 7, 15),
                expiry_date=date(2024, 7, 18),
                atm_strike=52400,
                underlying_price=52450,
                legs=[],
                total_pnl_points=100.0,
                total_pnl_value=1500.0,
                exit_reason="time_exit",
            ),
            DailyResult(
                trade_date=date(2024, 7, 16),
                expiry_date=date(2024, 7, 18),
                atm_strike=52400,
                underlying_price=52450,
                legs=[],
                total_pnl_points=-40.0,
                total_pnl_value=-600.0,
                exit_reason="leg_sl_hit",
            ),
            DailyResult(
                trade_date=date(2024, 7, 18),
                expiry_date=date(2024, 7, 18),
                atm_strike=52400,
                underlying_price=52450,
                legs=[],
                total_pnl_points=60.0,
                total_pnl_value=900.0,
                exit_reason="time_exit",
            ),
        ]
        m = compute_metrics(days)
        assert m["total_trading_days"] == 3
        assert m["overall_profit"] == 1800.0
        assert m["win_days"] == 2
        assert m["loss_days"] == 1
        assert m["win_pct"] == round(2 / 3 * 100, 2)
        assert m["max_drawdown"] == 600.0
        assert m["sl_hit_count"] == 1
        assert m["time_exit_count"] == 2
        assert len(m["equity_curve"]) == 3
        assert m["equity_curve"][-1]["cumulative"] == 1800.0


class TestBacktestSimulation:
    def test_run_backtest_with_stored_data(self):
        from engine.backtest import run_backtest
        cfg = StrategyConfig(
            symbol="BANKNIFTY",
            legs=[
                LegConfig(option_type=OptionType.CE, action=Action.SELL, strike_selection="ATM", lots=1),
                LegConfig(option_type=OptionType.PE, action=Action.SELL, strike_selection="ATM", lots=1),
            ],
            entry_time="09:20:00",
            exit_time="15:15:00",
        )
        # Run on our already downloaded date range
        res = run_backtest(cfg, date(2024, 7, 15), date(2024, 7, 19))
        assert res.strategy.symbol == "BANKNIFTY"
        # We have 4 trading days in 2024-07-15 to 2024-07-19 (15, 16, 18, 19)
        assert res.total_trading_days <= 4
        # Verify legs got calculated if options data was matched
        for d in res.daily_results:
            assert len(d.legs) == 2
            assert d.trade_date in [date(2024, 7, 15), date(2024, 7, 16), date(2024, 7, 18), date(2024, 7, 19)]
