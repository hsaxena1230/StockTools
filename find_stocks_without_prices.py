#!/usr/bin/env python3
"""
Find Stocks Without Price Data
Identifies stocks in the database for which we can't fetch price data from Yahoo Finance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.stock import Stock
import time

def check_stock_price_availability(symbol):
    """Check if price data is available for a stock symbol"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Try to fetch last 5 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            return False, "No historical data available"
        
        # Check if we have valid close prices
        valid_closes = df['Close'].dropna()
        if len(valid_closes) == 0:
            return False, "No valid closing prices"
        
        return True, f"Data available - Latest: {df.index[-1].strftime('%Y-%m-%d')}"
        
    except Exception as e:
        return False, f"Yahoo Finance error: {str(e)}"

def find_stocks_without_prices():
    print("=== Finding Stocks Without Price Data ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Get all stocks
    stock_model = Stock(db)
    all_stocks = stock_model.get_all_stocks()
    
    if not all_stocks:
        print("❌ No stocks found in database")
        return
    
    print(f"✅ Found {len(all_stocks)} stocks in database")
    
    # Check each stock for price data availability
    print(f"\n2. Checking price data availability for {len(all_stocks)} stocks...")
    
    stocks_with_data = []
    stocks_without_data = []
    
    for i, stock in enumerate(all_stocks, 1):
        symbol = stock['symbol']
        name = stock['name']
        
        print(f"Checking {i}/{len(all_stocks)}: {symbol} - {name}")
        
        has_data, reason = check_stock_price_availability(symbol)
        
        if has_data:
            stocks_with_data.append(stock)
            print(f"  ✓ {reason}")
        else:
            stocks_without_data.append({
                **stock,
                'reason': reason
            })
            print(f"  ✗ {reason}")
        
        # Rate limiting
        if i % 10 == 0:
            time.sleep(1)
            print(f"  Progress: {i}/{len(all_stocks)} stocks checked")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total stocks checked: {len(all_stocks)}")
    print(f"Stocks with price data: {len(stocks_with_data)}")
    print(f"Stocks without price data: {len(stocks_without_data)}")
    print(f"Success rate: {(len(stocks_with_data) / len(all_stocks) * 100):.1f}%")
    
    # Detailed breakdown of issues
    print("\n=== Breakdown by Issue Type ===")
    issue_counts = {}
    for stock in stocks_without_data:
        reason = stock['reason']
        issue_counts[reason] = issue_counts.get(reason, 0) + 1
    
    for reason, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{reason}: {count} stocks")
    
    # Show all stocks without data
    print(f"\n=== All Stocks Without Price Data ({len(stocks_without_data)}) ===")
    
    for i, stock in enumerate(stocks_without_data, 1):
        print(f"{i:3d}. {stock['symbol']:15s} - {stock['name']}")
        print(f"     Reason: {stock['reason']}")
        print(f"     Sector: {stock.get('sector', 'N/A')} | Industry: {stock.get('industry', 'N/A')}")
        print()
    
    # Create SQL query to show these stocks
    print("=== SQL Query to View These Stocks ===")
    if stocks_without_data:
        symbols = [f"'{stock['symbol']}'" for stock in stocks_without_data]
        symbols_str = ', '.join(symbols)
        
        query = f"""
-- Stocks without price data from Yahoo Finance
SELECT symbol, name, sector, industry
FROM stocks
WHERE symbol IN ({symbols_str})
ORDER BY symbol;
"""
        print(query)
    
    # Save results to file
    print("\n=== Saving Results ===")
    with open('stocks_without_price_data.txt', 'w') as f:
        f.write("Stocks Without Price Data from Yahoo Finance\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total stocks checked: {len(all_stocks)}\n")
        f.write(f"Stocks without price data: {len(stocks_without_data)}\n")
        f.write(f"Success rate: {(len(stocks_with_data) / len(all_stocks) * 100):.1f}%\n\n")
        
        f.write("Issue Breakdown:\n")
        for reason, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {reason}: {count} stocks\n")
        
        f.write("\nDetailed List:\n")
        f.write("-" * 30 + "\n")
        
        for i, stock in enumerate(stocks_without_data, 1):
            f.write(f"{i:3d}. {stock['symbol']} - {stock['name']}\n")
            f.write(f"     Reason: {stock['reason']}\n")
            f.write(f"     Sector: {stock.get('sector', 'N/A')} | Industry: {stock.get('industry', 'N/A')}\n\n")
    
    print("✅ Results saved to 'stocks_without_price_data.txt'")
    
    db.close()
    print("\n✅ Analysis completed!")

if __name__ == "__main__":
    find_stocks_without_prices()