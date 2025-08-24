from typing import List, Dict
from config.database import DatabaseConnection

class MissingStock:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_table(self):
        """Create table for stocks with missing data"""
        create_query = """
        CREATE TABLE IF NOT EXISTS missing_stock_data (
            id SERIAL PRIMARY KEY,
            sc_code VARCHAR(20),
            sc_name VARCHAR(255) NOT NULL,
            sc_group VARCHAR(10),
            attempted_symbol VARCHAR(50),
            reason VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sc_code)
        );
        """
        
        try:
            self.db.execute_query(create_query)
            print("✓ Created missing_stock_data table")
        except Exception as e:
            print(f"Error creating table: {e}")
    
    def insert_missing_stock(self, stock_data: Dict) -> bool:
        """Insert a stock with missing data"""
        insert_query = """
        INSERT INTO missing_stock_data (sc_code, sc_name, sc_group, attempted_symbol, reason)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sc_code) DO UPDATE SET
            attempted_symbol = EXCLUDED.attempted_symbol,
            reason = EXCLUDED.reason
        """
        
        try:
            self.db.execute_query(insert_query, (
                stock_data.get('sc_code'),
                stock_data['sc_name'],
                stock_data.get('sc_group'),
                stock_data.get('attempted_symbol'),
                stock_data.get('reason', 'Missing sector information')
            ))
            return True
        except Exception as e:
            print(f"Error inserting missing stock {stock_data['sc_name']}: {e}")
            return False
    
    def get_all_missing_stocks(self) -> List[Dict]:
        """Get all stocks with missing data"""
        query = """
        SELECT * FROM missing_stock_data 
        ORDER BY sc_name
        """
        
        results = self.db.execute_query(query)
        
        if results:
            columns = ['id', 'sc_code', 'sc_name', 'sc_group', 'attempted_symbol', 'reason', 'created_at']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_missing_count_by_reason(self) -> List[Dict]:
        """Get count of missing stocks grouped by reason"""
        query = """
        SELECT reason, COUNT(*) as count 
        FROM missing_stock_data 
        GROUP BY reason 
        ORDER BY count DESC
        """
        
        results = self.db.execute_query(query)
        
        if results:
            return [{'reason': row[0], 'count': row[1]} for row in results]
        
        return []