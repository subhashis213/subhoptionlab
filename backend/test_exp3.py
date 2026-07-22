import requests, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv("UPSTOX_ACCESS_TOKEN")
headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}

url = "https://api.upstox.com/v2/option/contract"
params = {"instrument_key": "NSE_INDEX|Nifty 50"}
response = requests.get(url, params=params, headers=headers)
print(response.json())
