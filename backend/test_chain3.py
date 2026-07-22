import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("UPSTOX_ACCESS_TOKEN")

for date in ["2026-07-22", "2026-07-23", "2026-07-24", "2026-07-30"]:
    url = f"https://api.upstox.com/v2/option/chain?instrument_key=NSE_INDEX|Nifty%20Bank&expiry_date={date}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(url, headers=headers)
    data = response.json().get('data', [])
    print(f"Date: {date}, Length: {len(data)}")
