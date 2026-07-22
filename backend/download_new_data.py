import requests
import time

res = requests.post("http://127.0.0.1:8000/api/data/download", json={
    "from_date": "2026-07-18",
    "to_date": "2026-07-21",
    "delay": 1.0
})
print("Download started:", res.json())
run_id = res.json()["run_id"]

for i in range(30):
    status_res = requests.get(f"http://127.0.0.1:8000/api/backtest/{run_id}/status")
    if status_res.status_code == 200:
        data = status_res.json()
        print(data)
        if data["status"] in ("completed", "failed"):
            break
    time.sleep(2)
