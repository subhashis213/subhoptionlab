import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv
import json

load_dotenv()
token = _get_access_token()
url = f"{UPSTOX_BASE_URL}/v2/option/contract"
res = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "2024-10-01"}, headers=_make_headers(token))
data = res.json().get("data", [])
for d in data[:5]:
    print(json.dumps(d))
