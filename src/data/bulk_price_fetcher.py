import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class BulkPriceFetcher:
    def __init__(self, max_workers=5, retry_limit=3, retry_delay=2):
        """
        Initialize bulk price fetcher
        
        Args:
            max_workers: Number of threads for parallel processing
            retry_limit: Number of retry attempts for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.max_workers = max_workers
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay
        self.lock = threading.Lock()
        self.progress_count = 0
    
    def fetch_single_stock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Dict:
        """Fetch historical data for a single stock with retry logic"""
        for attempt in range(self.retry_limit):
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval="1d")
                
                if df.empty:
                    return {
                        'symbol': symbol,
                        'success': False,
                        'reason': 'No data available',
                        'data': []
                    }
                
                # Convert to list of records
                price_data = []
                for index, row in df.iterrows():
                    # Skip rows with null close prices
                    if pd.isna(row['Close']):
                        continue
                    
                    price_data.append({
                        'date': index.date(),
                        'time': index.to_pydatetime(),
                        'close_price': float(round(row['Close'], 2)),
                        'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                        'high': float(round(row['High'], 2)) if pd.notna(row['High']) else None,
                        'low': float(round(row['Low'], 2)) if pd.notna(row['Low']) else None,
                        'open': float(round(row['Open'], 2)) if pd.notna(row['Open']) else None
                    })
                
                # Update progress
                with self.lock:
                    self.progress_count += 1
                
                return {
                    'symbol': symbol,
                    'success': True,
                    'reason': f'Fetched {len(price_data)} records',
                    'data': price_data,
                    'date_range': {
                        'start': df.index[0].date() if not df.empty else None,
                        'end': df.index[-1].date() if not df.empty else None
                    }
                }
                
            except Exception as e:
                if attempt < self.retry_limit - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    with self.lock:
                        self.progress_count += 1
                    
                    return {
                        'symbol': symbol,
                        'success': False,
                        'reason': f'Error after {self.retry_limit} attempts: {str(e)}',
                        'data': []
                    }
        
        return {
            'symbol': symbol,
            'success': False,
            'reason': 'Unknown error',
            'data': []
        }
    
    def get_last_10_years_data(self, symbols: List[str], years_back: int = 10) -> Dict:
        """
        Fetch last N years of data for given list of symbols
        
        Args:
            symbols: List of stock symbols to fetch
            years_back: Number of years of historical data to fetch
        
        Returns:
            Dictionary with results for each symbol
        """
        if not symbols:
            return {}
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years_back)
        
        print(f"Fetching {years_back} years of data for {len(symbols)} symbols")
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Using {self.max_workers} threads for parallel processing\n")
        
        # Initialize progress tracking
        self.progress_count = 0
        results = {}
        
        # Fetch data using thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.fetch_single_stock_data, symbol, start_date, end_date): symbol
                for symbol in symbols
            }
            
            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                try:
                    result = future.result()
                    results[symbol] = result
                    
                    # Print progress
                    status = "✓" if result['success'] else "✗"
                    print(f"{status} [{self.progress_count}/{len(symbols)}] {symbol}: {result['reason']}")
                    
                except Exception as e:
                    results[symbol] = {
                        'symbol': symbol,
                        'success': False,
                        'reason': f'Processing error: {str(e)}',
                        'data': []
                    }
                    print(f"✗ [{self.progress_count}/{len(symbols)}] {symbol}: Processing error: {str(e)}")
        
        # Summary statistics
        successful = sum(1 for r in results.values() if r['success'])
        failed = len(symbols) - successful
        total_records = sum(len(r['data']) for r in results.values() if r['success'])
        
        print(f"\n=== Summary ===")
        print(f"Total symbols processed: {len(symbols)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(successful / len(symbols) * 100):.1f}%")
        print(f"Total price records fetched: {total_records}")
        
        return results
    
    def get_data_summary(self, results: Dict) -> Dict:
        """Get summary statistics from fetched data"""
        successful_symbols = [s for s, r in results.items() if r['success']]
        failed_symbols = [s for s, r in results.items() if not r['success']]
        
        # Group failures by reason
        failure_reasons = {}
        for symbol, result in results.items():
            if not result['success']:
                reason = result['reason']
                if reason not in failure_reasons:
                    failure_reasons[reason] = []
                failure_reasons[reason].append(symbol)
        
        # Data statistics
        total_records = sum(len(r['data']) for r in results.values() if r['success'])
        
        summary = {
            'total_symbols': len(results),
            'successful_count': len(successful_symbols),
            'failed_count': len(failed_symbols),
            'success_rate': len(successful_symbols) / len(results) * 100 if results else 0,
            'total_records': total_records,
            'successful_symbols': successful_symbols,
            'failed_symbols': failed_symbols,
            'failure_reasons': failure_reasons
        }
        
        return summary
    
    def save_to_database(self, results: Dict, db_connection, stock_model) -> Dict:
        """Save fetched data to stock_prices table"""
        from src.models.stock_price import StockPrice
        
        stock_price_model = StockPrice(db_connection)
        
        # Get stock IDs for symbols
        all_stocks = stock_model.get_all_stocks()
        symbol_to_id = {stock['symbol']: stock['id'] for stock in all_stocks}
        
        total_inserted = 0
        total_skipped = 0
        insertion_results = {}
        
        print(f"\nSaving data to stock_prices table...")
        
        for symbol, result in results.items():
            if not result['success']:
                insertion_results[symbol] = {
                    'success': False,
                    'reason': 'No data to insert',
                    'inserted': 0
                }
                continue
            
            # Get stock ID
            stock_id = symbol_to_id.get(symbol)
            if not stock_id:
                insertion_results[symbol] = {
                    'success': False,
                    'reason': 'Stock not found in database',
                    'inserted': 0
                }
                print(f"  ✗ {symbol}: Stock not found in database")
                continue
            
            # Prepare data for insertion
            price_data = []
            for record in result['data']:
                price_data.append({
                    'time': record['time'],
                    'stock_id': stock_id,
                    'symbol': symbol,
                    'close_price': record['close_price'],
                    'volume': record['volume'],
                    'high': record['high'],
                    'low': record['low'],
                    'open': record['open']
                })
            
            # Insert data
            inserted_count = stock_price_model.insert_price_data(price_data)
            
            if inserted_count > 0:
                total_inserted += inserted_count
                insertion_results[symbol] = {
                    'success': True,
                    'reason': f'Inserted {inserted_count} records',
                    'inserted': inserted_count
                }
                print(f"  ✓ {symbol}: {inserted_count} records inserted")
            else:
                total_skipped += len(price_data)
                insertion_results[symbol] = {
                    'success': False,
                    'reason': 'Database insertion failed',
                    'inserted': 0
                }
                print(f"  ✗ {symbol}: Database insertion failed")
        
        print(f"\n=== Database Insertion Summary ===")
        print(f"Total records inserted: {total_inserted}")
        print(f"Total records skipped: {total_skipped}")
        
        successful_inserts = sum(1 for r in insertion_results.values() if r['success'])
        print(f"Successful symbol inserts: {successful_inserts}/{len(results)}")
        
        return insertion_results
    
    def save_to_csv(self, results: Dict, filename: str = None):
        """Save fetched data to CSV files (kept for backward compatibility)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stock_data_{timestamp}.csv"
        
        # Combine all successful data
        all_data = []
        for symbol, result in results.items():
            if result['success']:
                for record in result['data']:
                    all_data.append({
                        'symbol': symbol,
                        'date': record['date'],
                        'open': record['open'],
                        'high': record['high'],
                        'low': record['low'],
                        'close': record['close_price'],
                        'volume': record['volume']
                    })
        
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(filename, index=False)
            print(f"✅ Data saved to {filename}")
            return filename
        else:
            print("❌ No data to save")
            return None


# Convenience function for direct use
def get_historical_data(symbols: List[str], years_back: int = 10, max_workers: int = 5) -> Dict:
    """
    Convenience function to fetch historical data for a list of symbols
    
    Args:
        symbols: List of stock symbols (e.g., ['TCS.NS', 'RELIANCE.BO'])
        years_back: Number of years of data to fetch (default: 10)
        max_workers: Number of parallel threads (default: 5)
    
    Returns:
        Dictionary with results for each symbol
    """
    fetcher = BulkPriceFetcher(max_workers=max_workers)
    return fetcher.get_last_10_years_data(symbols, years_back)