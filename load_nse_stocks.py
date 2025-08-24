#!/usr/bin/env python3
"""
Load NSE Stocks Only - Script to load NSE stocks from CSV into database
Use this when BSE stocks are already in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection
from src.data.stock_fetcher import IndianStockFetcher
from src.models.stock import Stock

def check_existing_companies(db_connection):
    """Check how many companies already exist in database"""
    try:
        query = "SELECT COUNT(*) FROM stocks"
        result = db_connection.execute_query(query)
        return result[0][0] if result else 0
    except:
        return 0

def load_nse_stocks():
    print("=== NSE Stock Loader ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database. Please check your .env file and database settings.")
        return
    
    print("✅ Connected to database successfully")
    
    # Check existing stocks
    existing_count = check_existing_companies(db)
    print(f"\n2. Current stocks in database: {existing_count}")
    
    # Initialize models
    stock_model = Stock(db)
    
    # Fetch NSE stocks only
    print("\n3. Loading NSE stocks from CSV...")
    fetcher = IndianStockFetcher()
    nse_stocks = fetcher.load_nse_stocks_only()
    
    if not nse_stocks:
        print("❌ No NSE stock data found. Exiting.")
        db.close()
        return
    
    # Check for duplicates before inserting
    print(f"\n4. Checking for duplicates and inserting {len(nse_stocks)} NSE stocks...")
    
    inserted_count = 0
    duplicate_count = 0
    error_count = 0
    
    for i, stock_data in enumerate(nse_stocks, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(nse_stocks)}")
        
        # Check if company already exists
        existing_stock = stock_model.get_stock_by_symbol(stock_data['symbol'])
        
        if existing_stock:
            duplicate_count += 1
            print(f"  ⚠️  Duplicate: {stock_data['name']} ({stock_data['symbol']}) - already exists")
        else:
            # Try to insert
            if stock_model.insert_stock(stock_data):
                inserted_count += 1
                print(f"  ✓ Inserted: {stock_data['name']} ({stock_data['symbol']})")
            else:
                error_count += 1
                print(f"  ❌ Error inserting: {stock_data['name']} ({stock_data['symbol']})")
    
    # Final summary
    print("\n=== Summary ===")
    print(f"NSE stocks processed: {len(nse_stocks)}")
    print(f"Successfully inserted: {inserted_count}")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Errors: {error_count}")
    
    # Check final count
    final_count = check_existing_companies(db)
    print(f"\nTotal stocks in database now: {final_count}")
    print(f"Net increase: {final_count - existing_count}")
    
    # Close database connection
    db.close()
    print("\n✅ Process completed!")

if __name__ == "__main__":
    load_nse_stocks()