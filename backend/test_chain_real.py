import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv
import json

load_dotenv()
token = _get_access_token()
url = f"{UPSTOX_BASE_URL}/v2/option/chain"
res = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "2026-08-25"}, headers=_make_headers(token))
data = res.json().get("data", [])
if data:
    print(json.dumps(data[0]))
else:
    print("No data")
