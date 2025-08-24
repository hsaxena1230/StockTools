#!/usr/bin/env python3
"""
Continue/Resume 2-year industry relative strength generation
This script checks what's already calculated and continues from there
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.relative_strength import RelativeStrength
from src.utils.relative_strength_calculator import RelativeStrengthCalculator

def main():
    print("=== Resuming 2-Year Industry Relative Strength Generation ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Check existing data
    print("\n2. Checking existing relative strength data...")
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=730)
    
    # Get already processed dates
    existing_query = """
    SELECT DISTINCT date 
    FROM relative_strength 
    WHERE entity_type = 'INDUSTRY_INDEX'
    AND date >= %s AND date <= %s
    ORDER BY date
    """
    
    existing_dates_result = db.execute_query(existing_query, (start_date, end_date))
    existing_dates = set(row[0] for row in existing_dates_result) if existing_dates_result else set()
    
    print(f"   Found {len(existing_dates)} dates already processed")
    
    # Get all dates that need processing
    all_dates_query = """
    SELECT DISTINCT date 
    FROM equiweighted_index 
    WHERE date >= %s AND date <= %s
    ORDER BY date
    """
    
    all_dates_result = db.execute_query(all_dates_query, (start_date, end_date))
    all_dates = [row[0] for row in all_dates_result] if all_dates_result else []
    
    # Find dates that still need processing
    dates_to_process = [date for date in all_dates if date not in existing_dates]
    
    print(f"   Total dates available: {len(all_dates)}")
    print(f"   Dates remaining to process: {len(dates_to_process)}")
    
    if not dates_to_process:
        print("\n✅ All dates have been processed! Nothing to do.")
        
        # Show summary
        summary_query = """
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
        
        summary = db.execute_query(summary_query, (start_date, end_date))
        if summary:
            total, dates, industries, min_date, max_date = summary[0]
            print(f"\n📊 Current Status:")
            print(f"   Total records: {total:,}")
            print(f"   Date range: {min_date} to {max_date}")
            print(f"   Unique dates: {dates}")
            print(f"   Unique industries: {industries}")
        
        db.close()
        return
    
    # Get industries
    industries_query = """
    SELECT DISTINCT industry 
    FROM equiweighted_index 
    WHERE date >= %s AND date <= %s
    ORDER BY industry
    """
    
    industries_result = db.execute_query(industries_query, (start_date, end_date))
    industries = [row[0] for row in industries_result] if industries_result else []
    
    print(f"   Industries to process: {len(industries)}")
    
    # Initialize calculator
    rs_model = RelativeStrength(db)
    calculator = RelativeStrengthCalculator(db, benchmark_symbol='^CRSLDX')
    
    # Ensure table exists
    rs_model.create_table()
    
    # Process remaining dates
    print(f"\n3. Processing {len(dates_to_process)} remaining dates...")
    print("   This will take several minutes to complete...")
    
    total_calculations = len(dates_to_process) * len(industries)
    successful_calculations = 0
    failed_calculations = 0
    processed_count = 0
    
    for date_idx, calc_date in enumerate(dates_to_process, 1):
        if date_idx % 5 == 0 or date_idx == 1:
            print(f"\nProcessing date {date_idx}/{len(dates_to_process)}: {calc_date}")
        
        # Get benchmark data for this date
        benchmark_df = calculator.get_benchmark_price_data(calc_date, days_back=270)
        
        if benchmark_df.empty:
            print(f"   No benchmark data for {calc_date}, skipping...")
            failed_calculations += len(industries)
            processed_count += len(industries)
            continue
        
        rs_batch = []
        date_success = 0
        date_failed = 0
        
        # Calculate relative strength for each industry on this date
        for industry in industries:
            try:
                # Check if this specific combination already exists
                check_query = """
                SELECT 1 FROM relative_strength 
                WHERE symbol = %s AND date = %s AND benchmark_symbol = %s
                AND entity_type = 'INDUSTRY_INDEX'
                LIMIT 1
                """
                exists = db.execute_query(check_query, (industry, calc_date, '^CRSLDX'))
                
                if not exists or len(exists) == 0:
                    # Calculate industry relative strength
                    rs_data = calculator.calculate_industry_relative_strength(industry, benchmark_df, calc_date)
                    
                    if rs_data:
                        rs_batch.append(rs_data)
                        date_success += 1
                    else:
                        date_failed += 1
                        # Log why it failed
                        if date_failed <= 5:  # Only log first few failures
                            print(f"      Failed: {industry}")
                else:
                    # Already exists, skip
                    date_success += 1
                
            except Exception as e:
                print(f"   Error calculating RS for {industry} on {calc_date}: {e}")
                date_failed += 1
            
            processed_count += 1
            
            # Progress update
            if processed_count % 500 == 0:
                progress = (processed_count / total_calculations) * 100
                print(f"   Overall progress: {processed_count}/{total_calculations} ({progress:.1f}%)")
        
        # Insert batch for this date
        if rs_batch:
            try:
                inserted_count = rs_model.insert_relative_strength_data(rs_batch)
                print(f"   ✓ Date {calc_date}: Inserted {inserted_count} new records")
                successful_calculations += inserted_count
            except Exception as e:
                print(f"   ✗ Error inserting batch for {calc_date}: {e}")
                failed_calculations += len(rs_batch)
        else:
            print(f"   ✓ Date {calc_date}: All {date_success} industries already processed")
            successful_calculations += date_success
        
        failed_calculations += date_failed
    
    # Final summary
    print(f"\n=== Resume Operation Complete ===")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Dates processed in this run: {len(dates_to_process)}")
    print(f"Industries: {len(industries)}")
    print(f"Successful calculations: {successful_calculations:,}")
    print(f"Failed calculations: {failed_calculations:,}")
    
    # Get final state
    final_query = """
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT date) as unique_dates,
        COUNT(DISTINCT symbol) as unique_industries
    FROM relative_strength 
    WHERE entity_type = 'INDUSTRY_INDEX'
    AND date >= %s AND date <= %s
    """
    
    final_result = db.execute_query(final_query, (start_date, end_date))
    if final_result:
        total, dates, industries = final_result[0]
        print(f"\n📊 Final Database State:")
        print(f"   Total RS records: {total:,}")
        print(f"   Unique dates: {dates}")
        print(f"   Unique industries: {industries}")
        print(f"   Expected total: ~{dates * industries:,}")
    
    db.close()
    print("\n✅ Done!")

if __name__ == '__main__':
    main()