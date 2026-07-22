import asyncio
import os
import requests
from dotenv import load_dotenv

load_dotenv()

UPSTOX_BASE_URL = "https://api.upstox.com"
token = os.getenv("UPSTOX_ACCESS_TOKEN")
print("Token length:", len(token) if token else 0)

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {token}",
}
url = f"{UPSTOX_BASE_URL}/v2/market-quote/ltp?instrument_key=NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank"
res = requests.get(url, headers=headers)
print("Status Code:", res.status_code)
print("Response:", res.text)
