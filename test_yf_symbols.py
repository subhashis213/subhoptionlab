import yfinance as yf
for sym in ["^CNXFIN", "NIFTY_FIN_SERVICE.NS", "^NSEMDCP50"]:
    info = yf.Ticker(sym).info
    print(sym, info.get("regularMarketPrice"))
