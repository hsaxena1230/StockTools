#!/usr/bin/env python3
"""
Find BSE Stocks with Missing Sector Information
Analyzes BSE stocks and identifies those without sector data from Yahoo Finance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import yfinance as yf
from config.database import DatabaseConnection
from src.models.missing_stock import MissingStock
from src.data.stock_fetcher import IndianStockFetcher
import time
import re

def is_valid_company_name(sc_name):
    """Check if company name is valid (doesn't start with number)"""
    if not sc_name or sc_name.strip() == '':
        return False
    
    # Remove leading/trailing spaces
    sc_name = sc_name.strip()
    
    # Check if starts with number
    if sc_name[0].isdigit():
        return False
    
    return True

def check_stock_sector(symbol):
    """Check if a stock has sector information on Yahoo Finance"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if it's a mutual fund (we want to exclude these)
        if info.get('quoteType') == 'MUTUALFUND':
            return None, "Mutual Fund"
        
        # Check if sector information exists
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        
        if not sector or sector.strip() == '':
            return None, "No sector information"
        
        return {
            'sector': sector,
            'industry': industry,
            'long_name': info.get('longName', ''),
            'short_name': info.get('shortName', '')
        }, None
        
    except Exception as e:
        return None, f"Yahoo Finance error: {str(e)}"

def find_missing_sector_stocks():
    print("=== Finding BSE Stocks with Missing Sector Information ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    missing_stock_model = MissingStock(db)
    stock_fetcher = IndianStockFetcher()
    
    # Create missing stock table
    print("\n2. Setting up missing_stock_data table...")
    missing_stock_model.create_table()
    
    # Read BSE CSV file
    print("\n3. Reading BSE stocks CSV...")
    try:
        bse_csv_path = os.path.join('src', 'data', 'bse_stocks.CSV')
        df = pd.read_csv(bse_csv_path)
        
        if 'SC_NAME' not in df.columns:
            print("❌ SC_NAME column not found in BSE CSV")
            return
        
        print(f"✅ Found {len(df)} stocks in BSE CSV")
        
    except Exception as e:
        print(f"❌ Error reading BSE CSV: {e}")
        return
    
    # Filter valid company names
    print("\n4. Filtering valid company names...")
    valid_stocks = []
    
    for _, row in df.iterrows():
        sc_name = str(row['SC_NAME']).strip()
        
        if is_valid_company_name(sc_name):
            valid_stocks.append({
                'sc_code': row.get('SC_CODE', ''),
                'sc_name': sc_name,
                'sc_group': row.get('SC_GROUP', '')
            })
    
    print(f"✅ Filtered to {len(valid_stocks)} valid company names")
    print(f"   Excluded {len(df) - len(valid_stocks)} names starting with numbers")
    
    # Check each stock for sector information
    print(f"\n5. Checking sector information for {len(valid_stocks)} stocks...")
    
    missing_stocks = []
    stocks_with_data = 0
    mutual_funds = 0
    errors = 0
    
    for i, stock in enumerate(valid_stocks, 1):
        print(f"Checking {i}/{len(valid_stocks)}: {stock['sc_name']}")
        
        # Convert to Yahoo symbol
        symbol = stock_fetcher._convert_to_yahoo_symbol(stock['sc_name'])
        
        if not symbol:
            missing_stocks.append({
                **stock,
                'attempted_symbol': 'N/A',
                'reason': 'Could not generate Yahoo symbol'
            })
            print(f"  ✗ Could not generate Yahoo symbol")
            continue
        
        # Check sector information
        stock_info, error_reason = check_stock_sector(symbol)
        
        if stock_info:
            stocks_with_data += 1
            print(f"  ✓ Has sector: {stock_info['sector']}")
        elif error_reason == "Mutual Fund":
            mutual_funds += 1
            print(f"  ~ Mutual Fund (skipped)")
        else:
            missing_stocks.append({
                **stock,
                'attempted_symbol': symbol,
                'reason': error_reason
            })
            print(f"  ✗ Missing: {error_reason}")
            
            if "error" in error_reason.lower():
                errors += 1
        
        # Rate limiting
        if i % 10 == 0:
            time.sleep(1)
            print(f"  Progress: {i}/{len(valid_stocks)} stocks checked")
    
    # Store missing stocks in database
    print(f"\n6. Storing {len(missing_stocks)} missing stocks in database...")
    
    stored_count = 0
    for stock in missing_stocks:
        if missing_stock_model.insert_missing_stock(stock):
            stored_count += 1
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total BSE stocks in CSV: {len(df)}")
    print(f"Valid company names (not starting with number): {len(valid_stocks)}")
    print(f"Stocks with sector information: {stocks_with_data}")
    print(f"Mutual funds (excluded): {mutual_funds}")
    print(f"Missing sector information: {len(missing_stocks)}")
    print(f"Yahoo Finance errors: {errors}")
    print(f"Successfully stored in database: {stored_count}")
    
    # Show breakdown by reason
    print("\n=== Missing Data Breakdown ===")
    reason_counts = missing_stock_model.get_missing_count_by_reason()
    for item in reason_counts:
        print(f"{item['reason']}: {item['count']} stocks")
    
    # Show some examples
    print("\n=== Sample Missing Stocks ===")
    sample_missing = missing_stock_model.get_all_missing_stocks()[:10]
    for stock in sample_missing:
        print(f"• {stock['sc_name']} ({stock['attempted_symbol']}) - {stock['reason']}")
    
    if len(sample_missing) > 10:
        print(f"... and {len(sample_missing) - 10} more")
    
    db.close()
    print("\n✅ Analysis completed!")

if __name__ == "__main__":
    find_missing_sector_stocks()