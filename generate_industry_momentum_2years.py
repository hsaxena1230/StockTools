#!/usr/bin/env python3
"""
Generate 2-Year Historical Momentum for Industry Indices
Creates momentum data for all industry indices for the last 2 years
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from config.database import DatabaseConnection
from src.models.momentum import Momentum
from src.utils.momentum_calculator import MomentumCalculator
import argparse

def main():
    parser = argparse.ArgumentParser(description='Generate 2-year historical momentum for industry indices')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--check-existing', action='store_true', help='Check existing momentum data first')
    
    args = parser.parse_args()
    
    print("=== Industry Momentum 2-Year Historical Generation ===\n")
    
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
    
    # Create table if needed
    print("\n2. Setting up momentum table...")
    momentum_model.create_table()
    
    # Parse end date
    end_date = datetime.now().date()
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print("❌ Invalid end date format. Use YYYY-MM-DD")
            return
    
    # Check existing data if requested
    if args.check_existing:
        print(f"\n3. Checking existing momentum data...")
        start_date = end_date - timedelta(days=730)
        
        existing_query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT date) as unique_dates,
            COUNT(DISTINCT symbol) as unique_industries,
            MIN(date) as min_date,
            MAX(date) as max_date
        FROM momentum 
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
    
    # Generate historical momentum
    print(f"\n4. Generating 2-year historical momentum...")
    print(f"   End date: {end_date}")
    print(f"   Start date: {end_date - timedelta(days=730)}")
    
    try:
        results = calculator.generate_industry_momentum_historical_2years(end_date)
        
        if results['success']:
            print(f"\n✅ Historical momentum generation completed!")
            print(f"📊 Summary:")
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
            FROM momentum 
            WHERE entity_type = 'INDUSTRY_INDEX'
            AND date >= %s AND date <= %s
            """
            
            verify_result = db.execute_query(verify_query, (end_date - timedelta(days=730), end_date))
            if verify_result:
                total, dates, industries = verify_result[0]
                print(f"\n📈 Final database state:")
                print(f"   Total momentum records: {total:,}")
                print(f"   Unique dates: {dates}")
                print(f"   Unique industries: {industries}")
        else:
            print(f"\n❌ Historical momentum generation failed!")
            print(f"Error: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error during momentum generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()