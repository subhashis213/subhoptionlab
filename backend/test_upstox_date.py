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
print("Status:", res.status_code)
data = res.json().get("data", [])
print("Data items:", len(data))
