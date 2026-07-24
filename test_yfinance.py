import yfinance as yf
ticker = yf.Ticker("^NSEI")
info = ticker.info
print("NIFTY 50:", info.get("currentPrice", info.get("regularMarketPrice")))
print("Change:", info.get("regularMarketChange"), info.get("regularMarketChangePercent"))
