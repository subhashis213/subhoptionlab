import requests
import io
import gzip
import csv

url = 'https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz'
response = requests.get(url)
with gzip.open(io.BytesIO(response.content), 'rt') as f:
    reader = csv.reader(f)
    for _ in range(5):
        print(next(reader))
