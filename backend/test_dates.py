import requests

res = requests.get("http://127.0.0.1:8000/api/instruments/data-range?symbol=BANKNIFTY")
print(res.status_code)
print(res.json())
