#!/usr/bin/env python3
"""
Create Equal-Weighted Industry Indices
Calculates equal-weighted indices for all distinct industries and stores them in equiweighted_index table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.database import DatabaseConnection
from src.models.equiweighted_index import EquiweightedIndex
from src.utils.index_calculator import IndexCalculator
import argparse

def create_industry_indices():
    """Main function to create industry indices"""
    print("=== Industry Equal-Weighted Index Creator ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Initialize models
    index_model = EquiweightedIndex(db)
    calculator = IndexCalculator(db)
    
    # Create table
    print("\n2. Setting up equiweighted_index table...")
    index_model.create_table()
    
    # Get user preferences
    print("\n3. Configuration:")
    
    # Period selection
    print("   Select time period:")
    print("   1. Last 1 year (365 days)")
    print("   2. Last 2 years (730 days)")
    print("   3. Last 3 years (1095 days)")
    print("   4. Custom period")
    
    period_choice = input("   Enter choice (1-4): ").strip()
    
    if period_choice == "1":
        period_days = 365
    elif period_choice == "2":
        period_days = 730
    elif period_choice == "3":
        period_days = 1095
    elif period_choice == "4":
        try:
            period_days = int(input("   Enter number of days: ").strip())
        except ValueError:
            print("   Invalid input. Using 365 days.")
            period_days = 365
    else:
        print("   Invalid choice. Using 365 days.")
        period_days = 365
    
    # Base value selection
    base_value_input = input(f"   Enter base index value (default 1000): ").strip()
    try:
        base_value = float(base_value_input) if base_value_input else 1000.0
    except ValueError:
        print("   Invalid input. Using 1000.")
        base_value = 1000.0
    
    print(f"\n4. Configuration Summary:")
    print(f"   Period: {period_days} days")
    print(f"   Base value: {base_value}")
    
    # Get preview of industries
    print(f"\n5. Preview of industries to process:")
    industries = index_model.get_industries_with_stocks()
    
    if not industries:
        print("❌ No industries found with sufficient stocks (minimum 3 stocks required)")
        db.close()
        return
    
    print(f"   Found {len(industries)} industries:")
    for i, industry_info in enumerate(industries[:10], 1):
        print(f"   {i:2d}. {industry_info['industry']:<30} ({industry_info['stock_count']} stocks)")
    
    if len(industries) > 10:
        print(f"   ... and {len(industries) - 10} more industries")
    
    # Confirm execution
    proceed = input(f"\nProceed with calculating indices for {len(industries)} industries? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("❌ Operation cancelled")
        db.close()
        return
    
    # Calculate indices
    print(f"\n6. Calculating equal-weighted indices...")
    
    try:
        results = calculator.calculate_all_industry_indices(period_days, base_value)
        
        if results['success']:
            print(f"\n✅ Index calculation completed successfully!")
            
            # Display results
            print(f"\n=== Final Results ===")
            print(f"Industries processed: {results['total_industries']}")
            print(f"Successfully calculated: {len(results['successful_industries'])}")
            print(f"Failed calculations: {len(results['failed_industries'])}")
            print(f"Total data points: {results['total_data_points']}")
            print(f"Period: {results['period_start']} to {results['period_end']}")
            
            # Show sample of successful industries
            if results['successful_industries']:
                print(f"\nSuccessfully processed industries:")
                for industry in results['successful_industries'][:10]:
                    print(f"  ✓ {industry}")
                
                if len(results['successful_industries']) > 10:
                    print(f"  ... and {len(results['successful_industries']) - 10} more")
            
            # Show failed industries if any
            if results['failed_industries']:
                print(f"\nFailed to process:")
                for industry in results['failed_industries']:
                    print(f"  ✗ {industry}")
        
        else:
            print(f"❌ Index calculation failed: {results.get('message', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error during calculation: {str(e)}")
    
    # Show statistics
    print(f"\n7. Database statistics:")
    try:
        stats = calculator.get_index_statistics()
        if stats:
            print(f"   Total industries in database: {stats.get('total_industries', 0)}")
            print(f"   Total data points: {stats.get('total_data_points', 0)}")
            print(f"   Date range: {stats.get('earliest_date', 'N/A')} to {stats.get('latest_date', 'N/A')}")
            print(f"   Average stocks per industry: {stats.get('avg_stocks_per_industry', 0):.1f}")
            
            # Show top performers
            if 'top_performers' in stats:
                print(f"\n   Top performing industries:")
                for i, performer in enumerate(stats['top_performers'], 1):
                    print(f"   {i}. {performer['industry']:<30} {performer['return_pct']:+.2f}%")
    
    except Exception as e:
        print(f"   Error getting statistics: {str(e)}")
    
    db.close()
    print(f"\n✅ Process completed!")

def update_specific_industry():
    """Update index for a specific industry"""
    print("=== Update Specific Industry Index ===\n")
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    # Initialize models
    index_model = EquiweightedIndex(db)
    calculator = IndexCalculator(db)
    
    # Get industries
    industries = index_model.get_industries_with_stocks()
    
    if not industries:
        print("❌ No industries found")
        db.close()
        return
    
    print("Available industries:")
    for i, industry_info in enumerate(industries, 1):
        print(f"{i:2d}. {industry_info['industry']} ({industry_info['stock_count']} stocks)")
    
    try:
        choice = int(input(f"\nEnter industry number (1-{len(industries)}): ").strip())
        
        if 1 <= choice <= len(industries):
            industry = industries[choice - 1]['industry']
            
            period_days = int(input("Enter period in days (default 365): ") or "365")
            base_value = float(input("Enter base value (default 1000): ") or "1000")
            
            success = calculator.update_industry_index(industry, period_days, base_value)
            
            if success:
                print(f"✅ Successfully updated index for {industry}")
            else:
                print(f"❌ Failed to update index for {industry}")
        else:
            print("❌ Invalid choice")
    
    except ValueError:
        print("❌ Invalid input")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    db.close()

def view_index_data():
    """View existing index data"""
    print("=== View Index Data ===\n")
    
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    index_model = EquiweightedIndex(db)
    calculator = IndexCalculator(db)
    
    # Get statistics
    stats = calculator.get_index_statistics()
    
    if not stats:
        print("❌ No index data found")
        db.close()
        return
    
    print("=== Index Statistics ===")
    print(f"Total industries: {stats.get('total_industries', 0)}")
    print(f"Total data points: {stats.get('total_data_points', 0)}")
    print(f"Date range: {stats.get('earliest_date', 'N/A')} to {stats.get('latest_date', 'N/A')}")
    print(f"Average stocks per industry: {stats.get('avg_stocks_per_industry', 0):.1f}")
    
    # Show latest values
    latest_values = index_model.get_all_industries_latest_values()
    
    if latest_values:
        print(f"\n=== Latest Index Values ===")
        for value in latest_values[:20]:  # Show first 20
            print(f"{value['industry']:<30} {value['index_value']:>10.2f} ({value['stock_count']} stocks) [{value['date']}]")
        
        if len(latest_values) > 20:
            print(f"... and {len(latest_values) - 20} more industries")
    
    # Show top performers
    if 'top_performers' in stats:
        print(f"\n=== Top Performing Industries ===")
        for i, performer in enumerate(stats['top_performers'], 1):
            print(f"{i}. {performer['industry']:<30} {performer['return_pct']:+.2f}%")
    
    db.close()

def main():
    parser = argparse.ArgumentParser(description='Industry Equal-Weighted Index Tools')
    parser.add_argument('--action', choices=['create', 'update', 'view'], 
                       help='Action to perform: create indices, update specific industry, or view data')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_industry_indices()
    elif args.action == 'update':
        update_specific_industry()
    elif args.action == 'view':
        view_index_data()
    else:
        # Interactive mode
        print("=== Industry Index Management ===")
        print("1. Create all industry indices")
        print("2. Update specific industry")
        print("3. View existing index data")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            create_industry_indices()
        elif choice == "2":
            update_specific_industry()
        elif choice == "3":
            view_index_data()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()