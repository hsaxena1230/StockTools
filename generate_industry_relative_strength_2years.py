#!/usr/bin/env python3
"""
Generate 2-Year Historical Relative Strength for Industry Indices
Creates relative strength data for all industry indices for the last 2 years
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator
import argparse

def main():
    parser = argparse.ArgumentParser(description='Generate 2-year historical relative strength for industry indices')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--benchmark', type=str, default='^CRSLDX', help='Benchmark symbol (default: ^CRSLDX)')
    parser.add_argument('--check-existing', action='store_true', help='Check existing relative strength data first')
    
    args = parser.parse_args()
    
    print("=== Industry Relative Strength 2-Year Historical Generation ===\n")
    
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
    calculator = RelativeStrengthCalculator(db, benchmark_symbol=args.benchmark)
    
    # Create table if needed
    print("\n2. Setting up relative strength table...")
    rs_model.create_table()
    
    # Parse end date
    end_date = datetime.now().date()
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid end date format. Use YYYY-MM-DD")
            return
    
    print(f"   Benchmark symbol: {args.benchmark}")
    print(f"   End date: {end_date}")
    print(f"   Start date: {end_date - timedelta(days=730)}")
    
    # Check existing data if requested
    if args.check_existing:
        print(f"\n3. Checking existing relative strength data...")
        start_date = end_date - timedelta(days=730)
        
        existing_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT date) as unique_dates,
            COUNT(DISTINCT symbol) as unique_industries,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM relative_strength 
        WHERE entity_type = 'INDUSTRY_INDEX'
        AND date >= %s AND date <= %s
        """
        
        result = db.execute_query(existing_query, (start_date, end_date))
        if result:
            total, dates, industries, min_date, max_date = result[0]
            print(f"   Existing records: {total:,}")
            print(f"   Date range: {min_date} to {max_date}")
            print(f"   Unique dates: {dates}")
            print(f"   Unique industries: {industries}")
            
            if total > 0:
                response = input(f"\nFound {total:,} existing records. Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Operation cancelled.")
                    return
    
    # Generate historical relative strength
    print(f"\n4. Generating 2-year historical relative strength...")
    print("   This will take several minutes to complete...")
    
    try:
        results = calculator.generate_industry_relative_strength_historical_2years(end_date)
        
        if results['success']:
            print(f"\n✅ Historical relative strength generation completed!")
            print(f"📊 Summary:")
            print(f"   Benchmark: {results['benchmark_symbol']}")
            print(f"   Date range: {results['date_range']}")
            print(f"   Industries: {results['industries_count']}")
            print(f"   Trading days: {results['trading_days']}")
            print(f"   Total calculations: {results['total_calculations']:,}")
            print(f"   Successful: {results['successful_calculations']:,}")
            print(f"   Failed: {results['failed_calculations']:,}")
            print(f"   Success rate: {results['success_rate']}%")
            
            # Verify final data
            verify_query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT date) as unique_dates,
                COUNT(DISTINCT symbol) as unique_industries
            FROM relative_strength 
            WHERE entity_type = 'INDUSTRY_INDEX'
            AND date >= %s AND date <= %s
            """
            
            verify_result = db.execute_query(verify_query, (end_date - timedelta(days=730), end_date))
            if verify_result:
                total, dates, industries = verify_result[0]
                print(f"\n📈 Final database state:")
                print(f"   Total relative strength records: {total:,}")
                print(f"   Unique dates: {dates}")
                print(f"   Unique industries: {industries}")
        else:
            print(f"\n❌ Historical relative strength generation failed!")
            print(f"Error: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error during relative strength generation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == '__main__':
    main()