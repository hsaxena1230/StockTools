#!/usr/bin/env python3
"""
Query Missing Stock Data
Helper script to view and analyze stocks with missing sector information
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection
from src.models.missing_stock import MissingStock

def query_missing_stocks():
    print("=== Missing Stock Data Analysis ===\n")
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    missing_stock_model = MissingStock(db)
    
    # Get summary statistics
    print("1. Summary Statistics:")
    reason_counts = missing_stock_model.get_missing_count_by_reason()
    
    total_missing = sum(item['count'] for item in reason_counts)
    print(f"   Total stocks with missing data: {total_missing}")
    
    print("\n2. Breakdown by Reason:")
    for item in reason_counts:
        percentage = (item['count'] / total_missing * 100) if total_missing > 0 else 0
        print(f"   • {item['reason']}: {item['count']} stocks ({percentage:.1f}%)")
    
    # Get all missing stocks
    all_missing = missing_stock_model.get_all_missing_stocks()
    
    print(f"\n3. Sample Missing Stocks (showing first 20):")
    for i, stock in enumerate(all_missing[:20], 1):
        print(f"   {i:2d}. {stock['sc_name']}")
        print(f"       Code: {stock['sc_code']} | Symbol: {stock['attempted_symbol']} | Reason: {stock['reason']}")
    
    if len(all_missing) > 20:
        print(f"   ... and {len(all_missing) - 20} more stocks")
    
    # Stocks with specific issues
    print(f"\n4. Stocks with Yahoo Finance Errors:")
    yahoo_errors = [s for s in all_missing if 'Yahoo Finance error' in s['reason']]
    print(f"   Count: {len(yahoo_errors)}")
    for stock in yahoo_errors[:5]:
        print(f"   • {stock['sc_name']} - {stock['reason']}")
    
    print(f"\n5. Stocks without Symbols:")
    no_symbol = [s for s in all_missing if 'Could not generate' in s['reason']]
    print(f"   Count: {len(no_symbol)}")
    for stock in no_symbol[:5]:
        print(f"   • {stock['sc_name']}")
    
    db.close()
    print("\n✅ Query completed!")

if __name__ == "__main__":
    query_missing_stocks()