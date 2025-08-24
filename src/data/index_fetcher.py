import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

class IndexFetcher:
    def __init__(self):
        self.index_symbols = {
            'NIFTY_500': '^CRSLDX',
            'NIFTY_50': '^NSEI',
            'NIFTY_BANK': '^NSEBANK',
            'SENSEX': '^BSESN'
        }
    
    def fetch_index_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch historical data for an index"""
        try:
            print(f"Fetching data for index {symbol}...")
            ticker = yf.Ticker(symbol)
            
            # Fetch historical data
            df = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if df.empty:
                print(f"No data found for {symbol}")
                return []
            
            # Convert to list of dictionaries
            price_data = []
            for index, row in df.iterrows():
                # Skip rows with null close prices
                if pd.isna(row['Close']):
                    continue
                
                price_data.append({
                    'time': index.to_pydatetime(),
                    'symbol': symbol,
                    'close_price': float(round(row['Close'], 2)),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                    'high': float(round(row['High'], 2)) if pd.notna(row['High']) else None,
                    'low': float(round(row['Low'], 2)) if pd.notna(row['Low']) else None,
                    'open': float(round(row['Open'], 2)) if pd.notna(row['Open']) else None
                })
            
            print(f"Fetched {len(price_data)} records for {symbol}")
            return price_data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return []
    
    def fetch_nifty_500_data(self, years_back: int = 10) -> List[Dict]:
        """Fetch Nifty 500 historical data"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years_back)
        
        return self.fetch_index_data(self.index_symbols['NIFTY_500'], start_date, end_date)
    
    def fetch_latest_index_price(self, symbol: str) -> Optional[Dict]:
        """Fetch the latest price for an index"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Fetch last 5 days to ensure we get the latest trading day
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            df = ticker.history(start=start_date, end=end_date, interval="1d")
            
            if not df.empty:
                # Get the most recent trading day
                latest_row = df.iloc[-1]
                latest_date = df.index[-1]
                
                # Skip if close price is null
                if pd.isna(latest_row['Close']):
                    return None
                
                return {
                    'time': latest_date.to_pydatetime(),
                    'symbol': symbol,
                    'close_price': float(round(latest_row['Close'], 2)),
                    'volume': int(latest_row['Volume']) if pd.notna(latest_row['Volume']) else None,
                    'high': float(round(latest_row['High'], 2)) if pd.notna(latest_row['High']) else None,
                    'low': float(round(latest_row['Low'], 2)) if pd.notna(latest_row['Low']) else None,
                    'open': float(round(latest_row['Open'], 2)) if pd.notna(latest_row['Open']) else None
                }
            
            return None
            
        except Exception as e:
            print(f"Error fetching latest price for {symbol}: {e}")
            return None
    
    def fetch_all_indices_latest(self) -> List[Dict]:
        """Fetch latest prices for all tracked indices"""
        latest_prices = []
        
        for index_name, symbol in self.index_symbols.items():
            print(f"Fetching latest price for {index_name} ({symbol})...")
            price_data = self.fetch_latest_index_price(symbol)
            
            if price_data:
                latest_prices.append(price_data)
                print(f"  ✓ {index_name}: {price_data['close_price']} on {price_data['time'].strftime('%Y-%m-%d')}")
            else:
                print(f"  ✗ {index_name}: No recent data")
            
            # Rate limiting
            time.sleep(1)
        
        return latest_prices