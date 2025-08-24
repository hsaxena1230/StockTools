from typing import List, Dict, Optional
from datetime import datetime, date
from config.database import DatabaseConnection

class EquiweightedIndex:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_table(self):
        """Create equiweighted_index table"""
        create_query = """
        CREATE TABLE IF NOT EXISTS equiweighted_index (
            id SERIAL PRIMARY KEY,
            industry VARCHAR(100) NOT NULL,
            date DATE NOT NULL,
            index_value DECIMAL(12, 6) NOT NULL,
            stock_count INTEGER NOT NULL,
            base_value DECIMAL(12, 6) DEFAULT 1000.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(industry, date)
        );
        """
        
        # Create index for faster queries
        index_query = """
        CREATE INDEX IF NOT EXISTS idx_equiweighted_index_industry_date 
        ON equiweighted_index (industry, date DESC);
        """
        
        try:
            self.db.execute_query(create_query)
            self.db.execute_query(index_query)
            print("✓ Created equiweighted_index table")
        except Exception as e:
            print(f"Error creating equiweighted_index table: {e}")
    
    def insert_index_data(self, index_data: List[Dict]) -> int:
        """Insert index data with conflict resolution"""
        if not index_data:
            return 0
        
        insert_query = """
        INSERT INTO equiweighted_index (industry, date, index_value, stock_count, base_value)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (industry, date) DO UPDATE SET
            index_value = EXCLUDED.index_value,
            stock_count = EXCLUDED.stock_count,
            base_value = EXCLUDED.base_value
        """
        
        cursor = self.db.connection.cursor()
        success_count = 0
        
        try:
            # Prepare data for batch insert
            values = []
            for data in index_data:
                values.append((
                    data['industry'],
                    data['date'],
                    data['index_value'],
                    data['stock_count'],
                    data.get('base_value', 1000.0)
                ))
            
            # Execute batch insert
            import psycopg2.extras
            psycopg2.extras.execute_batch(cursor, insert_query, values, page_size=1000)
            self.db.connection.commit()
            success_count = len(values)
            
        except Exception as e:
            print(f"Error inserting index data: {e}")
            self.db.connection.rollback()
        finally:
            cursor.close()
        
        return success_count
    
    def get_industries_with_stocks(self) -> List[Dict]:
        """Get all industries with their stock counts"""
        query = """
        SELECT 
            industry,
            COUNT(*) as stock_count,
            COUNT(DISTINCT symbol) as unique_symbols
        FROM stocks 
        WHERE industry IS NOT NULL 
        AND industry != '' 
        AND industry != 'N/A'
        GROUP BY industry
        HAVING COUNT(*) >= 3  -- At least 3 stocks for meaningful index
        ORDER BY COUNT(*) DESC
        """
        
        results = self.db.execute_query(query)
        
        if results:
            columns = ['industry', 'stock_count', 'unique_symbols']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_industry_index_history(self, industry: str, start_date: date, end_date: date) -> List[Dict]:
        """Get index history for a specific industry"""
        query = """
        SELECT date, index_value, stock_count, base_value
        FROM equiweighted_index
        WHERE industry = %s 
        AND date >= %s 
        AND date <= %s
        ORDER BY date
        """
        
        results = self.db.execute_query(query, (industry, start_date, end_date))
        
        if results:
            columns = ['date', 'index_value', 'stock_count', 'base_value']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_all_industries_latest_values(self) -> List[Dict]:
        """Get latest index values for all industries"""
        query = """
        WITH latest_dates AS (
            SELECT industry, MAX(date) as latest_date
            FROM equiweighted_index
            GROUP BY industry
        )
        SELECT 
            ei.industry,
            ei.date,
            ei.index_value,
            ei.stock_count,
            ei.base_value
        FROM equiweighted_index ei
        INNER JOIN latest_dates ld 
            ON ei.industry = ld.industry 
            AND ei.date = ld.latest_date
        ORDER BY ei.industry
        """
        
        results = self.db.execute_query(query)
        
        if results:
            columns = ['industry', 'date', 'index_value', 'stock_count', 'base_value']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def calculate_industry_performance(self, industry: str, days: int = 30) -> Dict:
        """Calculate performance metrics for an industry index"""
        query = """
        WITH daily_values AS (
            SELECT date, index_value
            FROM equiweighted_index
            WHERE industry = %s
            ORDER BY date DESC
            LIMIT %s
        ),
        performance_calc AS (
            SELECT 
                MIN(index_value) as min_value,
                MAX(index_value) as max_value,
                FIRST_VALUE(index_value) OVER (ORDER BY date DESC) as latest_value,
                LAST_VALUE(index_value) OVER (ORDER BY date DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as oldest_value,
                COUNT(*) as data_points
            FROM daily_values
        )
        SELECT 
            latest_value,
            oldest_value,
            min_value,
            max_value,
            data_points,
            CASE 
                WHEN oldest_value > 0 THEN 
                    ROUND(((latest_value - oldest_value) / oldest_value * 100)::numeric, 2)
                ELSE 0 
            END as return_pct
        FROM performance_calc
        """
        
        result = self.db.execute_query(query, (industry, days))
        
        if result and result[0]:
            columns = ['latest_value', 'oldest_value', 'min_value', 'max_value', 'data_points', 'return_pct']
            return dict(zip(columns, result[0]))
        
        return {}
    
    def delete_industry_data(self, industry: str) -> int:
        """Delete all data for a specific industry"""
        query = "DELETE FROM equiweighted_index WHERE industry = %s"
        
        try:
            result = self.db.execute_query(query, (industry,))
            return 1  # Success
        except Exception as e:
            print(f"Error deleting data for {industry}: {e}")
            return 0