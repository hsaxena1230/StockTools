#!/usr/bin/env python3
"""
Fetch Historical Stock Prices
Fetches last 10 years of closing prices for all stocks and stores in TimescaleDB
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.data.price_fetcher import PriceFetcher
import psycopg2.extras

def fetch_historical_prices(years_back=10, batch_size=50):
    print(f"=== Fetching {years_back} Years of Historical Stock Prices ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database.")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    stock_model = Stock(db)
    stock_price_model = StockPrice(db)
    price_fetcher = PriceFetcher()
    
    # Create TimescaleDB table
    print("\n2. Setting up TimescaleDB tables...")
    try:
        stock_price_model.create_timescale_table()
        print("✅ TimescaleDB tables ready")
    except Exception as e:
        print(f"❌ Error setting up TimescaleDB: {e}")
        db.close()
        return
    
    # Get all stocks
    print("\n3. Fetching stock list from database...")
    all_stocks = stock_model.get_all_stocks()
    
    if not all_stocks:
        print("❌ No stocks found in database. Please run main.py first.")
        db.close()
        return
    
    print(f"✅ Found {len(all_stocks)} stocks")
    
    # Set date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years_back)
    
    print(f"\n4. Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Process stocks in batches
    print(f"\n5. Fetching historical prices (batch size: {batch_size})...")
    
    total_records = 0
    successful_stocks = 0
    failed_stocks = 0
    
    for i in range(0, len(all_stocks), batch_size):
        batch = all_stocks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(all_stocks) + batch_size - 1) // batch_size
        
        print(f"\n--- Batch {batch_num}/{total_batches} ---")
        
        # Fetch prices for batch
        batch_data = price_fetcher.fetch_batch_historical_prices(batch, start_date, end_date)
        
        # Insert data for each stock
        for stock_id, price_data in batch_data.items():
            if price_data:
                inserted = stock_price_model.insert_price_data(price_data)
                if inserted > 0:
                    total_records += inserted
                    successful_stocks += 1
                else:
                    failed_stocks += 1
            else:
                failed_stocks += 1
        
        print(f"Batch {batch_num} complete. Total records so far: {total_records}")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total stocks processed: {len(all_stocks)}")
    print(f"Successful: {successful_stocks}")
    print(f"Failed: {failed_stocks}")
    print(f"Total price records inserted: {total_records}")
    print(f"Average records per stock: {total_records // successful_stocks if successful_stocks > 0 else 0}")
    
    # Show sample data
    print("\nSample data verification:")
    sample_stock = all_stocks[0]
    sample_prices = stock_price_model.get_price_history(
        sample_stock['symbol'],
        end_date - timedelta(days=30),
        end_date
    )
    
    if sample_prices:
        print(f"\nLast 5 prices for {sample_stock['symbol']}:")
        for price in sample_prices[:5]:
            print(f"  {price['time'].strftime('%Y-%m-%d')}: ₹{price['close_price']}")
    
    # Close connection
    db.close()
    print("\n✅ Historical price fetch completed!")

if __name__ == "__main__":
    # You can customize these parameters
    fetch_historical_prices(years_back=10, batch_size=50)