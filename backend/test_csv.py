import pandas as pd
import requests
import io
import gzip

url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'
response = requests.get(url)
with gzip.open(io.BytesIO(response.content), 'rt') as f:
    df = pd.read_csv(f)

print(df.columns)
print(df[df['name'] == 'BANKNIFTY'].head())
