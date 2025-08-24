#!/usr/bin/env python3
"""
Simple script to run 2-year industry relative strength generation without interactive prompts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator

def main():
    print("=== Generating 2-Year Industry Relative Strength (Non-Interactive) ===\n")
    
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
    calculator = RelativeStrengthCalculator(db, benchmark_symbol='^CRSLDX')
    
    # Create table
    print("\n2. Setting up relative strength table...")
    rs_model.create_table()
    
    # Generate 2-year historical relative strength
    print("\n3. Starting 2-year relative strength generation...")
    print("   Benchmark: Nifty 500 (^CRSLDX)")
    print("   This will take several minutes to complete...")
    
    try:
        results = calculator.generate_industry_relative_strength_historical_2years()
        
        if results['success']:
            print(f"\n✅ 2-Year relative strength generation completed successfully!")
            print(f"\n📊 Final Results:")
            print(f"   🎯 Benchmark: {results['benchmark_symbol']}")
            print(f"   📅 Date range: {results['date_range']}")
            print(f"   🏭 Industries processed: {results['industries_count']}")
            print(f"   📈 Trading days: {results['trading_days']}")
            print(f"   🔢 Total calculations: {results['total_calculations']:,}")
            print(f"   ✅ Successful: {results['successful_calculations']:,}")
            print(f"   ❌ Failed: {results['failed_calculations']:,}")
            print(f"   📊 Success rate: {results['success_rate']}%")
            
            print(f"\n🎉 Your journey charts will now show real historical relative strength data!")
            print(f"   • 30-day RS periods will show actual 30-day relative strength")
            print(f"   • 90-day RS periods will show actual 90-day relative strength") 
            print(f"   • 180-day RS periods will show actual 180-day relative strength")
            print(f"   • All data is calculated relative to Nifty 500 benchmark")
            
        else:
            print(f"\n❌ 2-Year relative strength generation failed!")
            if 'error' in results:
                print(f"   Error: {results['error']}")
                
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
        print(f"\n🔚 Database connection closed.")

if __name__ == '__main__':
    main()