from typing import List, Dict, Optional
from datetime import datetime, date
from config.database import DatabaseConnection

class Momentum:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def create_table(self):
        """Create momentum table for stocks and industry indices"""
        create_query = """
        CREATE TABLE IF NOT EXISTS momentum (
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
        
        # Create indices for faster queries
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_momentum_symbol_date ON momentum (symbol, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_entity_type_date ON momentum (entity_type, date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_date ON momentum (date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_30d_pct ON momentum (momentum_30d_pct DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_90d_pct ON momentum (momentum_90d_pct DESC);",
            "CREATE INDEX IF NOT EXISTS idx_momentum_180d_pct ON momentum (momentum_180d_pct DESC);"
        ]
        
        try:
            self.db.execute_query(create_query)
            print("✓ Created momentum table")
            
            for index_query in indices:
                self.db.execute_query(index_query)
            
            print("✓ Created momentum table indices")
            
        except Exception as e:
            print(f"Error creating momentum table: {e}")
    
    def insert_momentum_data(self, momentum_data: List[Dict]) -> int:
        """Insert momentum data with conflict resolution and validation"""
        if not momentum_data:
            return 0
        
        # Validate data before insertion
        validated_data = []
        for i, data in enumerate(momentum_data):
            try:
                # Validate and clean numeric fields
                validated_record = self._validate_momentum_record(data)
                if validated_record:
                    validated_data.append(validated_record)
                else:
                    print(f"Skipping invalid record {i+1}: {data.get('symbol', 'Unknown')}")
            except Exception as e:
                print(f"Error validating record {i+1} ({data.get('symbol', 'Unknown')}): {e}")
        
        if not validated_data:
            print("No valid momentum data to insert")
            return 0
        
        insert_query = """
        INSERT INTO momentum (
            symbol, entity_type, entity_name, date, current_price,
            price_30d, momentum_30d, momentum_30d_pct,
            price_90d, momentum_90d, momentum_90d_pct,
            price_180d, momentum_180d, momentum_180d_pct,
            volatility_30d, volume_avg_30d, updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, 
            %s, %s, %s,
            %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (symbol, date) DO UPDATE SET
            entity_type = EXCLUDED.entity_type,
            entity_name = EXCLUDED.entity_name,
            current_price = EXCLUDED.current_price,
            price_30d = EXCLUDED.price_30d,
            momentum_30d = EXCLUDED.momentum_30d,
            momentum_30d_pct = EXCLUDED.momentum_30d_pct,
            price_90d = EXCLUDED.price_90d,
            momentum_90d = EXCLUDED.momentum_90d,
            momentum_90d_pct = EXCLUDED.momentum_90d_pct,
            price_180d = EXCLUDED.price_180d,
            momentum_180d = EXCLUDED.momentum_180d,
            momentum_180d_pct = EXCLUDED.momentum_180d_pct,
            volatility_30d = EXCLUDED.volatility_30d,
            volume_avg_30d = EXCLUDED.volume_avg_30d,
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
                    data['current_price'],
                    data.get('price_30d'),
                    data.get('momentum_30d'),
                    data.get('momentum_30d_pct'),
                    data.get('price_90d'),
                    data.get('momentum_90d'),
                    data.get('momentum_90d_pct'),
                    data.get('price_180d'),
                    data.get('momentum_180d'),
                    data.get('momentum_180d_pct'),
                    data.get('volatility_30d'),
                    data.get('volume_avg_30d')
                ))
            
            # Execute batch insert
            import psycopg2.extras
            psycopg2.extras.execute_batch(cursor, insert_query, values, page_size=1000)
            self.db.connection.commit()
            success_count = len(values)
            
        except Exception as e:
            print(f"Error inserting momentum data: {e}")
            self.db.connection.rollback()
        finally:
            cursor.close()
        
        return success_count
    
    def _validate_momentum_record(self, data: Dict) -> Optional[Dict]:
        """Validate and sanitize a momentum record"""
        import math
        
        try:
            # Create a copy to avoid modifying original
            validated = data.copy()
            
            # Validate required fields
            if not all(key in validated for key in ['symbol', 'entity_type', 'entity_name', 'date', 'current_price']):
                return None
            
            # Validate and cap numeric fields
            numeric_fields = [
                'current_price', 'price_30d', 'price_90d', 'price_180d',
                'momentum_30d', 'momentum_90d', 'momentum_180d',
                'momentum_30d_pct', 'momentum_90d_pct', 'momentum_180d_pct',
                'volatility_30d'
            ]
            
            for field in numeric_fields:
                if field in validated and validated[field] is not None:
                    value = validated[field]
                    
                    # Check for NaN or infinite values
                    if not (isinstance(value, (int, float)) and math.isfinite(value)):
                        validated[field] = None
                        continue
                    
                    # Apply field-specific limits
                    if field.endswith('_pct'):
                        # Momentum percentages: cap at +/- 9999%
                        validated[field] = max(-9999, min(9999, float(value)))
                    elif field.startswith('momentum_'):
                        # Absolute momentum: cap at +/- 999999
                        validated[field] = max(-999999, min(999999, float(value)))
                    elif field == 'volatility_30d':
                        # Volatility: cap at 0-999%
                        validated[field] = max(0, min(999, float(value)))
                    elif field.startswith('price_') or field == 'current_price':
                        # Prices: must be positive and reasonable
                        if value <= 0 or value > 9999999:
                            if field == 'current_price':
                                return None  # Current price is required
                            else:
                                validated[field] = None
                        else:
                            validated[field] = float(value)
            
            # Validate volume
            if 'volume_avg_30d' in validated and validated['volume_avg_30d'] is not None:
                volume = validated['volume_avg_30d']
                if isinstance(volume, (int, float)) and math.isfinite(volume) and volume >= 0:
                    validated['volume_avg_30d'] = int(min(volume, 9999999999))  # Cap volume
                else:
                    validated['volume_avg_30d'] = None
            
            # Validate entity_type
            if validated['entity_type'] not in ['STOCK', 'INDUSTRY_INDEX', 'MARKET_INDEX']:
                return None
            
            return validated
            
        except Exception as e:
            print(f"Error validating momentum record: {e}")
            return None
    
    def get_top_momentum_stocks(self, period: str = '30d', limit: int = 20, entity_type: str = 'STOCK') -> List[Dict]:
        """Get top momentum stocks/indices for a specific period"""
        momentum_col = f"momentum_{period}_pct"
        
        query = f"""
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM momentum
            WHERE entity_type = %s
        )
        SELECT 
            m.symbol,
            m.entity_name,
            m.date,
            m.current_price,
            m.{momentum_col} as momentum_pct,
            m.volatility_30d,
            m.volume_avg_30d
        FROM momentum m
        INNER JOIN latest_date ld ON m.date = ld.max_date
        WHERE m.entity_type = %s
        AND m.{momentum_col} IS NOT NULL
        ORDER BY m.{momentum_col} DESC
        LIMIT %s
        """
        
        results = self.db.execute_query(query, (entity_type, entity_type, limit))
        
        if results:
            columns = ['symbol', 'entity_name', 'date', 'current_price', 'momentum_pct', 'volatility_30d', 'volume_avg_30d']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_momentum_history(self, symbol: str, days: int = 90) -> List[Dict]:
        """Get momentum history for a specific symbol"""
        query = """
        SELECT 
            date,
            current_price,
            momentum_30d_pct,
            momentum_90d_pct,
            momentum_180d_pct,
            volatility_30d
        FROM momentum
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT %s
        """
        
        results = self.db.execute_query(query, (symbol, days))
        
        if results:
            columns = ['date', 'current_price', 'momentum_30d_pct', 'momentum_90d_pct', 'momentum_180d_pct', 'volatility_30d']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_momentum_statistics(self) -> Dict:
        """Get momentum table statistics"""
        stats_query = """
        SELECT 
            entity_type,
            COUNT(*) as total_records,
            COUNT(DISTINCT symbol) as unique_symbols,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(momentum_30d_pct) as avg_momentum_30d,
            AVG(momentum_90d_pct) as avg_momentum_90d,
            AVG(momentum_180d_pct) as avg_momentum_180d
        FROM momentum
        GROUP BY entity_type
        ORDER BY entity_type
        """
        
        results = self.db.execute_query(stats_query)
        
        if results:
            columns = ['entity_type', 'total_records', 'unique_symbols', 'earliest_date', 'latest_date', 
                      'avg_momentum_30d', 'avg_momentum_90d', 'avg_momentum_180d']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def delete_old_data(self, days_to_keep: int = 365) -> int:
        """Delete momentum data older than specified days"""
        query = """
        DELETE FROM momentum 
        WHERE date < CURRENT_DATE - INTERVAL '%s days'
        """
        
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(query, (days_to_keep,))
            deleted_count = cursor.rowcount
            self.db.connection.commit()
            cursor.close()
            return deleted_count
        except Exception as e:
            print(f"Error deleting old momentum data: {e}")
            return 0
    
    def get_momentum_comparison(self, symbols: List[str], period: str = '30d') -> List[Dict]:
        """Compare momentum across multiple symbols"""
        if not symbols:
            return []
        
        momentum_col = f"momentum_{period}_pct"
        placeholders = ','.join(['%s'] * len(symbols))
        
        query = f"""
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM momentum
            WHERE symbol IN ({placeholders})
        )
        SELECT 
            m.symbol,
            m.entity_name,
            m.entity_type,
            m.current_price,
            m.{momentum_col} as momentum_pct,
            m.volatility_30d
        FROM momentum m
        INNER JOIN latest_date ld ON m.date = ld.max_date
        WHERE m.symbol IN ({placeholders})
        ORDER BY m.{momentum_col} DESC
        """
        
        params = symbols + symbols
        results = self.db.execute_query(query, params)
        
        if results:
            columns = ['symbol', 'entity_name', 'entity_type', 'current_price', 'momentum_pct', 'volatility_30d']
            return [dict(zip(columns, row)) for row in results]
        
        return []