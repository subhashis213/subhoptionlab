"""
Metrics Calculator — computes all dashboard stat cards from daily P&L results.

Given a list of DailyResult objects from the backtest engine, computes:
- Overall Profit, Avg Day Profit, Max Profit, Max Loss
- Win% (Days), Loss% (Days)
- Avg Monthly Profit, Avg Profit on Win Days, Avg Loss on Losing Days
- Max Drawdown (value + %) with start/end dates and recovery days
- Max Winning/Losing Streak
- Expectancy
- SL/TP/Time Exit hit counts
"""

from datetime import date
from engine.schemas import DailyResult


def compute_metrics(daily_results: list[DailyResult]) -> dict:
    """
    Compute all dashboard metrics from a list of daily backtest results.

    Args:
        daily_results: List of DailyResult from the backtest engine.

    Returns:
        Dictionary of computed metrics for the dashboard.
    """
    if not daily_results:
        return _empty_metrics()

    # Extract P&L series
    pnl_series = [d.total_pnl_value for d in daily_results]
    pnl_points_series = [d.total_pnl_points for d in daily_results]
    dates = [d.trade_date for d in daily_results]
    exit_reasons = [d.exit_reason for d in daily_results]

    total_days = len(daily_results)

    # ── Basic P&L Metrics ──
    overall_profit = sum(pnl_series)
    overall_profit_points = sum(pnl_points_series)
    avg_day_profit = overall_profit / total_days if total_days > 0 else 0
    max_profit = max(pnl_series)
    max_loss = min(pnl_series)

    # ── Win/Loss Split ──
    win_days = [p for p in pnl_series if p > 0]
    loss_days = [p for p in pnl_series if p < 0]
    flat_days = [p for p in pnl_series if p == 0]

    win_count = len(win_days)
    loss_count = len(loss_days)
    flat_count = len(flat_days)

    win_pct = (win_count / total_days * 100) if total_days > 0 else 0
    loss_pct = (loss_count / total_days * 100) if total_days > 0 else 0

    avg_profit_on_win = sum(win_days) / win_count if win_count > 0 else 0
    avg_loss_on_loss = sum(loss_days) / loss_count if loss_count > 0 else 0

    # ── Monthly Metrics ──
    months = set()
    for d in dates:
        months.add((d.year, d.month))
    num_months = len(months) or 1
    avg_monthly_profit = overall_profit / num_months

    # ── Drawdown ──
    dd_result = _compute_max_drawdown(pnl_series, dates)

    # ── Streaks ──
    max_win_streak, max_loss_streak = _compute_streaks(pnl_series)

    # ── Expectancy ──
    # E = (Win% × Avg Win) + (Loss% × Avg Loss)  [note: avg_loss is negative]
    win_frac = win_count / total_days if total_days > 0 else 0
    loss_frac = loss_count / total_days if total_days > 0 else 0
    expectancy = (win_frac * avg_profit_on_win) + (loss_frac * avg_loss_on_loss)

    # ── Exit Reason Counts ──
    sl_hit_count = sum(1 for r in exit_reasons if "sl" in r.lower() or "sl_hit" in r.lower())
    tp_hit_count = sum(1 for r in exit_reasons if "target" in r.lower() or "tp" in r.lower())
    time_exit_count = sum(1 for r in exit_reasons if "time" in r.lower() and "sl" not in r.lower() and "target" not in r.lower())

    return {
        "overall_profit": round(overall_profit, 2),
        "overall_profit_points": round(overall_profit_points, 2),
        "avg_day_profit": round(avg_day_profit, 2),
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
        "total_trading_days": total_days,
        "win_days": win_count,
        "loss_days": loss_count,
        "flat_days": flat_count,
        "win_pct": round(win_pct, 2),
        "loss_pct": round(loss_pct, 2),
        "avg_profit_on_win_days": round(avg_profit_on_win, 2),
        "avg_loss_on_loss_days": round(avg_loss_on_loss, 2),
        "avg_monthly_profit": round(avg_monthly_profit, 2),
        "num_months": num_months,
        "max_drawdown": round(dd_result["max_drawdown"], 2),
        "max_drawdown_pct": round(dd_result["max_drawdown_pct"], 2),
        "drawdown_start_date": str(dd_result["dd_start_date"]) if dd_result["dd_start_date"] else None,
        "drawdown_end_date": str(dd_result["dd_end_date"]) if dd_result["dd_end_date"] else None,
        "recovery_days": dd_result["recovery_days"],
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "expectancy": round(expectancy, 2),
        "sl_hit_count": sl_hit_count,
        "tp_hit_count": tp_hit_count,
        "time_exit_count": time_exit_count,
        # Equity curve data
        "equity_curve": _build_equity_curve(pnl_series, dates),
        # Monthly P&L breakdown
        "monthly_pnl": _build_monthly_pnl(pnl_series, dates),
    }


