#!/usr/bin/env python3
"""
Bulk Fetch Stock Data to Database
Fetches historical stock data and stores it directly in stock_prices table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.bulk_price_fetcher import BulkPriceFetcher
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice

def bulk_fetch_and_store(symbols_list=None, years_back=10, max_workers=5):
    """
    Fetch historical data for symbols and store in database
    
    Args:
        symbols_list: List of symbols to fetch. If None, will prompt user
        years_back: Number of years of data to fetch
        max_workers: Number of parallel threads
    """
    print("=== Bulk Fetch and Store to Database ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    stock_model = Stock(db)
    stock_price_model = StockPrice(db)
    
    # Ensure TimescaleDB table exists
    print("\n2. Setting up stock_prices table...")
    try:
        stock_price_model.create_timescale_table()
        print("✅ Stock prices table ready")
    except Exception as e:
        print(f"❌ Error setting up table: {e}")
        db.close()
        return
    
    # Get symbols to fetch
    if not symbols_list:
        print("\n3. Choose symbol source:")
        print("   1. Enter symbols manually")
        print("   2. Use first 20 symbols from database")
        print("   3. Use all symbols from database")
        print("   4. Use predefined list of major stocks")
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            symbols_input = input("Enter symbols (comma-separated): ").strip()
            symbols_list = [s.strip() for s in symbols_input.split(',') if s.strip()]
        
        elif choice == "2":
            all_stocks = stock_model.get_all_stocks()
            symbols_list = [stock['symbol'] for stock in all_stocks[:20]]
            print(f"Using first 20 symbols from database")
        
        elif choice == "3":
            all_stocks = stock_model.get_all_stocks()
            symbols_list = [stock['symbol'] for stock in all_stocks]
            print(f"Using all {len(symbols_list)} symbols from database")
        
        elif choice == "4":
            # Major Indian stocks
            symbols_list = [
                'TCS.NS', 'RELIANCE.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
                'KOTAKBANK.NS', 'BHARTIARTL.NS', 'ITC.NS', 'SBIN.NS', 'LICI.NS',
                'LT.NS', 'HCLTECH.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'MARUTI.NS',
                'SUNPHARMA.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'WIPRO.NS', 'NESTLEIND.NS'
            ]
            print(f"Using predefined list of {len(symbols_list)} major stocks")
        
        else:
            print("Invalid choice. Using major stocks list.")
            symbols_list = ['TCS.NS', 'RELIANCE.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']
    
    if not symbols_list:
        print("❌ No symbols to fetch")
        db.close()
        return
    
    print(f"\n4. Symbols to fetch ({len(symbols_list)}):")
    for i, symbol in enumerate(symbols_list, 1):
        print(f"   {i:2d}. {symbol}")
    
    # Confirm before proceeding
    proceed = input(f"\nProceed with fetching {years_back} years of data? (y/n): ").strip().lower()
    if proceed != 'y':
        print("❌ Operation cancelled")
        db.close()
        return
    
    # Initialize bulk fetcher
    print(f"\n5. Fetching {years_back} years of historical data...")
    fetcher = BulkPriceFetcher(max_workers=max_workers, retry_limit=3)
    
    # Fetch data
    results = fetcher.get_last_10_years_data(symbols_list, years_back)
    
    # Store in database
    print(f"\n6. Storing data in stock_prices table...")
    insertion_results = fetcher.save_to_database(results, db, stock_model)
    
    # Final summary
    print(f"\n=== Final Summary ===")
    
    fetch_summary = fetcher.get_data_summary(results)
    print(f"Data Fetching:")
    print(f"  Total symbols: {fetch_summary['total_symbols']}")
    print(f"  Successful fetches: {fetch_summary['successful_count']}")
    print(f"  Failed fetches: {fetch_summary['failed_count']}")
    print(f"  Total records fetched: {fetch_summary['total_records']}")
    
    insert_successful = sum(1 for r in insertion_results.values() if r['success'])
    total_inserted = sum(r['inserted'] for r in insertion_results.values() if r['success'])
    
    print(f"\nDatabase Insertion:")
    print(f"  Successful inserts: {insert_successful}/{len(insertion_results)}")
    print(f"  Total records inserted: {total_inserted}")
    
    # Show failed insertions
    failed_inserts = {k: v for k, v in insertion_results.items() if not v['success']}
    if failed_inserts:
        print(f"\nFailed Insertions:")
        for symbol, result in failed_inserts.items():
            print(f"  ✗ {symbol}: {result['reason']}")
    
    # Show some sample data
    print(f"\n=== Sample Data Verification ===")
    for symbol in symbols_list[:3]:
        if insertion_results.get(symbol, {}).get('success'):
            stock = next((s for s in stock_model.get_all_stocks() if s['symbol'] == symbol), None)
            if stock:
                recent_prices = stock_price_model.get_price_history(
                    symbol, 
                    stock_price_model.get_latest_price_date(stock['id']) - 
                    __import__('datetime').timedelta(days=7),
                    stock_price_model.get_latest_price_date(stock['id'])
                )
                
                if recent_prices:
                    print(f"\nRecent prices for {symbol}:")
                    for price in recent_prices[:3]:
                        print(f"  {price['time'].strftime('%Y-%m-%d')}: ₹{price['close_price']}")
                break
    
    db.close()
    print("\n✅ Bulk fetch and store completed!")

def fetch_missing_stocks():
    """Fetch data only for stocks without any price data"""
    print("=== Fetching Data for Stocks Without Prices ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    stock_model = Stock(db)
    stock_price_model = StockPrice(db)
    
    # Find stocks without price data
    missing_stocks = stock_price_model.get_missing_data_stocks(days_back=365)  # No data in last year
    
    if not missing_stocks:
        print("✅ All stocks have recent price data")
        db.close()
        return
    
    print(f"Found {len(missing_stocks)} stocks without recent price data:")
    for stock in missing_stocks[:10]:
        print(f"  • {stock['symbol']} - {stock['name']}")
    
    if len(missing_stocks) > 10:
        print(f"  ... and {len(missing_stocks) - 10} more")
    
    # Fetch data for these stocks
    symbols_to_fetch = [stock['symbol'] for stock in missing_stocks]
    
    print(f"\nFetching 10 years of data for {len(symbols_to_fetch)} stocks...")
    
    fetcher = BulkPriceFetcher(max_workers=5)
    results = fetcher.get_last_10_years_data(symbols_to_fetch, years_back=10)
    
    # Store in database
    insertion_results = fetcher.save_to_database(results, db, stock_model)
    
    print(f"\n✅ Completed fetching data for missing stocks")
    
    db.close()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Bulk fetch for specific symbols")
    print("2. Fetch data for stocks without prices")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        bulk_fetch_and_store()
    elif choice == "2":
        fetch_missing_stocks()
    else:
        print("Invalid choice. Running bulk fetch...")
        bulk_fetch_and_store()