from datetime import date
from data.queries import get_available_trade_dates
from engine.schemas import StrategyConfig, LegConfig, OptionType, Action
from engine.backtest import run_backtest

dates = get_available_trade_dates('BANKNIFTY', date(2026, 7, 1), date(2026, 7, 22))
print("Available trade dates in DB for BANKNIFTY:", [str(d) for d in dates])

config = StrategyConfig(
    symbol="BANKNIFTY",
    legs=[
        LegConfig(
            option_type=OptionType.CE,
            action=Action.SELL,
            strike_selection="ATM",
            lots=1
        )
    ]
)

res = run_backtest(config, date(2026, 7, 1), date(2026, 7, 22))
print("Backtest results dates:", [str(d.trade_date) for d in res.daily_results])
