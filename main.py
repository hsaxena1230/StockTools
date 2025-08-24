#!/usr/bin/env python3
"""
Stock Tools - Indian Stock Data Fetcher
Fetches Indian stock data from Yahoo Finance and stores in PostgreSQL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection
from src.data.stock_fetcher import IndianStockFetcher
from src.models.stock import Stock

def main():
    print("=== Stock Tools - Indian Stock Data Fetcher ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database. Please check your .env file and database settings.")
        return
    
    print("✅ Connected to database successfully")
    
    # Create table if it doesn't exist
    print("\n2. Setting up database table...")
    db.create_table()
    print("✅ Database table ready")
    
    # Initialize models
    stock_model = Stock(db)
    
    # Fetch stock data
    print("\n3. Fetching Indian stock data from NSE CSV and BSE/Yahoo Finance...")
    fetcher = IndianStockFetcher()
    stocks_data = fetcher.fetch_all_stocks_with_deduplication()
    
    if not stocks_data:
        print("❌ No stock data fetched. Exiting.")
        db.close()
        return
    
    # Insert data into database
    print(f"\n4. Inserting {len(stocks_data)} stocks into database...")
    success_count = stock_model.insert_multiple_stocks(stocks_data)
    
    print(f"✅ Successfully inserted/updated {success_count} stocks in the database")
    
    # Display summary
    print("\n=== Summary ===")
    all_stocks = stock_model.get_all_stocks()
    print(f"Total stocks in database: {len(all_stocks)}")
    
    # Show some sample data
    print("\nSample stocks:")
    for i, stock in enumerate(all_stocks[:5]):
        print(f"  {i+1}. {stock['name']} ({stock['symbol']}) - {stock['sector']}")
    
    if len(all_stocks) > 5:
        print(f"  ... and {len(all_stocks) - 5} more")
    
    # Close database connection
    db.close()
    print("\n✅ Process completed successfully!")

if __name__ == "__main__":
    main()