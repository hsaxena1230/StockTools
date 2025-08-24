#!/usr/bin/env python3
"""
Test Daily Calculations
Run this script to test the daily calculations manually before setting up cron
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daily_calculations import main
import argparse

def test_individual_steps():
    """Test individual steps of the daily calculations"""
    from daily_calculations import setup_logging, update_stock_prices, calculate_equiweighted_indices, calculate_momentum, calculate_relative_strength
    from config.database import DatabaseConnection
    
    print("🧪 TESTING INDIVIDUAL CALCULATION STEPS")
    print("=" * 60)
    
    logger = setup_logging()
    
    # Initialize database
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Database connected")
    
    # Test menu
    while True:
        print("\n📋 Test Options:")
        print("1. Test stock price updates")
        print("2. Test equiweighted indices calculation")
        print("3. Test momentum calculation")
        print("4. Test relative strength calculation")
        print("5. Run all steps (full test)")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            print("\n🧪 Testing stock price updates...")
            result = update_stock_prices(db, logger)
            print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}")
            
        elif choice == "2":
            print("\n🧪 Testing equiweighted indices calculation...")
            result = calculate_equiweighted_indices(db, logger)
            print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}")
            
        elif choice == "3":
            print("\n🧪 Testing momentum calculation...")
            result = calculate_momentum(db, logger)
            print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}")
            
        elif choice == "4":
            print("\n🧪 Testing relative strength calculation...")
            result = calculate_relative_strength(db, logger)
            print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}")
            
        elif choice == "5":
            print("\n🧪 Running full daily calculations test...")
            main()
            break
            
        elif choice == "6":
            break
            
        else:
            print("❌ Invalid choice. Please select 1-6.")
    
    db.close()
    print("\n🔚 Testing completed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test daily calculations')
    parser.add_argument('--interactive', action='store_true', help='Run interactive step-by-step tests')
    
    args = parser.parse_args()
    
    if args.interactive:
        test_individual_steps()
    else:
        print("🧪 Running full daily calculations test...")
        main()