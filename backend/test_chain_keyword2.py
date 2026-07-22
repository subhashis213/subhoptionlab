import requests
from papertrade.upstox_guard import _get_access_token, _make_headers, UPSTOX_BASE_URL
from dotenv import load_dotenv

load_dotenv()
token = _get_access_token()
url = f"{UPSTOX_BASE_URL}/v2/option/chain"
res = requests.get(url, params={"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "current_week"}, headers=_make_headers(token))
print(res.text)
