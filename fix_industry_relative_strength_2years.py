#!/usr/bin/env python3
"""
Fixed script to generate 2-year industry relative strength
Handles edge cases and provides better error reporting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator
import pandas as pd
import traceback

def calculate_rs_for_date_batch(calculator, industries, calc_date, benchmark_df, db):
    """Calculate RS for all industries on a specific date"""
    rs_batch = []
    success_count = 0
    failed_count = 0
    
    for industry in industries:
        try:
            # First check if we have enough data for this industry
            check_query = """
            SELECT COUNT(*) 
            FROM equiweighted_index 
            WHERE industry = %s 
            AND date >= %s AND date <= %s
            """
            
            days_back = 270
            start_check = calc_date - timedelta(days=days_back)
            result = db.execute_query(check_query, (industry, start_check, calc_date))
            
            if result and result[0][0] >= 30:  # Need at least 30 days of data
                # Check if already calculated
                exists_query = """
                SELECT 1 FROM relative_strength 
                WHERE symbol = %s AND date = %s 
                AND entity_type = 'INDUSTRY_INDEX'
                LIMIT 1
                """
                exists = db.execute_query(exists_query, (industry, calc_date))
                
                if not exists:
                    # Calculate RS
                    rs_data = calculator.calculate_industry_relative_strength(
                        industry, benchmark_df, calc_date
                    )
                    
                    if rs_data:
                        rs_batch.append(rs_data)
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    success_count += 1  # Already exists
            else:
                failed_count += 1  # Not enough data
                
        except Exception as e:
            failed_count += 1
            if failed_count <= 3:
                print(f"      Error for {industry}: {str(e)[:100]}")
    
    return rs_batch, success_count, failed_count

def main():
    print("=== Fixed 2-Year Industry Relative Strength Generation ===\n")
    
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
        
        # Define date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=730)
        
        print(f"Date range: {start_date} to {end_date}")
        print(f"Benchmark: ^CRSLDX (Nifty 500)")
        
        # Get all industries
        industries_query = """
        SELECT DISTINCT industry 
        FROM equiweighted_index 
        ORDER BY industry
        """
        industries = [row[0] for row in db.execute_query(industries_query)]
        print(f"Found {len(industries)} industries")
        
        # Get all dates that need processing
        dates_query = """
        SELECT DISTINCT ei.date 
        FROM equiweighted_index ei
        WHERE ei.date >= %s AND ei.date <= %s
        AND NOT EXISTS (
            SELECT 1 FROM relative_strength rs 
            WHERE rs.date = ei.date 
            AND rs.entity_type = 'INDUSTRY_INDEX'
            LIMIT 1
        )
        ORDER BY ei.date
        """
        
        dates_to_process = [row[0] for row in db.execute_query(dates_query, (start_date, end_date))]
        print(f"Dates to process: {len(dates_to_process)}")
        
        if not dates_to_process:
            print("\n✅ All dates already processed!")
            
            # Show summary
            summary = db.execute_query("""
                SELECT COUNT(*), MIN(date), MAX(date)
                FROM relative_strength 
                WHERE entity_type = 'INDUSTRY_INDEX'
                AND date >= %s
            """, (start_date,))
            
            if summary:
                count, min_date, max_date = summary[0]
                print(f"\nCurrent status:")
                print(f"  Total records: {count:,}")
                print(f"  Date range: {min_date} to {max_date}")
            return
        
        # Process dates in batches
        total_processed = 0
        total_failed = 0
        
        print(f"\nProcessing {len(dates_to_process)} dates...")
        
        for idx, calc_date in enumerate(dates_to_process):
            if idx % 10 == 0:
                print(f"\n[{idx+1}/{len(dates_to_process)}] Processing {calc_date}...")
            
            # Get benchmark data
            benchmark_df = calculator.get_benchmark_price_data(calc_date, days_back=270)
            
            if benchmark_df.empty:
                print(f"   ⚠️  No benchmark data for {calc_date}, skipping")
                total_failed += len(industries)
                continue
            
            # Calculate RS for all industries on this date
            rs_batch, success, failed = calculate_rs_for_date_batch(
                calculator, industries, calc_date, benchmark_df, db
            )
            
            # Insert batch
            if rs_batch:
                try:
                    inserted = rs_model.insert_relative_strength_data(rs_batch)
                    print(f"   ✓ Inserted {inserted} records (success: {success}, failed: {failed})")
                    total_processed += inserted
                except Exception as e:
                    print(f"   ❌ Insert error: {e}")
                    total_failed += len(rs_batch)
            else:
                if success > 0:
                    print(f"   ✓ All {success} industries already processed")
                else:
                    print(f"   ⚠️  No new records (failed: {failed})")
            
            total_failed += failed
        
        # Final summary
        print(f"\n=== Generation Complete ===")
        print(f"Total new records inserted: {total_processed:,}")
        print(f"Total failures: {total_failed:,}")
        
        # Show final state
        final_summary = db.execute_query("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT date) as dates,
                COUNT(DISTINCT symbol) as industries
            FROM relative_strength 
            WHERE entity_type = 'INDUSTRY_INDEX'
            AND date >= %s
        """, (start_date,))
        
        if final_summary:
            total, dates, industries = final_summary[0]
            expected = dates * industries
            print(f"\nFinal database state:")
            print(f"  Total records: {total:,}")
            print(f"  Unique dates: {dates}")
            print(f"  Unique industries: {industries}")
            print(f"  Coverage: {total}/{expected} ({total/expected*100:.1f}%)")
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    
    finally:
        db.close()
        print("\n✅ Done!")

if __name__ == '__main__':
    main()