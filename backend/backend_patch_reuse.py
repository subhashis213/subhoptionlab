import asyncio
from datetime import datetime, date, timedelta
from papertrade.models import StrategyCreate
# Just testing next thursday
def _next_thursday():
    d = date.today()
    days_ahead = 3 - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days_ahead)
print(_next_thursday().isoformat())
