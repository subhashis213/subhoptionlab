# Building a StockMock-style Options Backtesting Tool — Build Plan

## 1. What the tool in your screenshots is actually doing

Breaking down the UI into what's happening behind the scenes:

**Strategy Builder (Image 1)**
- Pick Index (BankNifty/Nifty/FinNifty/MidcapNifty) → Segment (Futures/Options) → Option Type (CE/PE) → Action (Buy/Sell) → Strike selection (ATM/ITM/OTM) → Lots → "Add Position" appends a leg.
- Multi-leg strategies (e.g. Sell ATM CE + Sell ATM PE = short straddle).
- "Use Spot as ATM" vs "Use Futures as ATM" — changes which price the ATM strike is calculated from.
- Per-leg SL%, Target Profit%, Trailing SL, "Move SL to Cost," "Wait & Trade," "Square Off One Leg."
- Entry Time / Exit Time down to the second.
- "Same Day" vs "Next Day" expiry (weekly vs next-weekly contract).

**Date Range & Run (Image 2)**
- Strategy-level Target Profit / Stop Loss (across all legs combined).
- "Protect the Profits" (a ratchet/lock-in mechanism).
- From Date / To Date, with quick presets (1M/3M/6M/1Y/2Y/3Y/From Starting).
- Intraday vs Positional toggle.
- Save/Share strategy.

**Results Dashboard (Image 3)**
- Overall Profit, Avg Day Profit, Max Profit, Win% (Days), Loss% (Days), Avg Monthly Profit, Avg Profit on Win Days.
- Max Drawdown (MDD) + MDD Days (Recovery Days) with the actual date range of the worst drawdown.
- Max Winning/Losing Streak, SL/TP hit counts, Expectancy, Estimated Margin.

So functionally, this is: **a strategy DSL (legs + rules) → a historical options-price simulator → a stats engine that turns a day-by-day P&L series into all those cards.**

---

## 2. The one hard part: historical options data

Everything else here is standard engineering. This is the part that decides whether your tool is accurate or a toy, so decide it first.

You need, for each trading day, the option premium (ideally minute-level, at minimum multiple intraday snapshots) for every relevant strike/expiry of BankNifty/Nifty, going back years. Three realistic paths:

| Path | What you get | Cost | Effort |
|---|---|---|---|
| **A. NSE Bhavcopy (free)** | Daily EOD OHLC per strike/expiry, back to ~2017 | Free | Low — just a daily download+parse job |
| **B. Paid intraday vendor** (Truedata, Global Datafeeds/GDFL, Sensibull data license, AlgoTest data) | 1-min OHLC per strike/expiry, multi-year history | ₹2k–15k/month depending on vendor & years | Medium — vendor integration |
| **C. Build your own going forward** | You already pull live option chain via Upstox for your Nifty bot — start persisting every strike's LTP every minute during market hours from today onward | Free (uses what you have) | Low, but you only get history *after* you start |

**Recommended for you specifically:** since you already have a working Upstox-based data pipeline (from your Nifty bot), do **A + C together** for the MVP:
- Use free NSE bhavcopy for day-level backtests going back to 2017 (this alone replicates ~80% of what StockMock's dashboard shows, since Win%, Overall Profit, Drawdown etc. can all be computed off end-of-day option settlement prices with entry/exit approximated at bhavcopy close, or by scraping NSE's intraday snapshot files where available).
- In parallel, start recording your own 1-minute option chain snapshots from your existing Upstox feed. In 3–6 months you'll have real intraday data for accurate SL/target-hit simulation, and can upgrade the engine then.
- If your Reels/CSIR-NET or trading bot income justifies it later, add Path B for a proper backtest going back years at minute resolution.

I'll design the schema and engine so it works with daily data now and drops in intraday data later without a rewrite.

---

## 3. Data model

```
# instruments (contract master)
symbol         # BANKNIFTY, NIFTY, FINNIFTY
expiry_date
strike
option_type    # CE / PE
lot_size       # varies by date! (you already noted this in StockMock's footnote)

# option_prices  (daily grain to start; add a `minute` column later)
instrument_id
trade_date
[minute]       # nullable for now, populate later
open, high, low, close
oi, volume

# underlying_prices (spot + futures, for ATM calculation)
symbol
trade_date
[minute]
spot_close, fut_close

# strategies (user-saved)
id, user_id, name, config_json, created_at

# backtest_runs
id, strategy_id, from_date, to_date, params_json, status
daily_pnl_json   # [{date, pnl, exit_reason}]
metrics_json     # the computed stats cards
```

Store `option_prices` as partitioned Parquet files (by symbol + year) read via DuckDB/Polars for the backtest — this is dramatically faster than MongoDB for scanning millions of rows across years, which is what a backtest engine spends 90% of its time doing. Keep MongoDB for strategies/users/runs (matches your existing MERN stack) and use Parquet+DuckDB purely as the time-series read layer, queried from a Python service.

---

## 4. Backtest engine — core logic

