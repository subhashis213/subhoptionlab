import asyncio
import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv

load_dotenv()
token = _get_access_token()
headers = _make_headers(token)
keys = "NSE_FO|63947,NSE_FO|63948"

res = requests.get(f"{UPSTOX_BASE_URL}/v2/market-quote/ltp", params={"instrument_key": keys}, headers=headers)
print("Status:", res.status_code)
print("Response JSON:")
import json
print(json.dumps(res.json(), indent=2))
