#!/usr/bin/env python3
"""
Generate Relative Strength for Industry Indices - Last 6 Months
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator

def main():
    print("=== Generating 6-Month Industry Relative Strength ===\n")
    
    # Initialize database
    db = DatabaseConnection()
    if not db.connect():
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    try:
        # Initialize models
        rs_model = RelativeStrength(db)
        calculator = RelativeStrengthCalculator(db, benchmark_symbol='^CRSLDX')
        
        # Ensure table exists
        rs_model.create_table()
        
        # Define date range (6 months = ~180 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=180)
        
        print(f"📅 Date range: {start_date} to {end_date}")
        print(f"🎯 Benchmark: ^CRSLDX (Nifty 500)")
        
        # Get all industries
        industries_query = """
        SELECT DISTINCT industry 
        FROM equiweighted_index 
        WHERE date >= %s
        ORDER BY industry
        """
        industries = [row[0] for row in db.execute_query(industries_query, (start_date,))]
        print(f"🏭 Found {len(industries)} industries")
        
        # Get dates that need processing
        dates_query = """
        SELECT DISTINCT ei.date 
        FROM equiweighted_index ei
        WHERE ei.date >= %s AND ei.date <= %s
        AND NOT EXISTS (
            SELECT 1 FROM relative_strength rs 
            WHERE rs.date = ei.date 
            AND rs.entity_type = 'INDUSTRY_INDEX'
            AND rs.symbol IN (
                SELECT DISTINCT industry FROM equiweighted_index
            )
            LIMIT 1
        )
        ORDER BY ei.date
        """
        
        dates_to_process = [row[0] for row in db.execute_query(dates_query, (start_date, end_date))]
        
        # Check what's already done
        existing_query = """
        SELECT COUNT(*), MIN(date), MAX(date)
        FROM relative_strength 
        WHERE entity_type = 'INDUSTRY_INDEX'
        AND date >= %s
        """
        existing = db.execute_query(existing_query, (start_date,))
        if existing and existing[0][0] > 0:
            count, min_date, max_date = existing[0]
            print(f"\n📊 Existing data in range: {count:,} records ({min_date} to {max_date})")
        
        print(f"📋 Dates to process: {len(dates_to_process)}")
        
        if not dates_to_process:
            print("\n✅ All dates in the 6-month range already processed!")
            return
        
        # Process dates
        total_processed = 0
        total_failed = 0
        
        print(f"\n🚀 Processing {len(dates_to_process)} dates...")
        
        for idx, calc_date in enumerate(dates_to_process):
            if idx % 5 == 0:
                progress = (idx / len(dates_to_process)) * 100
                print(f"\n[{progress:.0f}%] Processing {calc_date}...")
            
            # Get benchmark data
            benchmark_df = calculator.get_benchmark_price_data(calc_date, days_back=270)
            
            if benchmark_df.empty:
                print(f"   ⚠️  No benchmark data for {calc_date}")
                total_failed += len(industries)
                continue
            
            rs_batch = []
            date_success = 0
            date_failed = 0
            
            # Calculate RS for each industry
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
                        # Check if we have enough data
                        data_check = db.execute_query("""
                            SELECT COUNT(*) 
                            FROM equiweighted_index 
                            WHERE industry = %s 
                            AND date >= %s AND date <= %s
                        """, (industry, calc_date - timedelta(days=200), calc_date))
                        
                        if data_check and data_check[0][0] >= 30:
                            rs_data = calculator.calculate_industry_relative_strength(
                                industry, benchmark_df, calc_date
                            )
                            
                            if rs_data:
                                rs_batch.append(rs_data)
                                date_success += 1
                            else:
                                date_failed += 1
                        else:
                            date_failed += 1
                    else:
                        date_success += 1
                        
                except Exception as e:
                    date_failed += 1
                    if date_failed <= 3:
                        print(f"      Error: {industry} - {str(e)[:80]}")
            
            # Insert batch
            if rs_batch:
                try:
                    inserted = rs_model.insert_relative_strength_data(rs_batch)
                    print(f"   ✓ Inserted {inserted} records ({date_success} success, {date_failed} failed)")
                    total_processed += inserted
                except Exception as e:
                    print(f"   ❌ Insert error: {e}")
                    total_failed += len(rs_batch)
            elif date_success > 0:
                print(f"   ✓ All {date_success} industries already processed")
            
            total_failed += date_failed
        
        # Final summary
        print(f"\n=== 6-Month Generation Complete ===")
        print(f"✅ New records inserted: {total_processed:,}")
        print(f"❌ Failed calculations: {total_failed:,}")
        
        # Show final state
        final = db.execute_query("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date) as dates,
                COUNT(DISTINCT symbol) as industries,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM relative_strength 
            WHERE entity_type = 'INDUSTRY_INDEX'
            AND date >= %s
        """, (start_date,))
        
        if final:
            total, dates, industries, min_date, max_date = final[0]
            expected = dates * industries
            print(f"\n📊 Final Status (Last 6 Months):")
            print(f"  Total records: {total:,}")
            print(f"  Date range: {min_date} to {max_date}")
            print(f"  Unique dates: {dates}")
            print(f"  Unique industries: {industries}")
            print(f"  Coverage: {total}/{expected} ({total/expected*100:.1f}%)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
        print("\n✅ Done!")

if __name__ == '__main__':
    main()