def _compute_max_drawdown(
    pnl_series: list[float],
    dates: list[date],
) -> dict:
    """
    Compute maximum drawdown from a P&L series.

    MDD = max over t of (peak_equity[0..t] - equity[t])
    """
    if not pnl_series:
        return {
            "max_drawdown": 0, "max_drawdown_pct": 0,
            "dd_start_date": None, "dd_end_date": None,
            "recovery_days": 0,
        }

    # Build cumulative equity curve
    equity = []
    cum = 0
    for p in pnl_series:
        cum += p
        equity.append(cum)

    # Find max drawdown
    peak = equity[0]
    peak_idx = 0
    max_dd = 0
    max_dd_peak_idx = 0
    max_dd_trough_idx = 0

    for i, eq in enumerate(equity):
        if eq > peak:
            peak = eq
            peak_idx = i
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            max_dd_peak_idx = peak_idx
            max_dd_trough_idx = i

    # Calculate drawdown as percentage of peak
    peak_value = equity[max_dd_peak_idx] if max_dd_peak_idx < len(equity) else 0
    max_dd_pct = (max_dd / peak_value * 100) if peak_value > 0 else 0

    # Find recovery (when equity exceeds prior peak after trough)
    recovery_days = 0
    dd_end_date = None
    if max_dd > 0:
        for i in range(max_dd_trough_idx + 1, len(equity)):
            if equity[i] >= equity[max_dd_peak_idx]:
                recovery_days = i - max_dd_trough_idx
                dd_end_date = dates[i] if i < len(dates) else None
                break
        else:
            # Not yet recovered
            recovery_days = len(equity) - max_dd_trough_idx
            dd_end_date = dates[-1] if dates else None

    return {
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "dd_start_date": dates[max_dd_peak_idx] if max_dd_peak_idx < len(dates) else None,
        "dd_end_date": dd_end_date,
        "recovery_days": recovery_days,
    }


def _compute_streaks(pnl_series: list[float]) -> tuple[int, int]:
    """Compute max winning and losing streaks."""
    max_win = 0
    max_loss = 0
    current_win = 0
    current_loss = 0

    for p in pnl_series:
        if p > 0:
            current_win += 1
            current_loss = 0
            max_win = max(max_win, current_win)
        elif p < 0:
            current_loss += 1
            current_win = 0
            max_loss = max(max_loss, current_loss)
        else:
            current_win = 0
            current_loss = 0

    return max_win, max_loss


def _build_equity_curve(
    pnl_series: list[float],
    dates: list[date],
) -> list[dict]:
    """Build cumulative equity curve data for charting."""
    curve = []
    cum = 0
    for pnl, d in zip(pnl_series, dates):
        cum += pnl
        curve.append({
            "date": str(d),
            "pnl": round(pnl, 2),
            "cumulative": round(cum, 2),
        })
    return curve


def _build_monthly_pnl(
    pnl_series: list[float],
    dates: list[date],
) -> list[dict]:
    """Build monthly P&L summary for heatmap/table."""
    monthly: dict[tuple[int, int], float] = {}
    for pnl, d in zip(pnl_series, dates):
        key = (d.year, d.month)
        monthly[key] = monthly.get(key, 0) + pnl

    result = []
    for (year, month), total_pnl in sorted(monthly.items()):
        result.append({
            "year": year,
            "month": month,
            "pnl": round(total_pnl, 2),
        })
    return result


def _empty_metrics() -> dict:
    """Return empty/zero metrics when no data is available."""
    return {
        "overall_profit": 0,
        "overall_profit_points": 0,
        "avg_day_profit": 0,
        "max_profit": 0,
        "max_loss": 0,
        "total_trading_days": 0,
        "win_days": 0,
        "loss_days": 0,
        "flat_days": 0,
        "win_pct": 0,
        "loss_pct": 0,
        "avg_profit_on_win_days": 0,
        "avg_loss_on_loss_days": 0,
        "avg_monthly_profit": 0,
        "num_months": 0,
        "max_drawdown": 0,
        "max_drawdown_pct": 0,
        "drawdown_start_date": None,
        "drawdown_end_date": None,
        "recovery_days": 0,
        "max_win_streak": 0,
        "max_loss_streak": 0,
        "expectancy": 0,
        "sl_hit_count": 0,
        "tp_hit_count": 0,
        "time_exit_count": 0,
        "equity_curve": [],
        "monthly_pnl": [],
    }
