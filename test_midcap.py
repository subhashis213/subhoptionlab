import yfinance as yf
print("MIDCPNIFTY.NS:", yf.Ticker("MIDCPNIFTY.NS").info.get("regularMarketPrice"))
print("^NSEMDCP50:", yf.Ticker("^NSEMDCP50").info.get("regularMarketPrice"))
