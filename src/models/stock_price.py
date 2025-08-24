from typing import List, Dict, Optional
from datetime import datetime
import psycopg2
from config.database import DatabaseConnection

class StockPrice:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_timescale_table(self):
        """Create TimescaleDB hypertable for stock prices"""
        queries = [
            # Create extension if not exists
            "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",
            
            # Create stock_prices table
            """
            CREATE TABLE IF NOT EXISTS stock_prices (
                time TIMESTAMP NOT NULL,
                stock_id INTEGER NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                close_price DECIMAL(10, 2) NOT NULL,
                volume BIGINT,
                high DECIMAL(10, 2),
                low DECIMAL(10, 2),
                open DECIMAL(10, 2),
                CONSTRAINT stock_prices_pkey PRIMARY KEY (time, stock_id),
                CONSTRAINT stock_prices_stock_id_fkey FOREIGN KEY (stock_id) 
                    REFERENCES stocks(id) ON DELETE CASCADE
            );
            """,
            
            # Convert to hypertable
            """
            SELECT create_hypertable('stock_prices', 'time', 
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '1 month'
            );
            """,
            
            # Create index for faster queries
            """
            CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_time 
            ON stock_prices (symbol, time DESC);
            """,
            
            # Create index on stock_id
            """
            CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id_time 
            ON stock_prices (stock_id, time DESC);
            """
        ]
        
        for query in queries:
            try:
                self.db.execute_query(query)
                print(f"✓ Executed: {query[:50]}...")
            except Exception as e:
                print(f"Error executing query: {e}")
                if "already exists" not in str(e):
                    raise
    
    def insert_price_data(self, price_data: List[Dict]) -> int:
        """Insert multiple price records using batch insert"""
        if not price_data:
            return 0
        
        insert_query = """
        INSERT INTO stock_prices (time, stock_id, symbol, close_price, volume, high, low, open)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (time, stock_id) DO UPDATE SET
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            open = EXCLUDED.open
        """
        
        cursor = self.db.connection.cursor()
        success_count = 0
        
        try:
            # Prepare data for batch insert
            values = []
            for data in price_data:
                values.append((
                    data['time'],
                    data['stock_id'],
                    data['symbol'],
                    data['close_price'],
                    data.get('volume'),
                    data.get('high'),
                    data.get('low'),
                    data.get('open')
                ))
            
            # Execute batch insert
            psycopg2.extras.execute_batch(cursor, insert_query, values, page_size=1000)
            self.db.connection.commit()
            success_count = len(values)
            
        except Exception as e:
            print(f"Error inserting price data: {e}")
            self.db.connection.rollback()
        finally:
            cursor.close()
        
        return success_count
    
    def get_latest_price_date(self, stock_id: int) -> Optional[datetime]:
        """Get the latest price date for a stock"""
        query = """
        SELECT MAX(time) FROM stock_prices WHERE stock_id = %s
        """
        
        result = self.db.execute_query(query, (stock_id,))
        if result and result[0][0]:
            return result[0][0]
        return None
    
    def get_price_history(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get price history for a symbol within date range"""
        query = """
        SELECT time, close_price, volume, high, low, open
        FROM stock_prices
        WHERE symbol = %s AND time >= %s AND time <= %s
        ORDER BY time DESC
        """
        
        results = self.db.execute_query(query, (symbol, start_date, end_date))
        
        if results:
            columns = ['time', 'close_price', 'volume', 'high', 'low', 'open']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_missing_data_stocks(self, days_back: int = 1) -> List[Dict]:
        """Get stocks that haven't been updated in the last N days"""
        query = """
        SELECT s.id, s.symbol, s.name, MAX(sp.time) as last_update
        FROM stocks s
        LEFT JOIN stock_prices sp ON s.id = sp.stock_id
        GROUP BY s.id, s.symbol, s.name
        HAVING MAX(sp.time) < CURRENT_DATE - INTERVAL '%s days' 
           OR MAX(sp.time) IS NULL
        ORDER BY s.symbol
        """
        
        results = self.db.execute_query(query, (days_back,))
        
        if results:
            columns = ['id', 'symbol', 'name', 'last_update']
            return [dict(zip(columns, row)) for row in results]
        
        return []