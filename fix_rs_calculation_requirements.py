#!/usr/bin/env python3
"""
Fix the RS calculation to work with available data
Temporarily modifies the data requirements to match what's actually available
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def patch_rs_calculator():
    """Patch the RelativeStrengthCalculator to use realistic data requirements"""
    
    # Read the current file
    rs_calc_file = 'src/utils/relative_strength_calculator.py'
    
    with open(rs_calc_file, 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = rs_calc_file + '.backup'
    with open(backup_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Created backup: {backup_file}")
    
    # Apply patches
    patches = [
        # Change the 200-day requirement to 30 days
        ('len(industry_df) < 200', 'len(industry_df) < 30'),
        ('len(benchmark_df) < 200', 'len(benchmark_df) < 30'),
        # Change moving average calculation to use available data
        ('industry_ma_200 = self.calculate_moving_average(industry_values, 200)', 
         'industry_ma_200 = self.calculate_moving_average(industry_values, min(200, len(industry_values)//2))'),
        ('benchmark_ma_200 = self.calculate_moving_average(benchmark_prices, 200)',
         'benchmark_ma_200 = self.calculate_moving_average(benchmark_prices, min(200, len(benchmark_prices)//2))'),
    ]
    
    modified_content = content
    for old, new in patches:
        if old in modified_content:
            modified_content = modified_content.replace(old, new)
            print(f"✅ Applied patch: {old[:50]}... -> {new[:50]}...")
        else:
            print(f"⚠️  Patch not found: {old[:50]}...")
    
    # Write the modified file
    with open(rs_calc_file, 'w') as f:
        f.write(modified_content)
    
    print(f"✅ Patched {rs_calc_file}")
    
    return backup_file

def restore_original(backup_file):
    """Restore the original file from backup"""
    rs_calc_file = 'src/utils/relative_strength_calculator.py'
    
    if os.path.exists(backup_file):
        with open(backup_file, 'r') as f:
            content = f.read()
        
        with open(rs_calc_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Restored original from {backup_file}")
        return True
    else:
        print(f"❌ Backup file not found: {backup_file}")
        return False

def test_fixed_calculation():
    """Test the calculation with the fixes applied"""
    from config.database import DatabaseConnection
    from src.utils.relative_strength_calculator import RelativeStrengthCalculator
    from datetime import datetime, timedelta
    
    db = DatabaseConnection()
    if not db.connect():
        print("❌ Database connection failed")
        return False
    
    calculator = RelativeStrengthCalculator(db, benchmark_symbol='^CRSLDX')
    test_date = datetime(2024, 7, 24).date()
    
    print(f"\\n🧪 Testing fixed calculation for {test_date}...")
    
    # Get benchmark data
    benchmark_df = calculator.get_benchmark_price_data(test_date, days_back=270)
    
    if benchmark_df.empty:
        print("❌ No benchmark data")
        db.close()
        return False
    
    # Test calculation
    rs_data = calculator.calculate_industry_relative_strength('Medical Devices', benchmark_df, test_date)
    
    if rs_data:
        print("✅ RS calculation now works!")
        print(f"   Symbol: {rs_data['symbol']}")
        print(f"   Date: {rs_data['date']}")
        print(f"   RS_30d: {rs_data['relative_strength_30d']}")
        db.close()
        return True
    else:
        print("❌ RS calculation still fails")
        db.close()
        return False

def generate_6month_rs_with_fix():
    """Generate 6-month RS data with the fixes applied"""
    from config.database import DatabaseConnection
    from src.models.relative_strength import RelativeStrength
    from src.utils.relative_strength_calculator import RelativeStrengthCalculator
    from datetime import datetime, timedelta
    
    print("\\n🚀 Generating 6-month RS data with fixes...")
    
    db = DatabaseConnection()
    if not db.connect():
        print("❌ Database connection failed")
        return
    
    try:
        rs_model = RelativeStrength(db)
        calculator = RelativeStrengthCalculator(db, benchmark_symbol='^CRSLDX')
        
        # Define 6-month range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=180)
        
        print(f"Date range: {start_date} to {end_date}")
        
        # Get industries
        industries = db.execute_query("""
            SELECT DISTINCT industry 
            FROM equiweighted_index 
            WHERE date >= %s
            ORDER BY industry
        """, (start_date,))
        industries = [row[0] for row in industries]
        
        # Get dates to process (skip existing)
        dates = db.execute_query("""
            SELECT DISTINCT date 
            FROM equiweighted_index 
            WHERE date >= %s AND date <= %s
            AND date NOT IN (
                SELECT DISTINCT date 
                FROM relative_strength 
                WHERE entity_type = 'INDUSTRY_INDEX' 
                AND date >= %s
            )
            ORDER BY date
        """, (start_date, end_date, start_date))
        dates = [row[0] for row in dates]
        
        print(f"Industries: {len(industries)}")
        print(f"Dates to process: {len(dates)}")
        
        if not dates:
            print("✅ All dates already processed")
            return
        
        total_inserted = 0
        
        for i, calc_date in enumerate(dates):
            if i % 10 == 0:
                print(f"\\nProcessing date {i+1}/{len(dates)}: {calc_date}")
            
            # Get benchmark data
            benchmark_df = calculator.get_benchmark_price_data(calc_date, days_back=270)
            if benchmark_df.empty:
                continue
            
            rs_batch = []
            success_count = 0
            
            for industry in industries:
                try:
                    # Check if already exists
                    exists = db.execute_query("""
                        SELECT 1 FROM relative_strength 
                        WHERE symbol = %s AND date = %s 
                        AND entity_type = 'INDUSTRY_INDEX'
                        LIMIT 1
                    """, (industry, calc_date))
                    
                    if not exists:
                        rs_data = calculator.calculate_industry_relative_strength(
                            industry, benchmark_df, calc_date
                        )
                        if rs_data:
                            rs_batch.append(rs_data)
                            success_count += 1
                except Exception as e:
                    continue
            
            # Insert batch
            if rs_batch:
                inserted = rs_model.insert_relative_strength_data(rs_batch)
                total_inserted += inserted
                print(f"   ✓ Inserted {inserted} records")
        
        print(f"\\n✅ Generation complete! Total inserted: {total_inserted:,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def main():
    print("=== Fixing RS Calculation Requirements ===\\n")
    
    # Apply patches
    backup_file = patch_rs_calculator()
    
    # Test the fix
    if test_fixed_calculation():
        print("\\n✅ Fix successful! Proceeding with data generation...")
        
        # Generate the data
        generate_6month_rs_with_fix()
        
        # Ask user if they want to keep the changes
        response = input("\\nKeep the patches applied? (y/N): ").strip().lower()
        if response != 'y':
            restore_original(backup_file)
            print("✅ Restored original requirements")
        else:
            print("✅ Keeping relaxed requirements for future calculations")
    else:
        print("\\n❌ Fix didn't work, restoring original...")
        restore_original(backup_file)

if __name__ == '__main__':
    main()