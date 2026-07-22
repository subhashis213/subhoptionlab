import requests, os, json
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("UPSTOX_ACCESS_TOKEN")

headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {token}'
}

# Upstox v2 API has an endpoint for option contracts?
url = "https://api.upstox.com/v2/market/instruments/master"
# We won't download the whole master here, it's a huge CSV.
# Let's search via quote api if there's any other way.

# Wait, maybe the Option Chain API can return valid expiries if we send an invalid one?
url_oc = "https://api.upstox.com/v2/option/chain"
params = {"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "2024-07-24"}
response = requests.get(url_oc, params=params, headers=headers)
print("2024-07-24:", len(response.json().get('data', [])))

params = {"instrument_key": "NSE_INDEX|Nifty Bank", "expiry_date": "2024-11-20"}
response = requests.get(url_oc, params=params, headers=headers)
print("2024-11-20:", len(response.json().get('data', [])))
