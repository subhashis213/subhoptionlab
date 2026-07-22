import requests
from dotenv import load_dotenv
import os
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL

load_dotenv()
token = _get_access_token()
headers = _make_headers(token)

res = requests.get(
    f"{UPSTOX_BASE_URL}/v2/option/chain",
    params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "2026-07-28"},
    headers=headers
)
data = res.json().get("data", [])
strikes = [float(d["strike_price"]) for d in data]
print(f"Min: {min(strikes)}, Max: {max(strikes)}")
print(f"Is 58000 in strikes? {58000.0 in strikes}")
