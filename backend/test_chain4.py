import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("UPSTOX_ACCESS_TOKEN")

url = "https://api.upstox.com/v2/option/chain"
params = {
    "instrument_key": "NSE_INDEX|Nifty Bank",
    "expiry_date": "2026-07-22"
}
headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}'
}
response = requests.get(url, params=params, headers=headers)
print("Status:", response.status_code)
print(response.json())
