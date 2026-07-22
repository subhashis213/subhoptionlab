import asyncio
import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv

load_dotenv()
token = _get_access_token()
headers = _make_headers(token)

url = f"{UPSTOX_BASE_URL}/v2/option/chain"
res = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "current_month"}, headers=headers)
data = res.json().get("data", [])
strikes = [d["strike_price"] for d in data]
print(f"Min Strike: {min(strikes)}, Max Strike: {max(strikes)}")
print(f"Is 57800 in strikes? {57800 in strikes}")
