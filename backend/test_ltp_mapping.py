import requests

data = {
  "NSE_FO:NIFTY26JUL24200CE": {
    "last_price": 67.8,
    "instrument_token": "NSE_FO|63947"
  },
  "NSE_FO:NIFTY26JUL24200PE": {
    "last_price": 304.2,
    "instrument_token": "NSE_FO|63948"
  }
}

result = {}
for key, quote_info in data.items():
    ltp = quote_info.get("last_price")
    if ltp is not None:
        val = float(ltp)
        result[key] = val
        result[key.replace(":", "|")] = val
        itoken = quote_info.get("instrument_token")
        if itoken:
            result[itoken] = val
            result[itoken.replace("|", ":")] = val

print("Result keys:", list(result.keys()))
print("Lookup 'NSE_FO|63947':", result.get("NSE_FO|63947"))
print("Lookup 'NSE_FO|NIFTY26JUL24200CE':", result.get("NSE_FO|NIFTY26JUL24200CE"))
print("Lookup 'NSE_FO:NIFTY26JUL24200CE':", result.get("NSE_FO:NIFTY26JUL24200CE"))
