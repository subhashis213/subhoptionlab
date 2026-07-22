import asyncio
import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv

load_dotenv()
token = _get_access_token()
keywords = ["current_week", "next_week", "current_month", "next_month", "far_month"]
headers = _make_headers(token)

for kw in keywords:
    url = f"{UPSTOX_BASE_URL}/v2/option/chain"
    res = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": kw}, headers=headers)
    data = res.json().get("data", [])
    if data:
        print(kw, data[0]["expiry"])
    else:
        print(kw, "no data")
