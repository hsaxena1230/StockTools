import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.models.equiweighted_index import EquiweightedIndex
import numpy as np

class IndexCalculator:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.stock_model = Stock(db_connection)
        self.stock_price_model = StockPrice(db_connection)
        self.index_model = EquiweightedIndex(db_connection)
    
    def get_industry_stocks(self, industry: str) -> List[Dict]:
        """Get all stocks for a specific industry"""
        query = """
        SELECT id, symbol, name, industry, sector
        FROM stocks
        WHERE industry = %s
        AND symbol IS NOT NULL
        AND symbol != ''
        ORDER BY symbol
        """
        
        results = self.db.execute_query(query, (industry,))
        
        if results:
            columns = ['id', 'symbol', 'name', 'industry', 'sector']
            return [dict(zip(columns, row)) for row in results]
        
        return []
    
    def get_stock_prices_for_period(self, stock_ids: List[int], start_date: date, end_date: date) -> pd.DataFrame:
        """Get stock prices for multiple stocks within a date range"""
        if not stock_ids:
            return pd.DataFrame()
        
        # Convert list to tuple for SQL IN clause
        stock_ids_tuple = tuple(stock_ids)
        placeholders = ','.join(['%s'] * len(stock_ids))
        
        query = f"""
        SELECT 
            sp.time::date as date,
            s.symbol,
            s.id as stock_id,
            sp.close_price
        FROM stock_prices sp
        INNER JOIN stocks s ON sp.stock_id = s.id
        WHERE sp.stock_id IN ({placeholders})
        AND sp.time::date >= %s
        AND sp.time::date <= %s
        ORDER BY sp.time::date, s.symbol
        """
        
        params = list(stock_ids) + [start_date, end_date]
        results = self.db.execute_query(query, params)
        
        if results:
            df = pd.DataFrame(results, columns=['date', 'symbol', 'stock_id', 'close_price'])
            df['date'] = pd.to_datetime(df['date'])
            df['close_price'] = pd.to_numeric(df['close_price'])
            return df
        
        return pd.DataFrame()
    
    def calculate_equal_weighted_index(self, prices_df: pd.DataFrame, base_value: float = 1000.0) -> pd.DataFrame:
        """Calculate equal-weighted index from price data"""
        if prices_df.empty:
            return pd.DataFrame()
        
        # Pivot to get prices by date and symbol
        pivot_df = prices_df.pivot(index='date', columns='symbol', values='close_price')
        
        # Forward fill missing values (use last available price)
        pivot_df = pivot_df.fillna(method='ffill')
        
        # Drop any rows/columns that are still completely NaN
        pivot_df = pivot_df.dropna(axis=1, how='all')  # Drop columns with all NaN
        pivot_df = pivot_df.dropna(axis=0, how='all')  # Drop rows with all NaN
        
        if pivot_df.empty:
            return pd.DataFrame()
        
        # Calculate daily returns for each stock
        returns_df = pivot_df.pct_change().fillna(0)
        
        # Calculate equal-weighted returns (mean of all stock returns each day)
        equal_weighted_returns = returns_df.mean(axis=1)
        
        # Calculate cumulative index values starting from base_value
        index_values = (1 + equal_weighted_returns).cumprod() * base_value
        
        # Create result DataFrame
        result_df = pd.DataFrame({
            'date': index_values.index.date,
            'index_value': index_values.values,
            'stock_count': (~pivot_df.isna()).sum(axis=1).values  # Count of non-NaN stocks each day
        })
        
        return result_df
    
    def calculate_industry_index(self, industry: str, start_date: date, end_date: date, base_value: float = 1000.0) -> List[Dict]:
        """Calculate equal-weighted index for a specific industry"""
        # Get stocks in the industry
        industry_stocks = self.get_industry_stocks(industry)
        
        if len(industry_stocks) < 3:  # Need at least 3 stocks for meaningful index
            print(f"  ⚠️  Industry '{industry}' has only {len(industry_stocks)} stocks, skipping")
            return []
        
        stock_ids = [stock['id'] for stock in industry_stocks]
        
        # Get price data
        prices_df = self.get_stock_prices_for_period(stock_ids, start_date, end_date)
        
        if prices_df.empty:
            print(f"  ⚠️  No price data found for industry '{industry}'")
            return []
        
        # Calculate index
        index_df = self.calculate_equal_weighted_index(prices_df, base_value)
        
        if index_df.empty:
            print(f"  ⚠️  Could not calculate index for industry '{industry}'")
            return []
        
        # Convert to list of dictionaries
        index_data = []
        for _, row in index_df.iterrows():
            index_data.append({
                'industry': industry,
                'date': row['date'],
                'index_value': float(row['index_value']),
                'stock_count': int(row['stock_count']),
                'base_value': base_value
            })
        
        return index_data
    
    def calculate_all_industry_indices(self, period_days: int = 365, base_value: float = 1000.0) -> Dict:
        """Calculate equal-weighted indices for all industries"""
        print(f"=== Calculating Equal-Weighted Industry Indices ===\n")
        
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"Period: {start_date} to {end_date} ({period_days} days)")
        print(f"Base index value: {base_value}")
        
        # Get all industries with sufficient stocks
        industries = self.index_model.get_industries_with_stocks()
        
        if not industries:
            print("❌ No industries found with sufficient stocks")
            return {'success': False, 'message': 'No industries found'}
        
        print(f"\nFound {len(industries)} industries with 3+ stocks:")
        for industry_info in industries[:10]:  # Show first 10
            print(f"  • {industry_info['industry']}: {industry_info['stock_count']} stocks")
        
        if len(industries) > 10:
            print(f"  ... and {len(industries) - 10} more industries")
        
        # Calculate indices for each industry
        print(f"\n=== Calculating Indices ===")
        
        all_index_data = []
        successful_industries = []
        failed_industries = []
        
        for i, industry_info in enumerate(industries, 1):
            industry = industry_info['industry']
            stock_count = industry_info['stock_count']
            
            print(f"\n{i}/{len(industries)}. Processing: {industry} ({stock_count} stocks)")
            
            try:
                index_data = self.calculate_industry_index(industry, start_date, end_date, base_value)
                
                if index_data:
                    all_index_data.extend(index_data)
                    successful_industries.append(industry)
                    print(f"  ✓ Generated {len(index_data)} data points")
                else:
                    failed_industries.append(industry)
                    print(f"  ✗ Failed to generate index")
                    
            except Exception as e:
                failed_industries.append(industry)
                print(f"  ✗ Error: {str(e)}")
        
        # Store in database
        if all_index_data:
            print(f"\n=== Storing Index Data ===")
            inserted_count = self.index_model.insert_index_data(all_index_data)
            print(f"✓ Inserted {inserted_count} index data points")
        
        # Summary
        print(f"\n=== Summary ===")
        print(f"Industries processed: {len(industries)}")
        print(f"Successful: {len(successful_industries)}")
        print(f"Failed: {len(failed_industries)}")
        print(f"Total data points generated: {len(all_index_data)}")
        
        if failed_industries:
            print(f"\nFailed industries:")
            for industry in failed_industries:
                print(f"  • {industry}")
        
        return {
            'success': True,
            'total_industries': len(industries),
            'successful_industries': successful_industries,
            'failed_industries': failed_industries,
            'total_data_points': len(all_index_data),
            'period_start': start_date,
            'period_end': end_date
        }
    
    def update_industry_index(self, industry: str, period_days: int = 365, base_value: float = 1000.0) -> bool:
        """Update index for a specific industry"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"Updating index for industry: {industry}")
        
        try:
            index_data = self.calculate_industry_index(industry, start_date, end_date, base_value)
            
            if index_data:
                inserted_count = self.index_model.insert_index_data(index_data)
                print(f"✓ Updated {inserted_count} data points for {industry}")
                return True
            else:
                print(f"✗ Failed to generate index data for {industry}")
                return False
                
        except Exception as e:
            print(f"✗ Error updating {industry}: {str(e)}")
            return False
    
    def get_index_statistics(self) -> Dict:
        """Get statistics about the indices"""
        query = """
        SELECT 
            COUNT(DISTINCT industry) as total_industries,
            COUNT(*) as total_data_points,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(stock_count) as avg_stocks_per_industry
        FROM equiweighted_index
        """
        
        result = self.db.execute_query(query)
        
        if result and result[0]:
            columns = ['total_industries', 'total_data_points', 'earliest_date', 'latest_date', 'avg_stocks_per_industry']
            stats = dict(zip(columns, result[0]))
            
            # Get top performing industries
            top_performers_query = """
            WITH latest_values AS (
                SELECT industry, MAX(date) as latest_date
                FROM equiweighted_index
                GROUP BY industry
            ),
            performance AS (
                SELECT 
                    ei.industry,
                    ei.index_value,
                    FIRST_VALUE(ei.index_value) OVER (
                        PARTITION BY ei.industry 
                        ORDER BY ei.date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    ) as first_value
                FROM equiweighted_index ei
                INNER JOIN latest_values lv ON ei.industry = lv.industry AND ei.date = lv.latest_date
            )
            SELECT 
                industry,
                ROUND(((index_value - first_value) / first_value * 100)::numeric, 2) as return_pct
            FROM performance
            ORDER BY return_pct DESC
            LIMIT 5
            """
            
            top_performers = self.db.execute_query(top_performers_query)
            if top_performers:
                stats['top_performers'] = [
                    {'industry': row[0], 'return_pct': float(row[1])} 
                    for row in top_performers
                ]
            
            return stats
        
        return {}