#!/usr/bin/env python3
"""
Quick Test for Daily Calculations (Non-Interactive)
Tests all the daily calculation components without actually running the full process
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required imports work"""
    print("🧪 Testing imports...")
    
    try:
        from config.database import DatabaseConnection
        from src.models.stock import Stock
        from src.models.stock_price import StockPrice
        from src.models.equiweighted_index import EquiweightedIndex
        from src.models.momentum import Momentum
        from src.models.relative_strength import RelativeStrength
        from src.data.price_fetcher import PriceFetcher
        from src.data.index_fetcher import IndexFetcher
        from src.utils.momentum_calculator import MomentumCalculator
        from src.utils.relative_strength_calculator import RelativeStrengthCalculator
        from src.utils.index_calculator import IndexCalculator
        
        print("✅ All imports successful")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("🧪 Testing database connection...")
    
    try:
        from config.database import DatabaseConnection
        
        db = DatabaseConnection()
        connection = db.connect()
        
        if connection:
            print("✅ Database connection successful")
            db.close()
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_initializations():
    """Test that all classes can be initialized"""
    print("🧪 Testing class initializations...")
    
    try:
        from config.database import DatabaseConnection
        from src.models.stock import Stock
        from src.models.stock_price import StockPrice
        from src.models.equiweighted_index import EquiweightedIndex
        from src.models.momentum import Momentum
        from src.models.relative_strength import RelativeStrength
        from src.data.price_fetcher import PriceFetcher
        from src.data.index_fetcher import IndexFetcher
        from src.utils.momentum_calculator import MomentumCalculator
        from src.utils.relative_strength_calculator import RelativeStrengthCalculator
        from src.utils.index_calculator import IndexCalculator
        
        db = DatabaseConnection()
        connection = db.connect()
        
        if not connection:
            print("❌ Cannot test initializations without database")
            return False
        
        # Test models (require database)
        stock_model = Stock(db)
        stock_price_model = StockPrice(db)
        index_model = EquiweightedIndex(db)
        momentum_model = Momentum(db)
        rs_model = RelativeStrength(db)
        
        # Test fetchers (no database required)
        price_fetcher = PriceFetcher()
        index_fetcher = IndexFetcher()
        
        # Test calculators (require database)
        momentum_calculator = MomentumCalculator(db)
        rs_calculator = RelativeStrengthCalculator(db)
        index_calculator = IndexCalculator(db)
        
        print("✅ All class initializations successful")
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_critical_methods():
    """Test that critical methods exist"""
    print("🧪 Testing critical method availability...")
    
    try:
        from config.database import DatabaseConnection
        from src.data.price_fetcher import PriceFetcher
        from src.data.index_fetcher import IndexFetcher
        from src.utils.momentum_calculator import MomentumCalculator
        from src.utils.relative_strength_calculator import RelativeStrengthCalculator
        from src.utils.index_calculator import IndexCalculator
        
        db = DatabaseConnection()
        connection = db.connect()
        
        if not connection:
            print("❌ Cannot test methods without database")
            return False
        
        # Test fetcher methods
        price_fetcher = PriceFetcher()
        if not hasattr(price_fetcher, 'fetch_latest_prices'):
            print("❌ PriceFetcher missing fetch_latest_prices method")
            return False
        
        index_fetcher = IndexFetcher()
        if not hasattr(index_fetcher, 'fetch_latest_index_price'):
            print("❌ IndexFetcher missing fetch_latest_index_price method")
            return False
        
        # Test calculator methods
        momentum_calculator = MomentumCalculator(db)
        if not hasattr(momentum_calculator, 'calculate_all_momentum'):
            print("❌ MomentumCalculator missing calculate_all_momentum method")
            return False
        
        rs_calculator = RelativeStrengthCalculator(db)
        if not hasattr(rs_calculator, 'calculate_all_relative_strength'):
            print("❌ RelativeStrengthCalculator missing calculate_all_relative_strength method")
            return False
        
        index_calculator = IndexCalculator(db)
        if not hasattr(index_calculator, 'calculate_all_industry_indices'):
            print("❌ IndexCalculator missing calculate_all_industry_indices method")
            return False
        
        print("✅ All critical methods are available")
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Method test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 QUICK DAILY CALCULATIONS COMPATIBILITY TEST")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Database Connection Test", test_database_connection),
        ("Class Initialization Test", test_initializations),
        ("Critical Methods Test", test_critical_methods)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        print("-" * (len(test_name) + 5))
        results[test_name] = test_func()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Daily calculations script should work correctly")
        print("✅ You can safely run: python3 daily_calculations.py")
        print("✅ You can safely setup cron: ./setup_cron.sh")
    else:
        print("\n⚠️ SOME TESTS FAILED!")
        print("❌ Fix the failing components before running daily calculations")
        print("❌ Check import paths and database configuration")
    
    print("=" * 60)

if __name__ == '__main__':
    main()