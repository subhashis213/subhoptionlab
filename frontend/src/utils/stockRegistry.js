export const TOP_FO_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Limited", "lot_size": 250},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Limited", "lot_size": 400},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Limited", "lot_size": 700},
    {"symbol": "INFY", "name": "Infosys Limited", "lot_size": 400},
    {"symbol": "TCS", "name": "Tata Consultancy Services Limited", "lot_size": 175},
    {"symbol": "ITC", "name": "ITC Limited", "lot_size": 1600},
    {"symbol": "LT", "name": "Larsen & Toubro Limited", "lot_size": 300},
    {"symbol": "SBIN", "name": "State Bank of India", "lot_size": 1500},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Limited", "lot_size": 950},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Limited", "lot_size": 400},
    {"symbol": "AXISBANK", "name": "Axis Bank Limited", "lot_size": 625},
    {"symbol": "TATASTEEL", "name": "Tata Steel Limited", "lot_size": 5500},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Limited", "lot_size": 1425},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Limited", "lot_size": 200},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Limited", "lot_size": 50},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Limited", "lot_size": 700},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Limited", "lot_size": 300},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Limited", "lot_size": 125},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Limited", "lot_size": 700},
    {"symbol": "NTPC", "name": "NTPC Limited", "lot_size": 3000},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation of India Limited", "lot_size": 3600},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Limited", "lot_size": 100},
    {"symbol": "TITAN", "name": "Titan Company Limited", "lot_size": 175},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Limited", "lot_size": 500},
    {"symbol": "WIPRO", "name": "Wipro Limited", "lot_size": 1500},
    {"symbol": "NESTLEIND", "name": "Nestle India Limited", "lot_size": 400},
    {"symbol": "HCLTECH", "name": "HCL Technologies Limited", "lot_size": 700},
    {"symbol": "TECHM", "name": "Tech Mahindra Limited", "lot_size": 600},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corporation Limited", "lot_size": 3850},
    {"symbol": "COALINDIA", "name": "Coal India Limited", "lot_size": 2100},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Limited", "lot_size": 1400},
    {"symbol": "GRASIM", "name": "Grasim Industries Limited", "lot_size": 475},
    {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Limited", "lot_size": 125},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Limited", "lot_size": 300},
    {"symbol": "ADANIPORTS", "name": "Adani Ports and Special Economic Zone Limited", "lot_size": 800},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories Limited", "lot_size": 200},
    {"symbol": "CIPLA", "name": "Cipla Limited", "lot_size": 650},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Limited", "lot_size": 125},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Limited", "lot_size": 175},
    {"symbol": "UPL", "name": "UPL Limited", "lot_size": 1300},
    {"symbol": "BRITANNIA", "name": "Britannia Industries Limited", "lot_size": 200},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Limited", "lot_size": 500},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corporation Limited", "lot_size": 1800},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Limited", "lot_size": 300},
];

export const LOT_SIZES = { NIFTY: 75, BANKNIFTY: 30, FINNIFTY: 65, MIDCAPNIFTY: 120 }

export function getLotSize(symbol) {
  if (!symbol) return 1;
  const upper = symbol.toUpperCase();
  if (LOT_SIZES[upper]) return LOT_SIZES[upper];
  
  const stock = TOP_FO_STOCKS.find(s => s.symbol === upper);
  if (stock) return stock.lot_size;
  
  return 1;
}
