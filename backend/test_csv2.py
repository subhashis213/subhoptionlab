import requests
import io
import gzip
import csv

url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'
response = requests.get(url)
with gzip.open(io.BytesIO(response.content), 'rt') as f:
    reader = csv.DictReader(f)
    print(reader.fieldnames)
    count = 0
    for row in reader:
        if row['name'] == 'BANKNIFTY' and row['instrument_type'] in ['CE', 'PE']:
            print(row['instrument_key'], row['tradingsymbol'], row['expiry'], row['strike'], row['instrument_type'])
            count += 1
            if count > 5:
                break
