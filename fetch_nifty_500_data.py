#!/usr/bin/env python3
"""
Fetch Nifty 500 Historical Data
Fetches last 10 years of Nifty 500 data and stores in stock_prices table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.data.index_fetcher import IndexFetcher

def ensure_index_in_stocks_table(db_connection, symbol: str, name: str) -> int:
    """Ensure the index exists in stocks table and return its ID"""
    stock_model = Stock(db_connection)
    
    # Check if index already exists
    existing_stock = stock_model.get_stock_by_symbol(symbol)
    
    if existing_stock:
        print(f"✅ Index {symbol} already exists in stocks table with ID: {existing_stock['id']}")
        return existing_stock['id']
    
    # Insert the index into stocks table
    stock_data = {
        'symbol': symbol,
        'name': name,
        'sector': 'INDEX',
        'industry': 'Market Index',
        'market_cap': 0  # Indices don't have market cap
    }
    
    if stock_model.insert_stock(stock_data):
        # Get the newly inserted stock
        new_stock = stock_model.get_stock_by_symbol(symbol)
        if new_stock:
            print(f"✅ Inserted {symbol} into stocks table with ID: {new_stock['id']}")
            return new_stock['id']
    
    raise Exception(f"Failed to insert {symbol} into stocks table")

def fetch_and_store_nifty_500(years_back: int = 10):
    """Fetch and store Nifty 500 historical data"""
    print("=== Fetching Nifty 500 Historical Data ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    stock_price_model = StockPrice(db)
    index_fetcher = IndexFetcher()
    
    # Ensure TimescaleDB table exists
    print("\n2. Checking TimescaleDB tables...")
    try:
        stock_price_model.create_timescale_table()
        print("✅ TimescaleDB tables ready")
    except Exception as e:
        print(f"❌ Error with TimescaleDB: {e}")
        db.close()
        return
    
    # Ensure Nifty 500 exists in stocks table
    print("\n3. Ensuring Nifty 500 in stocks table...")
    try:
        nifty_500_id = ensure_index_in_stocks_table(db, '^CRSLDX', 'NIFTY 500 Index')
    except Exception as e:
        print(f"❌ Error: {e}")
        db.close()
        return
    
    # Fetch Nifty 500 data
    print(f"\n4. Fetching {years_back} years of Nifty 500 data from Yahoo Finance...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years_back)
    
    print(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Fetch the data
    nifty_data = index_fetcher.fetch_nifty_500_data(years_back)
    
    if not nifty_data:
        print("❌ No data fetched for Nifty 500")
        db.close()
        return
    
    print(f"✅ Fetched {len(nifty_data)} days of data")
    
    # Add stock_id to each record
    for record in nifty_data:
        record['stock_id'] = nifty_500_id
    
    # Insert into database
    print(f"\n5. Inserting data into stock_prices table...")
    
    inserted_count = stock_price_model.insert_price_data(nifty_data)
    
    if inserted_count > 0:
        print(f"✅ Successfully inserted {inserted_count} records")
    else:
        print("❌ Failed to insert data")
    
    # Show sample data
    print("\n6. Verification - Recent Nifty 500 prices:")
    recent_prices = stock_price_model.get_price_history(
        '^CRSLDX',
        end_date - timedelta(days=10),
        end_date
    )
    
    if recent_prices:
        for price in recent_prices[:5]:
            print(f"   {price['time'].strftime('%Y-%m-%d')}: {price['close_price']}")
    
    # Show summary statistics
    print("\n7. Summary Statistics:")
    
    # Get date range of stored data
    query = """
    SELECT 
        MIN(time) as earliest_date,
        MAX(time) as latest_date,
        COUNT(*) as total_records,
        MIN(close_price) as min_price,
        MAX(close_price) as max_price,
        AVG(close_price) as avg_price
    FROM stock_prices
    WHERE symbol = %s
    """
    
    stats = db.execute_query(query, ('^CRSLDX',))
    
    if stats and stats[0]:
        earliest, latest, total, min_price, max_price, avg_price = stats[0]
        print(f"   Date range: {earliest} to {latest}")
        print(f"   Total records: {total}")
        print(f"   Price range: {min_price} - {max_price}")
        print(f"   Average price: {avg_price:.2f}")
    
    db.close()
    print("\n✅ Nifty 500 data fetch completed!")

def fetch_all_indices():
    """Fetch historical data for all major indices"""
    print("=== Fetching All Major Index Data ===\n")
    
    indices = {
        '^CRSLDX': 'NIFTY 500 Index',
        '^NSEI': 'NIFTY 50 Index',
        '^NSEBANK': 'NIFTY Bank Index',
        '^BSESN': 'BSE SENSEX Index'
    }
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    stock_price_model = StockPrice(db)
    index_fetcher = IndexFetcher()
    
    for symbol, name in indices.items():
        print(f"\nProcessing {name} ({symbol})...")
        
        try:
            # Ensure index exists in stocks table
            stock_id = ensure_index_in_stocks_table(db, symbol, name)
            
            # Fetch data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 10)
            
            data = index_fetcher.fetch_index_data(symbol, start_date, end_date)
            
            if data:
                # Add stock_id
                for record in data:
                    record['stock_id'] = stock_id
                
                # Insert data
                inserted = stock_price_model.insert_price_data(data)
                print(f"✅ Inserted {inserted} records for {name}")
            else:
                print(f"❌ No data fetched for {name}")
                
        except Exception as e:
            print(f"❌ Error processing {name}: {e}")
        
        # Rate limiting
        time.sleep(2)
    
    db.close()
    print("\n✅ All indices data fetch completed!")

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Fetch only Nifty 500 data")
    print("2. Fetch all major indices (Nifty 500, Nifty 50, Bank Nifty, Sensex)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        years = input("Enter number of years of data to fetch (default 10): ").strip()
        years_back = int(years) if years.isdigit() else 10
        fetch_and_store_nifty_500(years_back)
    elif choice == "2":
        fetch_all_indices()
    else:
        print("Invalid choice. Fetching Nifty 500 data...")
        fetch_and_store_nifty_500()