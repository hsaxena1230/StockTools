#!/usr/bin/env python3
"""
Calculate and Store Momentum Data
Calculates 30d, 90d, and 180d momentum for stocks, industry indices, and market indices
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from config.database import DatabaseConnection
from src.models.momentum import Momentum
from src.utils.momentum_calculator import MomentumCalculator
import argparse

def calculate_daily_momentum():
    """Calculate momentum for current date"""
    print("=== Daily Momentum Calculation ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    momentum_model = Momentum(db)
    calculator = MomentumCalculator(db)
    
    # Create table
    print("\n2. Setting up momentum table...")
    momentum_model.create_table()
    
    # Calculate momentum
    print("\n3. Calculating momentum...")
    
    calculation_date = datetime.now().date()
    print(f"   Calculation date: {calculation_date}")
    
    try:
        results = calculator.calculate_all_momentum(calculation_date)
        
        if results['success']:
            print(f"\n✅ Momentum calculation completed!")
            
            # Display results
            print(f"\n=== Results Summary ===")
            print(f"Total momentum records: {results['total_records']}")
            print(f"Stocks processed: {results['stocks_processed']} (failed: {results['stocks_failed']})")
            print(f"Industry indices processed: {results['industries_processed']} (failed: {results['industries_failed']})")
            print(f"Market indices processed: {results['market_indices_processed']} (failed: {results['market_indices_failed']})")
            
            # Show top performers
            print(f"\n=== Top 30-Day Momentum Stocks ===")
            top_stocks = momentum_model.get_top_momentum_stocks(period='30d', limit=10, entity_type='STOCK')
            
            for i, stock in enumerate(top_stocks, 1):
                print(f"{i:2d}. {stock['entity_name']:<30} ({stock['symbol']:<12}) {stock['momentum_pct']:+7.2f}%")
            
            # Show top industry indices
            print(f"\n=== Top 30-Day Momentum Industries ===")
            top_industries = momentum_model.get_top_momentum_stocks(period='30d', limit=10, entity_type='INDUSTRY_INDEX')
            
            for i, industry in enumerate(top_industries, 1):
                print(f"{i:2d}. {industry['entity_name']:<40} {industry['momentum_pct']:+7.2f}%")
        
        else:
            print(f"❌ Momentum calculation failed")
    
    except Exception as e:
        print(f"❌ Error during calculation: {str(e)}")
    
    db.close()
    print(f"\n✅ Process completed!")

def update_specific_symbol():
    """Update momentum for a specific symbol"""
    print("=== Update Specific Symbol Momentum ===\n")
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    calculator = MomentumCalculator(db)
    
    # Get symbol from user
    symbol = input("Enter symbol to update (e.g., TCS.NS, ^CRSLDX): ").strip().upper()
    
    if not symbol:
        print("❌ No symbol provided")
        db.close()
        return
    
    # Update momentum
    success = calculator.update_momentum_for_symbol(symbol)
    
    if success:
        print(f"✅ Successfully updated momentum for {symbol}")
        
        # Show updated data
        momentum_model = Momentum(db)
        history = momentum_model.get_momentum_history(symbol, days=5)
        
        if history:
            print(f"\nRecent momentum data for {symbol}:")
            print("Date       | Current Price | 30d    | 90d    | 180d   | Volatility")
            print("-" * 70)
            for record in history:
                print(f"{record['date']} | {record['current_price']:>11.2f} | {record['momentum_30d_pct']:+6.2f}% | {record['momentum_90d_pct']:+6.2f}% | {record['momentum_180d_pct']:+6.2f}% | {record['volatility_30d']:>8.2f}%")
    else:
        print(f"❌ Failed to update momentum for {symbol}")
    
    db.close()

def view_momentum_data():
    """View existing momentum data"""
    print("=== View Momentum Data ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    momentum_model = Momentum(db)
    
    # Get statistics
    stats = momentum_model.get_momentum_statistics()
    
    if not stats:
        print("❌ No momentum data found")
        db.close()
        return
    
    print("=== Momentum Statistics ===")
    for stat in stats:
        print(f"\n{stat['entity_type']}:")
        print(f"  Total records: {stat['total_records']}")
        print(f"  Unique symbols: {stat['unique_symbols']}")
        print(f"  Date range: {stat['earliest_date']} to {stat['latest_date']}")
        print(f"  Average momentum:")
        print(f"    30d: {stat['avg_momentum_30d']:+6.2f}%")
        print(f"    90d: {stat['avg_momentum_90d']:+6.2f}%")
        print(f"    180d: {stat['avg_momentum_180d']:+6.2f}%")
    
    # Show top performers for different periods
    periods = ['30d', '90d', '180d']
    
    for period in periods:
        print(f"\n=== Top {period.upper()} Momentum Stocks ===")
        top_stocks = momentum_model.get_top_momentum_stocks(period=period, limit=10, entity_type='STOCK')
        
        for i, stock in enumerate(top_stocks, 1):
            print(f"{i:2d}. {stock['entity_name']:<25} ({stock['symbol']:<10}) {stock['momentum_pct']:+7.2f}%")
        
        print(f"\n=== Top {period.upper()} Momentum Industries ===")
        top_industries = momentum_model.get_top_momentum_stocks(period=period, limit=5, entity_type='INDUSTRY_INDEX')
        
        for i, industry in enumerate(top_industries, 1):
            print(f"{i:2d}. {industry['symbol']:<25} {industry['momentum_pct']:+7.2f}%")
    
    db.close()

def historical_momentum_calculation():
    """Calculate momentum for historical dates"""
    print("=== Historical Momentum Calculation ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    momentum_model = Momentum(db)
    calculator = MomentumCalculator(db)
    
    # Ensure table exists
    momentum_model.create_table()
    
    # Get date range from user
    try:
        days_back = int(input("Enter number of days back to calculate (default 30): ") or "30")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"\nCalculating momentum for date range: {start_date} to {end_date}")
        
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed_days = 0
        
        while current_date <= end_date:
            print(f"\nProcessing {current_date} ({processed_days + 1}/{total_days})...")
            
            try:
                results = calculator.calculate_all_momentum(current_date)
                
                if results['success']:
                    print(f"  ✓ Calculated {results['total_records']} momentum records")
                else:
                    print(f"  ✗ Failed to calculate momentum")
                    
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
            
            current_date += timedelta(days=1)
            processed_days += 1
        
        print(f"\n✅ Historical momentum calculation completed!")
        print(f"Processed {processed_days} days from {start_date} to {end_date}")
        
    except ValueError:
        print("❌ Invalid input")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    db.close()

def compare_symbols():
    """Compare momentum across multiple symbols"""
    print("=== Compare Symbol Momentum ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    momentum_model = Momentum(db)
    
    # Get symbols from user
    symbols_input = input("Enter symbols to compare (comma-separated, e.g., TCS.NS,INFY.NS,^CRSLDX): ").strip()
    
    if not symbols_input:
        print("❌ No symbols provided")
        db.close()
        return
    
    symbols = [s.strip().upper() for s in symbols_input.split(',')]
    
    print(f"\nComparing momentum for: {', '.join(symbols)}")
    
    # Compare across different periods
    periods = ['30d', '90d', '180d']
    
    for period in periods:
        print(f"\n=== {period.upper()} Momentum Comparison ===")
        comparison = momentum_model.get_momentum_comparison(symbols, period)
        
        if comparison:
            print("Symbol        | Entity Type      | Current Price | Momentum | Volatility")
            print("-" * 75)
            
            for item in comparison:
                momentum_pct = item['momentum_pct'] or 0
                volatility = item['volatility_30d'] or 0
                print(f"{item['symbol']:<12} | {item['entity_type']:<15} | {item['current_price']:>11.2f} | {momentum_pct:+7.2f}% | {volatility:>8.2f}%")
        else:
            print("No data found for comparison")
    
    db.close()

def generate_industry_momentum_2years():
    """Generate 2-year historical momentum for industry indices only"""
    print("=== Generate 2-Year Industry Momentum ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    momentum_model = Momentum(db)
    calculator = MomentumCalculator(db)
    
    # Create table
    print("\n2. Setting up momentum table...")
    momentum_model.create_table()
    
    try:
        print("\n3. Generating 2-year historical momentum for industry indices...")
        results = calculator.generate_industry_momentum_historical_2years()
        
        if results['success']:
            print(f"\n✅ 2-year momentum generation completed!")
            print(f"📊 Final Statistics:")
            print(f"   Date range: {results['date_range']}")
            print(f"   Industries: {results['industries_count']}")
            print(f"   Trading days: {results['trading_days']}")
            print(f"   Total calculations: {results['total_calculations']:,}")
            print(f"   Successful: {results['successful_calculations']:,}")
            print(f"   Failed: {results['failed_calculations']:,}")
            print(f"   Success rate: {results['success_rate']}%")
        else:
            print(f"\n❌ 2-year momentum generation failed!")
            if 'error' in results:
                print(f"Error: {results['error']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    db.close()

def main():
    parser = argparse.ArgumentParser(description='Momentum Calculation Tools')
    parser.add_argument('--action', choices=['calculate', 'update', 'view', 'historical', 'compare', 'industry-2years'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'calculate':
        calculate_daily_momentum()
    elif args.action == 'update':
        update_specific_symbol()
    elif args.action == 'view':
        view_momentum_data()
    elif args.action == 'historical':
        historical_momentum_calculation()
    elif args.action == 'compare':
        compare_symbols()
    elif args.action == 'industry-2years':
        generate_industry_momentum_2years()
    else:
        # Interactive mode
        print("=== Momentum Analysis Tools ===")
        print("1. Calculate daily momentum (current date)")
        print("2. Update specific symbol")
        print("3. View momentum data")
        print("4. Calculate historical momentum")
        print("5. Compare symbols")
        print("6. Generate 2-year industry momentum")
        
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == "1":
            calculate_daily_momentum()
        elif choice == "2":
            update_specific_symbol()
        elif choice == "3":
            view_momentum_data()
        elif choice == "4":
            historical_momentum_calculation()
        elif choice == "5":
            compare_symbols()
        elif choice == "6":
            generate_industry_momentum_2years()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()