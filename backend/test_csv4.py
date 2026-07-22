import requests
import io
import gzip
import csv

url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'
response = requests.get(url)
with gzip.open(io.BytesIO(response.content), 'rt') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        if row['instrument_type'] in ['CE', 'PE']:
            print(row['instrument_key'], row['tradingsymbol'], row['name'], row['expiry'], row['strike'], row['instrument_type'])
            count += 1
            if count > 5:
                break
