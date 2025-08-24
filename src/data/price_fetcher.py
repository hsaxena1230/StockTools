import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import psycopg2.extras

class PriceFetcher:
    def __init__(self):
        self.batch_size = 50  # Process stocks in batches
        self.retry_limit = 3
        self.retry_delay = 2  # seconds
    
    def fetch_historical_prices(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch historical prices for a single stock"""
        try:
            # Download data from Yahoo Finance
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
                    'close_price': float(round(row['Close'], 2)),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                    'high': float(round(row['High'], 2)) if pd.notna(row['High']) else None,
                    'low': float(round(row['Low'], 2)) if pd.notna(row['Low']) else None,
                    'open': float(round(row['Open'], 2)) if pd.notna(row['Open']) else None
                })
            
            return price_data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return []
    
    def fetch_with_retry(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch prices with retry logic"""
        for attempt in range(self.retry_limit):
            try:
                data = self.fetch_historical_prices(symbol, start_date, end_date)
                if data:
                    return data
            except Exception as e:
                if attempt < self.retry_limit - 1:
                    print(f"Retry {attempt + 1} for {symbol} after error: {e}")
                    time.sleep(self.retry_delay)
                else:
                    print(f"Failed to fetch {symbol} after {self.retry_limit} attempts")
        
        return []
    
    def fetch_batch_historical_prices(self, stocks: List[Dict], start_date: datetime, end_date: datetime) -> Dict[int, List[Dict]]:
        """Fetch historical prices for multiple stocks"""
        all_price_data = {}
        
        for i, stock in enumerate(stocks, 1):
            print(f"Fetching {i}/{len(stocks)}: {stock['symbol']} - {stock['name']}")
            
            price_data = self.fetch_with_retry(stock['symbol'], start_date, end_date)
            
            if price_data:
                # Add stock_id and symbol to each record
                for record in price_data:
                    record['stock_id'] = stock['id']
                    record['symbol'] = stock['symbol']
                
                all_price_data[stock['id']] = price_data
                print(f"  ✓ Fetched {len(price_data)} days of data")
            else:
                print(f"  ✗ No data fetched")
            
            # Rate limiting to avoid overwhelming the API
            if i % 10 == 0:
                time.sleep(1)
        
        return all_price_data
    
    def fetch_latest_prices(self, stocks: List[Dict]) -> List[Dict]:
        """Fetch only the latest closing prices for daily updates"""
        latest_prices = []
        
        for i, stock in enumerate(stocks, 1):
            try:
                ticker = yf.Ticker(stock['symbol'])
                
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
                        print(f"  ✗ {stock['symbol']}: No close price available")
                        continue
                    
                    price_record = {
                        'time': latest_date.to_pydatetime(),
                        'stock_id': stock['id'],
                        'symbol': stock['symbol'],
                        'close_price': float(round(latest_row['Close'], 2)),
                        'volume': int(latest_row['Volume']) if pd.notna(latest_row['Volume']) else None,
                        'high': float(round(latest_row['High'], 2)) if pd.notna(latest_row['High']) else None,
                        'low': float(round(latest_row['Low'], 2)) if pd.notna(latest_row['Low']) else None,
                        'open': float(round(latest_row['Open'], 2)) if pd.notna(latest_row['Open']) else None
                    }
                    
                    latest_prices.append(price_record)
                    print(f"  ✓ {stock['symbol']}: ₹{price_record['close_price']} on {latest_date.strftime('%Y-%m-%d')}")
                else:
                    print(f"  ✗ {stock['symbol']}: No recent data")
                    
            except Exception as e:
                print(f"  ✗ {stock['symbol']}: Error - {e}")
            
            # Rate limiting
            if i % 10 == 0:
                time.sleep(1)
        
        return latest_prices