from typing import List, Dict
from config.database import DatabaseConnection

class Stock:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def insert_stock(self, stock_data: Dict) -> bool:
        insert_query = """
        INSERT INTO stocks (symbol, name, sector, industry, market_cap)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol) DO UPDATE SET
            name = EXCLUDED.name,
            sector = EXCLUDED.sector,
            industry = EXCLUDED.industry,
            market_cap = EXCLUDED.market_cap,
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            self.db.execute_query(insert_query, (
                stock_data['symbol'],
                stock_data['name'],
                stock_data['sector'],
                stock_data['industry'],
                stock_data['market_cap']
            ))
            return True
        except Exception as e:
            print(f"Error inserting stock {stock_data['symbol']}: {e}")
            return False
    
    def insert_multiple_stocks(self, stocks_data: List[Dict]) -> int:
        success_count = 0
        
        for stock_data in stocks_data:
            if self.insert_stock(stock_data):
                success_count += 1
        
        return success_count
    
    def get_all_stocks(self) -> List[Dict]:
        query = "SELECT * FROM stocks ORDER BY name"
        results = self.db.execute_query(query)
        
        if results:
            columns = ['id', 'symbol', 'name', 'sector', 'industry', 'market_cap', 'created_at', 'updated_at']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_stock_by_symbol(self, symbol: str) -> Dict:
        query = "SELECT * FROM stocks WHERE symbol = %s"
        results = self.db.execute_query(query, (symbol,))
        
        if results:
            columns = ['id', 'symbol', 'name', 'sector', 'industry', 'market_cap', 'created_at', 'updated_at']
            return dict(zip(columns, results[0]))
        
        return {}
    
    def get_stocks_by_sector(self, sector: str) -> List[Dict]:
        query = "SELECT * FROM stocks WHERE sector = %s ORDER BY name"
        results = self.db.execute_query(query, (sector,))
        
        if results:
            columns = ['id', 'symbol', 'name', 'sector', 'industry', 'market_cap', 'created_at', 'updated_at']
            return [dict(zip(columns, row)) for row in results]
        
        return []