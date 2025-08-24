#!/usr/bin/env python3
"""
Fix Momentum Table Schema
Updates the momentum table to handle larger numeric values
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection

def fix_momentum_table():
    """Fix the momentum table schema to prevent numeric overflow"""
    print("=== Fixing Momentum Table Schema ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Check if table exists
    check_table_query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'momentum'
    );
    """
    
    table_exists = db.execute_query(check_table_query)
    
    if not table_exists or not table_exists[0][0]:
        print("✅ Momentum table doesn't exist yet - will be created with correct schema")
        db.close()
        return
    
    print("2. Checking current table schema...")
    
    # Get current column info
    column_info_query = """
    SELECT column_name, data_type, numeric_precision, numeric_scale
    FROM information_schema.columns
    WHERE table_name = 'momentum'
    AND column_name LIKE '%momentum%' OR column_name = 'volatility_30d'
    ORDER BY column_name;
    """
    
    current_columns = db.execute_query(column_info_query)
    
    if current_columns:
        print("Current numeric column specifications:")
        for col in current_columns:
            print(f"  {col[0]}: {col[1]}({col[2]},{col[3]})")
    
    print("\n3. Updating table schema...")
    
    # Drop and recreate with correct schema
    try:
        # Backup existing data if any
        backup_query = """
        CREATE TEMP TABLE momentum_backup AS
        SELECT * FROM momentum;
        """
        
        drop_query = "DROP TABLE IF EXISTS momentum CASCADE;"
        
        # New table with correct schema
        create_query = """
        CREATE TABLE momentum (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(50) NOT NULL,
            entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('STOCK', 'INDUSTRY_INDEX', 'MARKET_INDEX')),
            entity_name VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            current_price DECIMAL(12, 4) NOT NULL,
            
            -- 30-day momentum metrics
            price_30d DECIMAL(12, 4),
            momentum_30d DECIMAL(15, 4),
            momentum_30d_pct DECIMAL(10, 4),
            
            -- 90-day momentum metrics  
            price_90d DECIMAL(12, 4),
            momentum_90d DECIMAL(15, 4),
            momentum_90d_pct DECIMAL(10, 4),
            
            -- 180-day momentum metrics
            price_180d DECIMAL(12, 4), 
            momentum_180d DECIMAL(15, 4),
            momentum_180d_pct DECIMAL(10, 4),
            
            -- Additional metrics
            volatility_30d DECIMAL(10, 4),
            volume_avg_30d BIGINT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(symbol, date)
        );
        """
        
        # Create indices
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_momentum_symbol_date ON momentum (symbol, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_entity_type_date ON momentum (entity_type, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_date ON momentum (date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_30d_pct ON momentum (momentum_30d_pct DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_90d_pct ON momentum (momentum_90d_pct DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_180d_pct ON momentum (momentum_180d_pct DESC);"
        ]
        
        # Check if there's existing data
        count_query = "SELECT COUNT(*) FROM momentum;"
        existing_data = db.execute_query(count_query)
        has_data = existing_data and existing_data[0][0] > 0
        
        if has_data:
            print(f"   Found {existing_data[0][0]} existing records - backing up...")
            db.execute_query(backup_query)
            print("   ✓ Data backed up to temporary table")
        
        # Drop and recreate
        db.execute_query(drop_query)
        print("   ✓ Dropped old table")
        
        db.execute_query(create_query)
        print("   ✓ Created new table with updated schema")
        
        # Create indices
        for index_query in indices:
            db.execute_query(index_query)
        print("   ✓ Created indices")
        
        # Restore data if it existed
        if has_data:
            try:
                restore_query = """
                INSERT INTO momentum 
                SELECT * FROM momentum_backup
                WHERE momentum_30d_pct BETWEEN -9999 AND 9999
                AND momentum_90d_pct BETWEEN -9999 AND 9999  
                AND momentum_180d_pct BETWEEN -9999 AND 9999
                AND volatility_30d BETWEEN 0 AND 999;
                """
                
                result = db.execute_query(restore_query)
                print("   ✓ Restored valid data from backup")
                
                # Check restored count
                new_count = db.execute_query(count_query)
                if new_count:
                    restored = new_count[0][0]
                    skipped = existing_data[0][0] - restored
                    print(f"   ✓ Restored {restored} records")
                    if skipped > 0:
                        print(f"   ⚠️  Skipped {skipped} records with extreme values")
                
            except Exception as e:
                print(f"   ⚠️  Could not restore all data: {e}")
                print("   ℹ️  You may need to recalculate momentum data")
        
        print("\n✅ Table schema updated successfully!")
        
        # Show new schema
        print("\n4. New table schema:")
        new_columns = db.execute_query(column_info_query)
        if new_columns:
            for col in new_columns:
                print(f"  {col[0]}: {col[1]}({col[2]},{col[3]})")
        
    except Exception as e:
        print(f"❌ Error updating table schema: {e}")
        db.connection.rollback()
    
    db.close()
    print("\n✅ Schema fix completed!")

if __name__ == "__main__":
    proceed = input("This will drop and recreate the momentum table. Continue? (y/n): ").strip().lower()
    
    if proceed == 'y':
        fix_momentum_table()
    else:
        print("Operation cancelled")