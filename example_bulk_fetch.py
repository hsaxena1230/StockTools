#!/usr/bin/env python3
"""
Example usage of bulk price fetcher
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.bulk_price_fetcher import BulkPriceFetcher, get_historical_data
import json

def example_usage():
    """Example of how to use the bulk price fetcher"""
    
    # Example 1: Using the convenience function
    print("=== Example 1: Using convenience function ===")
    
    symbols = ['TCS.NS', 'RELIANCE.NS', 'INFY.NS', 'HDFC.NS', 'ICICIBANK.NS']
    results = get_historical_data(symbols, years_back=2, max_workers=3)
    
    # Show sample data for first successful symbol
    for symbol, result in results.items():
        if result['success'] and result['data']:
            print(f"\nSample data for {symbol}:")
            print(f"Total records: {len(result['data'])}")
            print("First 3 records:")
            for record in result['data'][:3]:
                print(f"  {record['date']}: Close=₹{record['close_price']}, Volume={record['volume']}")
            break
    
    print("\n" + "="*60 + "\n")
    
    # Example 2: Using the class directly with more control
    print("=== Example 2: Using BulkPriceFetcher class ===")
    
    fetcher = BulkPriceFetcher(max_workers=5, retry_limit=2)
    
    # Get 5 years of data for different symbols
    symbols2 = ['WIPRO.NS', 'BAJFINANCE.NS', 'MARUTI.NS']
    results2 = fetcher.get_last_10_years_data(symbols2, years_back=5)
    
    # Get detailed summary
    summary = fetcher.get_data_summary(results2)
    
    print(f"\n=== Detailed Summary ===")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    print(f"Total records: {summary['total_records']}")
    
    if summary['failed_symbols']:
        print(f"\nFailed symbols:")
        for reason, symbols in summary['failure_reasons'].items():
            print(f"  {reason}: {', '.join(symbols)}")
    
    # Save to CSV (optional)
    csv_file = fetcher.save_to_csv(results2)
    
    # Example: Save to database (if database is available)
    try:
        from config.database import DatabaseConnection
        from src.models.stock import Stock
        
        db = DatabaseConnection()
        connection = db.connect()
        
        if connection:
            stock_model = Stock(db)
            print("\nSaving to database...")
            insertion_results = fetcher.save_to_database(results2, db, stock_model)
            db.close()
        
    except Exception as e:
        print(f"Database save skipped: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Example 3: Fetch data for symbols from database
    print("=== Example 3: Fetch for symbols from database ===")
    
    try:
        from config.database import DatabaseConnection
        from src.models.stock import Stock
        
        db = DatabaseConnection()
        connection = db.connect()
        
        if connection:
            stock_model = Stock(db)
            all_stocks = stock_model.get_all_stocks()
            
            # Get first 10 symbols from database
            db_symbols = [stock['symbol'] for stock in all_stocks[:10]]
            
            print(f"Fetching data for first 10 symbols from database:")
            for symbol in db_symbols:
                print(f"  {symbol}")
            
            results3 = get_historical_data(db_symbols, years_back=1, max_workers=3)
            
            # Show success/failure breakdown
            successful = [s for s, r in results3.items() if r['success']]
            failed = [s for s, r in results3.items() if not r['success']]
            
            print(f"\nResults: {len(successful)} successful, {len(failed)} failed")
            
            db.close()
        else:
            print("Could not connect to database")
            
    except ImportError:
        print("Database modules not available")
    except Exception as e:
        print(f"Database error: {e}")

def fetch_specific_symbols():
    """Function to fetch data for specific symbols"""
    
    # Define your symbols here
    symbols_to_fetch = [
        'TCS.NS', 'RELIANCE.NS', 'INFY.NS', 'WIPRO.NS',
        'HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS',
        'MARUTI.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS'
    ]
    
    print(f"Fetching 10 years of data for {len(symbols_to_fetch)} symbols...")
    
    # Fetch the data
    results = get_historical_data(symbols_to_fetch, years_back=10, max_workers=5)
    
    # Save results to JSON for later use
    json_results = {}
    for symbol, result in results.items():
        json_results[symbol] = {
            'success': result['success'],
            'reason': result['reason'],
            'record_count': len(result['data']) if result['success'] else 0,
            'date_range': result.get('date_range', {})
        }
    
    with open('bulk_fetch_results.json', 'w') as f:
        json.dump(json_results, f, indent=2, default=str)
    
    print("✅ Results summary saved to bulk_fetch_results.json")
    
    return results

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Run examples")
    print("2. Fetch specific symbols")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        example_usage()
    elif choice == "2":
        fetch_specific_symbols()
    else:
        print("Invalid choice. Running examples...")
        example_usage()