```
for each trading_day in [from_date .. to_date]:
    if trading_day is not a valid NSE trading day: skip

    expiry = resolve_expiry(trading_day, same_day_or_next_day_setting)

    spot_or_fut_at_entry = get_price(underlying, trading_day, entry_time, use_futures_flag)
    atm_strike = round_to_strike_interval(spot_or_fut_at_entry, symbol)  # 100 for BANKNIFTY, 50 for NIFTY

    legs = []
    for leg_config in strategy.legs:
        strike = resolve_strike(atm_strike, leg_config.offset)  # ATM/ITM-n/OTM-n
        entry_price = get_option_price(strike, leg_config.type, expiry, trading_day, entry_time)
        legs.append({...leg_config, strike, entry_price, status: "open"})

    # Walk forward from entry_time to exit_time (minute bars if available,
    # else just evaluate at exit_time using daily OHLC as a proxy for whether
    # intraday high/low would have breached SL/target)
    for t in time_steps(entry_time, exit_time):
        for leg in open_legs:
            price_now = get_option_price(leg.strike, leg.type, expiry, trading_day, t)
            check_leg_sl_target(leg, price_now)       # per-leg SL%/target%, trailing SL, move-SL-to-cost
        check_strategy_level_sl_target(legs)           # combined SL/TP across all legs
        check_protect_profits(legs)                    # ratchet lock-in

    close_remaining_legs_at(exit_time)
    day_pnl = sum(leg.realized_pnl for leg in legs)
    record(trading_day, day_pnl, exit_reason)
```

With daily-only data, `check_leg_sl_target` uses that day's High/Low as an approximation (if Low breached the SL trigger price, assume SL hit) — less precise than true intraday, but this is exactly how most retail backtesters degrade gracefully without minute data, and it's still directionally correct for strategy evaluation.

---

## 5. Metrics — exact formulas for each dashboard card

- **Overall Profit** = Σ day_pnl across range
- **Avg Day Profit** = Overall Profit ÷ trading days in range
- **Max Profit** = max(day_pnl)
- **Win% (Days)** = (days with pnl > 0) ÷ total days × 100
- **Loss% (Days)** = (days with pnl < 0) ÷ total days × 100
- **Avg Monthly Profit** = Overall Profit ÷ number of distinct calendar months in range
- **Avg Profit on Win Days** = Σ(pnl where pnl>0) ÷ count(win days)
- **Max Drawdown (MDD)** = min over t of (equity[t] − running_max(equity[0..t])); also express as % of that running max
- **MDD Days (Recovery Days)** = days from the trough back to when equity re-exceeds the prior peak; report the [start, end] dates of that drawdown window
- **Max Winning/Losing Streak** = longest run of consecutive win/loss days
- **Expectancy** = (Win% × Avg Profit on Win Days) − (Loss% × Avg Loss on Losing Days)
- **SL/TP Hit Count** = tally of `exit_reason` across all days (`sl_hit`, `tp_hit`, `time_exit`)
- **Estimated Margin** = SPAN + exposure margin for the net position on the last day — either call a broker margin-calculator API (Upstox has one) or approximate via NSE's published SPAN files

---

## 6. API design (FastAPI, matches your existing bot's stack)

```
POST /strategies              # save a strategy config
GET  /strategies/{id}
POST /backtest/run             # { strategy_id | inline config, from_date, to_date }
                                # → runs async, returns run_id
GET  /backtest/{run_id}/status
GET  /backtest/{run_id}/results   # metrics_json + daily_pnl_json (for equity curve chart)
GET  /instruments/expiries?symbol=BANKNIFTY
GET  /instruments/atm?symbol=&date=&time=
```

Run backtests as background jobs (Celery, or simple asyncio task queue since you already use APScheduler in the trading bot) — a multi-year daily backtest over a multi-leg strategy is CPU-bound and shouldn't block the request thread.

---

## 7. Frontend (React + Vite, matches your stack)

- `StrategyBuilder.jsx` — mirrors Image 1: index/segment/type/action/strike dropdowns, "Add Position" leg list, per-leg SL/target/trailing inputs.
- `BacktestConfig.jsx` — mirrors Image 2: entry/exit time pickers, strategy-level SL/TP, date range with quick presets, intraday/positional toggle.
- `ResultsDashboard.jsx` — mirrors Image 3: stat cards grid + an equity curve chart (recharts) + a monthly P&L heatmap.
- `SavedStrategies.jsx` — sidebar list, save/load/share.

---

## 8. Build order (do it in this sequence)

1. NSE bhavcopy downloader + parser → Parquet store (BankNifty + Nifty, 2017–present).
2. Strike/expiry/ATM resolution utilities + unit tests against a few known dates.
3. Single-leg backtest engine (just Sell ATM CE, no SL/target) → validate P&L against a manual spot-check.
4. Add multi-leg, SL%, target%, trailing SL, strategy-level SL/TP.
5. Metrics module (section 5) with unit tests.
6. FastAPI endpoints + async job runner.
7. React strategy builder + results dashboard.
8. Start your own minute-level data capture in parallel (Path C) for future precision upgrade.
9. Auth + save/share strategies.

---

