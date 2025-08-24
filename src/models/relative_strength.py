from typing import List, Dict, Optional
from datetime import datetime, date
from config.database import DatabaseConnection

class RelativeStrength:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_table(self):
        """Create relative strength table for stocks and industry indices"""
        create_query = """
        CREATE TABLE IF NOT EXISTS relative_strength (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(50) NOT NULL,
            entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('STOCK', 'INDUSTRY_INDEX')),
            entity_name VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            benchmark_symbol VARCHAR(50) NOT NULL DEFAULT '^CRSLDX',
            
            -- Current prices
            current_price DECIMAL(12, 4) NOT NULL,
            benchmark_price DECIMAL(12, 4) NOT NULL,
            
            -- 30-day relative strength metrics
            price_30d DECIMAL(12, 4),
            benchmark_price_30d DECIMAL(12, 4),
            symbol_return_30d DECIMAL(10, 4),
            benchmark_return_30d DECIMAL(10, 4),
            relative_strength_30d DECIMAL(10, 4),
            
            -- 90-day relative strength metrics  
            price_90d DECIMAL(12, 4),
            benchmark_price_90d DECIMAL(12, 4),
            symbol_return_90d DECIMAL(10, 4),
            benchmark_return_90d DECIMAL(10, 4),
            relative_strength_90d DECIMAL(10, 4),
            
            -- 180-day relative strength metrics
            price_180d DECIMAL(12, 4), 
            benchmark_price_180d DECIMAL(12, 4),
            symbol_return_180d DECIMAL(10, 4),
            benchmark_return_180d DECIMAL(10, 4),
            relative_strength_180d DECIMAL(10, 4),
            
            -- Weinstein stage analysis data
            stock_ma_200 DECIMAL(12, 4),
            industry_ma_200 DECIMAL(12, 4),
            stock_ma_trend_up BOOLEAN,
            industry_ma_trend_up BOOLEAN,
            weinstein_stage INTEGER CHECK (weinstein_stage IN (1, 2, 3, 4)),
            benchmark_weinstein_stage INTEGER CHECK (benchmark_weinstein_stage IN (1, 2, 3, 4)),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(symbol, date, benchmark_symbol)
        );
        """
        
        # Create indices for faster queries
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_symbol_date ON relative_strength (symbol, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_entity_type_date ON relative_strength (entity_type, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_date ON relative_strength (date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_30d ON relative_strength (relative_strength_30d DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_90d ON relative_strength (relative_strength_90d DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_180d ON relative_strength (relative_strength_180d DESC);",
            "CREATE INDEX IF NOT EXISTS idx_relative_strength_benchmark ON relative_strength (benchmark_symbol, date DESC);"
        ]
        
        try:
            self.db.execute_query(create_query)
            print("✓ Created relative_strength table")
            
            for index_query in indices:
                self.db.execute_query(index_query)
            
            print("✓ Created relative_strength table indices")
            
        except Exception as e:
            print(f"Error creating relative_strength table: {e}")
    
    def insert_relative_strength_data(self, rs_data: List[Dict]) -> int:
        """Insert relative strength data with conflict resolution and validation"""
        if not rs_data:
            return 0
        
        # Validate data before insertion
        validated_data = []
        for i, data in enumerate(rs_data):
            try:
                validated_record = self._validate_rs_record(data)
                if validated_record:
                    validated_data.append(validated_record)
                else:
                    print(f"Skipping invalid record {i+1}: {data.get('symbol', 'Unknown')}")
            except Exception as e:
                print(f"Error validating record {i+1} ({data.get('symbol', 'Unknown')}): {e}")
        
        if not validated_data:
            print("No valid relative strength data to insert")
            return 0
        
        insert_query = """
        INSERT INTO relative_strength (
            symbol, entity_type, entity_name, date, benchmark_symbol,
            current_price, benchmark_price,
            price_30d, benchmark_price_30d, symbol_return_30d, benchmark_return_30d, relative_strength_30d,
            price_90d, benchmark_price_90d, symbol_return_90d, benchmark_return_90d, relative_strength_90d,
            price_180d, benchmark_price_180d, symbol_return_180d, benchmark_return_180d, relative_strength_180d,
            stock_ma_200, industry_ma_200, stock_ma_trend_up, industry_ma_trend_up, 
            weinstein_stage, benchmark_weinstein_stage,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (symbol, date, benchmark_symbol) DO UPDATE SET
            entity_type = EXCLUDED.entity_type,
            entity_name = EXCLUDED.entity_name,
            current_price = EXCLUDED.current_price,
            benchmark_price = EXCLUDED.benchmark_price,
            price_30d = EXCLUDED.price_30d,
            benchmark_price_30d = EXCLUDED.benchmark_price_30d,
            symbol_return_30d = EXCLUDED.symbol_return_30d,
            benchmark_return_30d = EXCLUDED.benchmark_return_30d,
            relative_strength_30d = EXCLUDED.relative_strength_30d,
            price_90d = EXCLUDED.price_90d,
            benchmark_price_90d = EXCLUDED.benchmark_price_90d,
            symbol_return_90d = EXCLUDED.symbol_return_90d,
            benchmark_return_90d = EXCLUDED.benchmark_return_90d,
            relative_strength_90d = EXCLUDED.relative_strength_90d,
            price_180d = EXCLUDED.price_180d,
            benchmark_price_180d = EXCLUDED.benchmark_price_180d,
            symbol_return_180d = EXCLUDED.symbol_return_180d,
            benchmark_return_180d = EXCLUDED.benchmark_return_180d,
            relative_strength_180d = EXCLUDED.relative_strength_180d,
            stock_ma_200 = EXCLUDED.stock_ma_200,
            industry_ma_200 = EXCLUDED.industry_ma_200,
            stock_ma_trend_up = EXCLUDED.stock_ma_trend_up,
            industry_ma_trend_up = EXCLUDED.industry_ma_trend_up,
            weinstein_stage = EXCLUDED.weinstein_stage,
            benchmark_weinstein_stage = EXCLUDED.benchmark_weinstein_stage,
            updated_at = CURRENT_TIMESTAMP
        """
        
        cursor = self.db.connection.cursor()
        success_count = 0
        
        try:
            # Prepare data for batch insert
            values = []
            for data in validated_data:
                values.append((
                    data['symbol'],
                    data['entity_type'],
                    data['entity_name'],
                    data['date'],
                    data['benchmark_symbol'],
                    data['current_price'],
                    data['benchmark_price'],
                    data.get('price_30d'),
                    data.get('benchmark_price_30d'),
                    data.get('symbol_return_30d'),
                    data.get('benchmark_return_30d'),
                    data.get('relative_strength_30d'),
                    data.get('price_90d'),
                    data.get('benchmark_price_90d'),
                    data.get('symbol_return_90d'),
                    data.get('benchmark_return_90d'),
                    data.get('relative_strength_90d'),
                    data.get('price_180d'),
                    data.get('benchmark_price_180d'),
                    data.get('symbol_return_180d'),
                    data.get('benchmark_return_180d'),
                    data.get('relative_strength_180d'),
                    data.get('stock_ma_200'),
                    data.get('industry_ma_200'),
                    data.get('stock_ma_trend_up'),
                    data.get('industry_ma_trend_up'),
                    data.get('weinstein_stage'),
                    data.get('benchmark_weinstein_stage')
                ))
            
            # Execute batch insert
            import psycopg2.extras
            psycopg2.extras.execute_batch(cursor, insert_query, values, page_size=1000)
            self.db.connection.commit()
            success_count = len(values)
            
        except Exception as e:
            print(f"Error inserting relative strength data: {e}")
            self.db.connection.rollback()
        finally:
            cursor.close()
        
        return success_count
    
    def _validate_rs_record(self, data: Dict) -> Optional[Dict]:
        """Validate and sanitize a relative strength record"""
        import math
        
        try:
            # Create a copy to avoid modifying original
            validated = data.copy()
            
            # Validate required fields
            required_fields = ['symbol', 'entity_type', 'entity_name', 'date', 'current_price', 'benchmark_price']
            if not all(key in validated for key in required_fields):
                return None
            
            # Set default benchmark if not provided
            if 'benchmark_symbol' not in validated:
                validated['benchmark_symbol'] = '^CRSLDX'
            
            # Validate and cap numeric fields
            numeric_fields = [
                'current_price', 'benchmark_price',
                'price_30d', 'price_90d', 'price_180d',
                'benchmark_price_30d', 'benchmark_price_90d', 'benchmark_price_180d',
                'symbol_return_30d', 'symbol_return_90d', 'symbol_return_180d',
                'benchmark_return_30d', 'benchmark_return_90d', 'benchmark_return_180d',
                'relative_strength_30d', 'relative_strength_90d', 'relative_strength_180d'
            ]
            
            for field in numeric_fields:
                if field in validated and validated[field] is not None:
                    value = validated[field]
                    
                    # Check for NaN or infinite values
                    if not (isinstance(value, (int, float)) and math.isfinite(value)):
                        validated[field] = None
                        continue
                    
                    # Apply field-specific limits
                    if field.endswith('_return_30d') or field.endswith('_return_90d') or field.endswith('_return_180d'):
                        # Returns: cap at +/- 9999%
                        validated[field] = max(-9999, min(9999, float(value)))
                    elif field.startswith('relative_strength_'):
                        # Relative strength: cap at +/- 9999 (can be very high or low)
                        validated[field] = max(-9999, min(9999, float(value)))
                    elif field.startswith('price_') or field.startswith('benchmark_price') or field in ['current_price', 'benchmark_price']:
                        # Prices: must be positive and reasonable
                        if value <= 0 or value > 9999999:
                            if field in ['current_price', 'benchmark_price']:
                                return None  # Current prices are required
                            else:
                                validated[field] = None
                        else:
                            validated[field] = float(value)
            
            # Validate entity_type
            if validated['entity_type'] not in ['STOCK', 'INDUSTRY_INDEX']:
                return None
            
            return validated
            
        except Exception as e:
            print(f"Error validating relative strength record: {e}")
            return None
    
    def get_top_relative_strength(self, period: str = '30d', limit: int = 20, entity_type: str = 'STOCK', benchmark: str = '^CRSLDX') -> List[Dict]:
        """Get top relative strength performers for a specific period"""
        rs_col = f"relative_strength_{period}"
        
        query = f"""
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM relative_strength
            WHERE entity_type = %s AND benchmark_symbol = %s
        )
        SELECT 
            rs.symbol,
            rs.entity_name,
            rs.date,
            rs.current_price,
            rs.{rs_col} as relative_strength,
            rs.symbol_return_{period} as symbol_return,
            rs.benchmark_return_{period} as benchmark_return
        FROM relative_strength rs
        INNER JOIN latest_date ld ON rs.date = ld.max_date
        WHERE rs.entity_type = %s
        AND rs.benchmark_symbol = %s
        AND rs.{rs_col} IS NOT NULL
        ORDER BY rs.{rs_col} DESC
        LIMIT %s
        """
        
        results = self.db.execute_query(query, (entity_type, benchmark, entity_type, benchmark, limit))
        
        if results:
            columns = ['symbol', 'entity_name', 'date', 'current_price', 'relative_strength', 'symbol_return', 'benchmark_return']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_relative_strength_history(self, symbol: str, days: int = 90, benchmark: str = '^CRSLDX') -> List[Dict]:
        """Get relative strength history for a specific symbol"""
        query = """
        SELECT 
            date,
            current_price,
            benchmark_price,
            relative_strength_30d,
            relative_strength_90d,
            relative_strength_180d,
            symbol_return_30d,
            benchmark_return_30d
        FROM relative_strength
        WHERE symbol = %s AND benchmark_symbol = %s
        ORDER BY date DESC
        LIMIT %s
        """
        
        results = self.db.execute_query(query, (symbol, benchmark, days))
        
        if results:
            columns = ['date', 'current_price', 'benchmark_price', 'relative_strength_30d', 'relative_strength_90d', 'relative_strength_180d', 'symbol_return_30d', 'benchmark_return_30d']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_relative_strength_statistics(self, benchmark: str = '^CRSLDX') -> List[Dict]:
        """Get relative strength table statistics"""
        stats_query = """
        SELECT 
            entity_type,
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(relative_strength_30d) as avg_rs_30d,
            AVG(relative_strength_90d) as avg_rs_90d,
            AVG(relative_strength_180d) as avg_rs_180d
        FROM relative_strength
        WHERE benchmark_symbol = %s
        GROUP BY entity_type
        ORDER BY entity_type
        """
        
        results = self.db.execute_query(stats_query, (benchmark,))
        
        if results:
            columns = ['entity_type', 'total_records', 'unique_symbols', 'earliest_date', 'latest_date', 
                      'avg_rs_30d', 'avg_rs_90d', 'avg_rs_180d']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def compare_relative_strength(self, symbols: List[str], period: str = '30d', benchmark: str = '^CRSLDX') -> List[Dict]:
        """Compare relative strength across multiple symbols"""
        if not symbols:
            return []
        
        rs_col = f"relative_strength_{period}"
        return_col = f"symbol_return_{period}"
        benchmark_return_col = f"benchmark_return_{period}"
        placeholders = ','.join(['%s'] * len(symbols))
        
        query = f"""
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM relative_strength
            WHERE symbol IN ({placeholders}) AND benchmark_symbol = %s
        )
        SELECT 
            rs.symbol,
            rs.entity_name,
            rs.entity_type,
            rs.current_price,
            rs.{rs_col} as relative_strength,
            rs.{return_col} as symbol_return,
            rs.{benchmark_return_col} as benchmark_return
        FROM relative_strength rs
        INNER JOIN latest_date ld ON rs.date = ld.max_date
        WHERE rs.symbol IN ({placeholders}) AND rs.benchmark_symbol = %s
        ORDER BY rs.{rs_col} DESC
        """
        
        params = symbols + [benchmark] + symbols + [benchmark]
        results = self.db.execute_query(query, params)
        
        if results:
            columns = ['symbol', 'entity_name', 'entity_type', 'current_price', 'relative_strength', 'symbol_return', 'benchmark_return']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def delete_old_data(self, days_to_keep: int = 365, benchmark: str = '^CRSLDX') -> int:
        """Delete relative strength data older than specified days"""
        query = """
        DELETE FROM relative_strength 
        WHERE date < CURRENT_DATE - INTERVAL '%s days'
        AND benchmark_symbol = %s
        """
        
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(query, (days_to_keep, benchmark))
            deleted_count = cursor.rowcount
            self.db.connection.commit()
            cursor.close()
            return deleted_count
        except Exception as e:
            print(f"Error deleting old relative strength data: {e}")
            return 0