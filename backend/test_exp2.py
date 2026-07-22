import requests, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv("UPSTOX_ACCESS_TOKEN")
headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}

# Try to get option contracts for BANKNIFTY
url = "https://api.upstox.com/v2/option/contract"
params = {"instrument_key": "NSE_INDEX|Nifty Bank"}
response = requests.get(url, params=params, headers=headers)
data = response.json().get('data', [])
print("Contracts returned:", len(data))
if data:
    expiries = {x['expiry'] for x in data}
    print("Available expiries:", sorted(list(expiries))[:5])
