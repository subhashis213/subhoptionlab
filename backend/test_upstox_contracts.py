import asyncio
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
import requests
import json

token = _get_access_token()
headers = _make_headers(token)
url = f"{UPSTOX_BASE_URL}/v2/option/contract"
response = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank"}, headers=headers)
data = response.json().get("data", [])
for d in data[:5]:
    print(json.dumps(d))
