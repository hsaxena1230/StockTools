#!/usr/bin/env python3
"""
Calculate and Store Relative Strength Data
Calculates 30d, 90d, and 180d relative strength for stocks and industry indices against Nifty 500
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator
import argparse

def calculate_daily_relative_strength():
    """Calculate relative strength for current date"""
    print("=== Daily Relative Strength Calculation ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    rs_model = RelativeStrength(db)
    calculator = RelativeStrengthCalculator(db)
    
    # Create table
    print("\n2. Setting up relative strength table...")
    rs_model.create_table()
    
    # Calculate relative strength
    print("\n3. Calculating relative strength...")
    
    calculation_date = datetime.now().date()
    print(f"   Calculation date: {calculation_date}")
    print(f"   Benchmark: {calculator.benchmark_symbol}")
    
    try:
        results = calculator.calculate_all_relative_strength(calculation_date)
        
        if results['success']:
            print(f"\n✅ Relative strength calculation completed!")
            
            # Display results
            print(f"\n=== Results Summary ===")
            print(f"Total relative strength records: {results['total_records']}")
            print(f"Stocks processed: {results['stocks_processed']} (failed: {results['stocks_failed']})") 
            print(f"Industry indices processed: {results['industries_processed']} (failed: {results['industries_failed']})")
            print(f"Benchmark: {results['benchmark_symbol']}")
            
            # Show top performers
            print(f"\n=== Top 30-Day Relative Strength Stocks ===")
            top_stocks = rs_model.get_top_relative_strength(period='30d', limit=10, entity_type='STOCK')
            
            for i, stock in enumerate(top_stocks, 1):
                rs_value = stock['relative_strength'] or 0
                symbol_return = stock['symbol_return'] or 0
                benchmark_return = stock['benchmark_return'] or 0
                print(f"{i:2d}. {stock['entity_name']:<30} ({stock['symbol']:<12}) RS: {rs_value:+7.4f} | Stock: {symbol_return:+6.2f}% | Benchmark: {benchmark_return:+6.2f}%")
            
            # Show top industry indices
            print(f"\n=== Top 30-Day Relative Strength Industries ===")
            top_industries = rs_model.get_top_relative_strength(period='30d', limit=10, entity_type='INDUSTRY_INDEX')
            
            for i, industry in enumerate(top_industries, 1):
                rs_value = industry['relative_strength'] or 0
                symbol_return = industry['symbol_return'] or 0
                benchmark_return = industry['benchmark_return'] or 0
                print(f"{i:2d}. {industry['entity_name']:<40} RS: {rs_value:+7.2f} | Industry: {symbol_return:+6.2f}% | Benchmark: {benchmark_return:+6.2f}%")
        
        else:
            print(f"❌ Relative strength calculation failed")
    
    except Exception as e:
        print(f"❌ Error during calculation: {str(e)}")
    
    db.close()
    print(f"\n✅ Process completed!")

def update_specific_symbol():
    """Update relative strength for a specific symbol"""
    print("=== Update Specific Symbol Relative Strength ===\n")
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    calculator = RelativeStrengthCalculator(db)
    
    # Get symbol from user
    symbol = input("Enter symbol to update (e.g., TCS.NS, Information Technology): ").strip()
    
    if not symbol:
        print("❌ No symbol provided")
        db.close()
        return
    
    # Update relative strength
    success = calculator.update_relative_strength_for_symbol(symbol)
    
    if success:
        print(f"✅ Successfully updated relative strength for {symbol}")
        
        # Show updated data
        rs_model = RelativeStrength(db)
        history = rs_model.get_relative_strength_history(symbol, days=5)
        
        if history:
            print(f"\nRecent relative strength data for {symbol}:")
            print("Date       | Current Price | Benchmark | 30d RS  | 90d RS  | 180d RS | Symbol 30d | Benchmark 30d")
            print("-" * 95)
            for record in history:
                current_price = record['current_price'] or 0
                benchmark_price = record['benchmark_price'] or 0
                rs_30d = record['relative_strength_30d'] or 0
                rs_90d = record['relative_strength_90d'] or 0
                rs_180d = record['relative_strength_180d'] or 0
                symbol_return = record['symbol_return_30d'] or 0
                benchmark_return = record['benchmark_return_30d'] or 0
                print(f"{record['date']} | {current_price:>11.2f} | {benchmark_price:>9.2f} | {rs_30d:+7.2f} | {rs_90d:+7.2f} | {rs_180d:+7.2f} | {symbol_return:+8.2f}% | {benchmark_return:+11.2f}%")
    else:
        print(f"❌ Failed to update relative strength for {symbol}")
    
    db.close()

def view_relative_strength_data():
    """View existing relative strength data"""
    print("=== View Relative Strength Data ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    rs_model = RelativeStrength(db)
    
    # Get statistics
    stats = rs_model.get_relative_strength_statistics()
    
    if not stats:
        print("❌ No relative strength data found")
        db.close()
        return
    
    print("=== Relative Strength Statistics ===")
    for stat in stats:
        print(f"\n{stat['entity_type']}:")
        print(f"  Total records: {stat['total_records']}")
        print(f"  Unique symbols: {stat['unique_symbols']}")
        print(f"  Date range: {stat['earliest_date']} to {stat['latest_date']}") 
        print(f"  Average relative strength:")
        print(f"    30d: {stat['avg_rs_30d']:+6.2f}")
        print(f"    90d: {stat['avg_rs_90d']:+6.2f}")
        print(f"    180d: {stat['avg_rs_180d']:+6.2f}")
    
    # Show top performers for different periods
    periods = ['30d', '90d', '180d']
    
    for period in periods:
        print(f"\n=== Top {period.upper()} Relative Strength Stocks ===")
        top_stocks = rs_model.get_top_relative_strength(period=period, limit=10, entity_type='STOCK')
        
        for i, stock in enumerate(top_stocks, 1):
            rs_value = stock['relative_strength'] or 0
            symbol_return = stock['symbol_return'] or 0
            benchmark_return = stock['benchmark_return'] or 0
            print(f"{i:2d}. {stock['entity_name']:<25} ({stock['symbol']:<10}) RS: {rs_value:+7.2f}")
        
        print(f"\n=== Top {period.upper()} Relative Strength Industries ===")
        top_industries = rs_model.get_top_relative_strength(period=period, limit=5, entity_type='INDUSTRY_INDEX')
        
        for i, industry in enumerate(top_industries, 1):
            rs_value = industry['relative_strength'] or 0
            print(f"{i:2d}. {industry['symbol']:<25} RS: {rs_value:+7.2f}")
    
    db.close()

def historical_relative_strength_calculation():
    """Calculate relative strength for historical dates"""
    print("=== Historical Relative Strength Calculation ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    rs_model = RelativeStrength(db)
    calculator = RelativeStrengthCalculator(db)
    
    # Ensure table exists
    rs_model.create_table()
    
    # Get date range from user
    try:
        days_back = int(input("Enter number of days back to calculate (default 7): ") or "7")
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"\nCalculating relative strength for date range: {start_date} to {end_date}")
        print(f"Benchmark: {calculator.benchmark_symbol}")
        
        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed_days = 0
        
        while current_date <= end_date:
            print(f"\nProcessing {current_date} ({processed_days + 1}/{total_days})...")
            
            try:
                results = calculator.calculate_all_relative_strength(current_date)
                
                if results['success']:
                    print(f"  ✓ Calculated {results['total_records']} relative strength records")
                else:
                    print(f"  ✗ Failed to calculate relative strength")
                    
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
            
            current_date += timedelta(days=1)
            processed_days += 1
        
        print(f"\n✅ Historical relative strength calculation completed!")
        print(f"Processed {processed_days} days from {start_date} to {end_date}")
        
    except ValueError:
        print("❌ Invalid input")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    db.close()

def compare_symbols():
    """Compare relative strength across multiple symbols"""
    print("=== Compare Symbol Relative Strength ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    rs_model = RelativeStrength(db)
    
    # Get symbols from user
    symbols_input = input("Enter symbols to compare (comma-separated, e.g., TCS.NS,INFY.NS,Information Technology): ").strip()
    
    if not symbols_input:
        print("❌ No symbols provided")
        db.close()
        return
    
    symbols = [s.strip() for s in symbols_input.split(',')]
    
    print(f"\nComparing relative strength for: {', '.join(symbols)}")
    
    # Compare across different periods
    periods = ['30d', '90d', '180d']
    
    for period in periods:
        print(f"\n=== {period.upper()} Relative Strength Comparison ===")
        comparison = rs_model.compare_relative_strength(symbols, period)
        
        if comparison:
            print("Symbol        | Entity Type      | Current Price | RS Value | Symbol Return | Benchmark Return")
            print("-" * 95)
            
            for item in comparison:
                rs_value = item['relative_strength'] or 0
                symbol_return = item['symbol_return'] or 0
                benchmark_return = item['benchmark_return'] or 0
                print(f"{item['symbol']:<12} | {item['entity_type']:<15} | {item['current_price']:>11.2f} | {rs_value:+8.2f} | {symbol_return:+11.2f}% | {benchmark_return:+14.2f}%")
        else:
            print("No data found for comparison")
    
    db.close()

def generate_industry_relative_strength_2years():
    """Generate 2-year historical relative strength for industry indices only"""
    print("=== Generate 2-Year Industry Relative Strength ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    rs_model = RelativeStrength(db)
    calculator = RelativeStrengthCalculator(db)
    
    # Create table
    print("\n2. Setting up relative strength table...")
    rs_model.create_table()
    
    try:
        print("\n3. Generating 2-year historical relative strength for industry indices...")
        results = calculator.generate_industry_relative_strength_historical_2years()
        
        if results['success']:
            print(f"\n✅ 2-year relative strength generation completed!")
            print(f"📊 Final Statistics:")
            print(f"   Benchmark: {results['benchmark_symbol']}")
            print(f"   Date range: {results['date_range']}")
            print(f"   Industries: {results['industries_count']}")
            print(f"   Trading days: {results['trading_days']}")
            print(f"   Total calculations: {results['total_calculations']:,}")
            print(f"   Successful: {results['successful_calculations']:,}")
            print(f"   Failed: {results['failed_calculations']:,}")
            print(f"   Success rate: {results['success_rate']}%")
        else:
            print(f"\n❌ 2-year relative strength generation failed!")
            if 'error' in results:
                print(f"Error: {results['error']}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    db.close()

def generate_industry_relative_strength_6months():
    """Generate 6-month historical relative strength for industry indices"""
    print("=== Generate 6-Month Industry Relative Strength ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    rs_model = RelativeStrength(db)
    calculator = RelativeStrengthCalculator(db)
    
    # Create table
    print("\n2. Setting up relative strength table...")
    rs_model.create_table()
    
    try:
        # Define 6-month range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=180)
        
        print(f"\n3. Generating 6-month relative strength ({start_date} to {end_date})...")
        
        # Get industries
        industries_query = "SELECT DISTINCT industry FROM equiweighted_index WHERE date >= %s ORDER BY industry"
        industries = [row[0] for row in db.execute_query(industries_query, (start_date,))]
        
        # Get dates to process
        dates_query = """
        SELECT DISTINCT date FROM equiweighted_index 
        WHERE date >= %s AND date <= %s
        AND date NOT IN (
            SELECT DISTINCT date FROM relative_strength 
            WHERE entity_type = 'INDUSTRY_INDEX' AND date >= %s
        )
        ORDER BY date
        """
        dates = [row[0] for row in db.execute_query(dates_query, (start_date, end_date, start_date))]
        
        print(f"   Industries: {len(industries)}")
        print(f"   Dates to process: {len(dates)}")
        
        if not dates:
            print("✅ All dates already processed!")
            return
        
        total_processed = 0
        
        for i, calc_date in enumerate(dates):
            if i % 10 == 0:
                print(f"   Processing date {i+1}/{len(dates)}: {calc_date}")
            
            # Get benchmark data
            benchmark_df = calculator.get_benchmark_price_data(calc_date, days_back=270)
            if benchmark_df.empty:
                continue
            
            rs_batch = []
            for industry in industries:
                try:
                    rs_data = calculator.calculate_industry_relative_strength(industry, benchmark_df, calc_date)
                    if rs_data:
                        rs_batch.append(rs_data)
                except:
                    continue
            
            if rs_batch:
                inserted = rs_model.insert_relative_strength_data(rs_batch)
                total_processed += inserted
        
        print(f"\n✅ 6-month relative strength generation completed!")
        print(f"   Total records inserted: {total_processed:,}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    db.close()

def explain_relative_strength():
    """Explain how relative strength is calculated"""
    print("=== Relative Strength Calculation Explanation ===\n")
    
    print("Relative Strength (RS) measures how a stock or industry performs relative to a benchmark.")
    print("In this system, we use Nifty 500 (^CRSLDX) as the benchmark.\n")
    
    print("📊 CALCULATION (Mansfield Relative Strength):")
    print("   RS = (Stock Price / Stock 200-day MA) ÷ (Benchmark Price / Benchmark 200-day MA) × 100\n")
    
    print("📈 INTERPRETATION:")
    print("   • RS > 100: Stock/Industry is OUTPERFORMING relative to moving averages")
    print("   • RS = 100: Stock/Industry is performing IN-LINE with benchmark (both at MA)")
    print("   • RS < 100: Stock/Industry is UNDERPERFORMING relative to moving averages")
    print("   • RS = 120: Stock is 20% stronger relative to its MA than benchmark to its MA")
    print("   • RS = 80: Stock is 20% weaker relative to its MA than benchmark to its MA\n")
    
    print("🔍 EXAMPLE:")
    print("   If TCS = ₹4000, TCS 200-MA = ₹3500, Nifty 500 = 25000, Nifty 200-MA = 24000:")
    print("   Stock Ratio = 4000/3500 = 1.143")
    print("   Benchmark Ratio = 25000/24000 = 1.042") 
    print("   RS = (1.143 ÷ 1.042) × 100 = 109.7")
    print("   This means TCS is performing 9.7% better relative to its MA than Nifty to its MA\n")
    
    print("⏱️  TIME PERIODS:")
    print("   • 30-day RS:  Short-term relative performance")
    print("   • 90-day RS:  Medium-term relative performance") 
    print("   • 180-day RS: Long-term relative performance\n")
    
    print("💡 USE CASES:")
    print("   • Identify stocks/sectors outperforming the market")
    print("   • Compare performance across different time horizons")
    print("   • Screen for momentum and relative strength patterns")
    print("   • Build relative strength-based investment strategies")

def main():
    parser = argparse.ArgumentParser(description='Relative Strength Calculation Tools')
    parser.add_argument('--action', choices=['calculate', 'update', 'view', 'historical', 'compare', 'explain', 'industry-2years', 'industry-6months'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'calculate':
        calculate_daily_relative_strength()
    elif args.action == 'update':
        update_specific_symbol()
    elif args.action == 'view':
        view_relative_strength_data()
    elif args.action == 'historical':
        historical_relative_strength_calculation()
    elif args.action == 'compare':
        compare_symbols()
    elif args.action == 'explain':
        explain_relative_strength()
    elif args.action == 'industry-2years':
        generate_industry_relative_strength_2years()
    elif args.action == 'industry-6months':
        generate_industry_relative_strength_6months()
    else:
        # Interactive mode
        print("=== Relative Strength Analysis Tools ===")
        print("1. Calculate daily relative strength (current date)")
        print("2. Update specific symbol")
        print("3. View relative strength data")
        print("4. Calculate historical relative strength")
        print("5. Compare symbols")
        print("6. Explain relative strength calculation")
        print("7. Generate 2-year industry relative strength")
        print("8. Generate 6-month industry relative strength")
        
        choice = input("Enter choice (1-8): ").strip()
        
        if choice == "1":
            calculate_daily_relative_strength()
        elif choice == "2":
            update_specific_symbol()
        elif choice == "3":
            view_relative_strength_data()
        elif choice == "4":
            historical_relative_strength_calculation()
        elif choice == "5":
            compare_symbols()
        elif choice == "6":
            explain_relative_strength()
        elif choice == "7":
            generate_industry_relative_strength_2years()
        elif choice == "8":
            generate_industry_relative_strength_6months()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()