## 9. Prompt for Antigravity

Paste this in as your project brief:

```
Build an options-strategy backtesting web app for Indian indices (NIFTY, BANKNIFTY,
FINNIFTY), similar in functionality to StockMock's backtester. Stack: Python
FastAPI backend, React + Vite frontend, MongoDB for app data (strategies, users,
backtest runs), Parquet files queried via DuckDB/Polars for historical option
price time series.

PHASE 1 — Data layer
- Build a script that downloads NSE's daily F&O bhavcopy files (CSV, publicly
  available from NSE's archives) for a given date range, parses out BANKNIFTY
  and NIFTY option contracts (strike, expiry, option type, OHLC, OI, volume),
  and writes them into partitioned Parquet files (partition by symbol and year).
- Also parse and store daily underlying (index) OHLC for BANKNIFTY and NIFTY.
- Handle the historical lot-size change for BANKNIFTY (75 until 21-Jul-23, 15
  after) and Nifty's variable lot size — store lot_size as an attribute that
  varies by date, not a constant.
- Write a query module with functions:
  get_option_price(symbol, strike, option_type, expiry, date) -> OHLC row
  get_underlying_price(symbol, date, use_futures: bool) -> price
  resolve_atm_strike(symbol, price) -> nearest valid strike (100-pt steps for
  BANKNIFTY, 50-pt for NIFTY)
  resolve_expiry(symbol, date, "same_day" | "next_day") -> expiry_date

PHASE 2 — Backtest engine
- Strategy config schema (JSON): symbol, segment, legs[] where each leg has
  {option_type, action (buy/sell), strike_selection (ATM/ITM-n/OTM-n), lots,
  sl_percent, target_percent, trailing_sl (optional), move_sl_to_cost (bool)},
  strategy_level_sl_percent, strategy_level_target_percent,
  protect_profits (optional), entry_time, exit_time, expiry_mode
  (same_day/next_day), date_from, date_to, mode (intraday/positional).
- For each trading day in range: resolve ATM strike at entry_time, resolve each
  leg's strike and entry price, then walk forward to exit_time checking each
  leg's SL/target against that day's High/Low as a conservative proxy (since
  we start with daily-only data — leave a clean extension point to swap in
  minute-level OHLC later without changing the engine's public interface),
  apply strategy-level SL/target and profit-protection rules, close remaining
  legs at exit_time, record {date, pnl, exit_reason, per_leg_breakdown}.
- Output: a list of daily results across the full date range (the "equity
  curve" input).

PHASE 3 — Metrics module
Given the daily results list, compute: Overall Profit, Avg Day Profit, Max
Profit, Win% (Days), Loss% (Days), Avg Monthly Profit, Avg Profit on Win Days,
Max Drawdown (value + %) with the [start_date, end_date] of the drawdown
window and recovery days count, Max Winning Streak, Max Losing Streak,
Expectancy, and counts of exit_reason == sl_hit / tp_hit / time_exit. Write
unit tests with a small synthetic daily-pnl series where I can hand-verify
every number.

PHASE 4 — API
FastAPI endpoints:
POST /strategies (save config)
GET /strategies/{id}
POST /backtest/run (accepts strategy config + date range, runs as a background
  task, returns run_id immediately)
GET /backtest/{run_id}/status
GET /backtest/{run_id}/results (metrics + daily pnl series for charting)
GET /instruments/expiries?symbol=
Use MongoDB (motor async driver) for strategies/runs/users. Use a simple
in-process background task queue (or Celery if Redis is available) so long
backtests don't block requests.

PHASE 5 — Frontend
React + Vite app with:
- A strategy builder form: index/segment/option-type/action/strike-selection/
  lots dropdowns with an "Add Position" button that appends a leg row (each
  row editable/removable), matching a multi-leg options strategy builder UI.
- A settings panel: entry time / exit time pickers, ATM basis toggle
  (spot/futures), same-day/next-day expiry radio, strategy-level SL/target
  inputs, date-range picker with quick presets (1M/3M/6M/1Y/2Y/3Y/from
  earliest available data), intraday/positional toggle, "Run Backtest" button.
- A results dashboard: a grid of stat cards for every metric from Phase 3, an
  equity curve line chart (recharts) of cumulative P&L over the date range, a
  monthly P&L heatmap/table.
- A "Saved Strategies" sidebar to save/load/rename backtest configs.
Use Tailwind for styling. Keep components small and typed with PropTypes or
TypeScript if you set the project up in TS.

Start with Phase 1 and stop for my review before moving to Phase 2 — I want
to sanity-check the parsed bhavcopy data against a couple of known BANKNIFTY
option prices before building the engine on top of it.
```

---

**One thing worth deciding before you hand this to Antigravity:** whether you want to start on free daily bhavcopy data (accurate strategy comparison, less precise on exact SL/target timing) or pay for a minute-level vendor from day one. Given you're already running the live Nifty bot on Upstox, my suggestion above (free bhavcopy now + start recording your own live minute data in parallel) gets you a working tool this week and a properly precise one in a few months, at zero extra cost.
