import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.models.equiweighted_index import EquiweightedIndex
from src.models.relative_strength import RelativeStrength

class RelativeStrengthCalculator:
    def __init__(self, db_connection: DatabaseConnection, benchmark_symbol: str = '^CRSLDX'):
        self.db = db_connection
        self.benchmark_symbol = benchmark_symbol
        self.stock_model = Stock(db_connection)
        self.stock_price_model = StockPrice(db_connection)
        self.index_model = EquiweightedIndex(db_connection)
        self.rs_model = RelativeStrength(db_connection)
    
    def calculate_mansfield_relative_strength(self, current_price: float, ma_200: float, benchmark_price: float, benchmark_ma_200: float) -> Optional[float]:
        """Calculate Mansfield Relative Strength: (Stock/Stock_MA200) / (Benchmark/Benchmark_MA200)"""
        try:
            if not all([current_price, ma_200, benchmark_price, benchmark_ma_200]):
                return None
            
            if ma_200 == 0 or benchmark_ma_200 == 0:
                return None
            
            # Calculate normalized ratios
            stock_ratio = current_price / ma_200
            benchmark_ratio = benchmark_price / benchmark_ma_200
            
            if benchmark_ratio == 0:
                return None
                
            # Mansfield RS = (Stock/StockMA) / (Benchmark/BenchmarkMA)
            mansfield_rs = stock_ratio / benchmark_ratio
            
            # Convert to percentage (1.0 = baseline, >1.0 = outperforming, <1.0 = underperforming)
            # Multiply by 100 to get percentage where 100 = baseline
            mansfield_rs_pct = mansfield_rs * 100
            
            # Cap extreme values
            if abs(mansfield_rs_pct) > 9999:
                mansfield_rs_pct = 9999 if mansfield_rs_pct > 0 else -9999
            
            # Handle NaN or infinite values
            if not np.isfinite(mansfield_rs_pct):
                return None
            
            return mansfield_rs_pct
            
        except (ZeroDivisionError, OverflowError, ValueError):
            return None

    def calculate_moving_average(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate simple moving average for given period"""
        if not prices or len(prices) < period:
            return None
        
        # Use the last 'period' prices
        recent_prices = prices[-period:]
        return sum(recent_prices) / len(recent_prices)

    def calculate_ma_trend(self, prices: List[float], ma_period: int = 200, trend_period: int = 5) -> Optional[bool]:
        """Calculate if moving average is trending up (True) or down (False)"""
        if not prices or len(prices) < ma_period + trend_period:
            # If we don't have enough data for trend comparison, use simpler method
            if len(prices) >= ma_period:
                # Compare last MA to first available MA as fallback
                available_data = len(prices) - ma_period
                if available_data >= 2:
                    current_ma = self.calculate_moving_average(prices, ma_period)
                    past_ma = self.calculate_moving_average(prices[:-1], ma_period)
                    return current_ma > past_ma if current_ma and past_ma else None
            return None
        
        # Calculate current MA and MA from trend_period days ago
        current_ma = self.calculate_moving_average(prices, ma_period)
        past_ma = self.calculate_moving_average(prices[:-trend_period], ma_period)
        
        if current_ma is None or past_ma is None:
            return None
        
        # Return True if MA is rising, False if falling
        return current_ma > past_ma

    def determine_weinstein_stage(self, current_price: float, ma_200: float, ma_trend_up: bool) -> int:
        """Determine Weinstein stage based on price vs MA and MA trend"""
        price_above_ma = current_price > ma_200
        
        if price_above_ma and ma_trend_up:
            return 2  # Stage 2 - Advancing (bullish)
        elif price_above_ma and not ma_trend_up:
            return 3  # Stage 3 - Distribution (bearish)
        elif not price_above_ma and not ma_trend_up:
            return 4  # Stage 4 - Declining (bearish)
        else:  # not price_above_ma and ma_trend_up
            return 1  # Stage 1 - Accumulation (bullish)

    def calculate_historical_mansfield_rs(self, stock_df: pd.DataFrame, benchmark_df: pd.DataFrame, 
                                        calculation_date: date, days_back: int) -> Optional[float]:
        """Calculate Mansfield RS for a historical date (days_back from calculation_date)"""
        try:
            target_date = calculation_date - timedelta(days=days_back)
            
            # Find stock data up to target date
            stock_historical = stock_df[stock_df['date'].dt.date <= target_date]
            benchmark_historical = benchmark_df[benchmark_df['date'].dt.date <= target_date]
            
            if len(stock_historical) < 200 or len(benchmark_historical) < 200:
                return None
            
            # Get prices at target date
            stock_price_at_date = float(stock_historical.iloc[-1]['close_price'])
            benchmark_price_at_date = float(benchmark_historical.iloc[-1]['close_price'])
            
            # Calculate 200-day MA at target date
            stock_prices_historical = stock_historical['close_price'].tolist()
            benchmark_prices_historical = benchmark_historical['close_price'].tolist()
            
            stock_ma_200 = self.calculate_moving_average(stock_prices_historical, 200)
            benchmark_ma_200 = self.calculate_moving_average(benchmark_prices_historical, 200)
            
            if not stock_ma_200 or not benchmark_ma_200:
                return None
            
            return self.calculate_mansfield_relative_strength(
                stock_price_at_date, stock_ma_200, benchmark_price_at_date, benchmark_ma_200
            )
            
        except Exception as e:
            return None

    def calculate_historical_mansfield_rs_industry(self, industry_df: pd.DataFrame, benchmark_df: pd.DataFrame, 
                                                  calculation_date: date, days_back: int) -> Optional[float]:
        """Calculate Mansfield RS for an industry at a historical date"""
        try:
            target_date = calculation_date - timedelta(days=days_back)
            
            # Find industry data up to target date
            industry_historical = industry_df[industry_df['date'].dt.date <= target_date]
            benchmark_historical = benchmark_df[benchmark_df['date'].dt.date <= target_date]
            
            if len(industry_historical) < 200 or len(benchmark_historical) < 200:
                return None
            
            # Get values at target date
            industry_value_at_date = float(industry_historical.iloc[-1]['index_value'])
            benchmark_price_at_date = float(benchmark_historical.iloc[-1]['close_price'])
            
            # Calculate 200-day MA at target date
            industry_values_historical = industry_historical['index_value'].tolist()
            benchmark_prices_historical = benchmark_historical['close_price'].tolist()
            
            industry_ma_200 = self.calculate_moving_average(industry_values_historical, 200)
            benchmark_ma_200 = self.calculate_moving_average(benchmark_prices_historical, 200)
            
            if not industry_ma_200 or not benchmark_ma_200:
                return None
            
            return self.calculate_mansfield_relative_strength(
                industry_value_at_date, industry_ma_200, benchmark_price_at_date, benchmark_ma_200
            )
            
        except Exception as e:
            return None

    def calculate_relative_strength(self, symbol_return: float, benchmark_return: float) -> Optional[float]:
        """Legacy method - kept for backward compatibility"""
        try:
            if benchmark_return == 0:
                return symbol_return if symbol_return is not None else None
            
            if symbol_return is None:
                return None
                
            relative_strength = ((symbol_return - benchmark_return) / benchmark_return) * 100
            
            # Cap extreme values to prevent database overflow
            if abs(relative_strength) > 9999:
                relative_strength = 9999 if relative_strength > 0 else -9999
            
            # Handle NaN or infinite values
            if not np.isfinite(relative_strength):
                return None
            
            return relative_strength
            
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
    
    def calculate_return(self, current_price: float, historical_price: float) -> Optional[float]:
        """Calculate percentage return between two prices"""
        if historical_price is None or historical_price == 0 or current_price is None:
            return None
        
        try:
            return_pct = ((current_price - historical_price) / historical_price) * 100
            
            # Cap extreme returns
            if abs(return_pct) > 9999:
                return_pct = 9999 if return_pct > 0 else -9999
            
            return return_pct if np.isfinite(return_pct) else None
            
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
    
    def find_price_by_calendar_days(self, price_df: pd.DataFrame, calculation_date: date, days_back: int) -> Optional[float]:
        """Find the closest available price for a specific number of calendar days back"""
        if price_df.empty:
            return None
        
        target_date = calculation_date - timedelta(days=days_back)
        
        # Convert dates to date objects for comparison
        price_df_copy = price_df.copy()
        price_df_copy['date_only'] = price_df_copy['date'].dt.date
        
        # Find the closest available date on or before the target date
        available_dates = price_df_copy[price_df_copy['date_only'] <= target_date]
        
        if available_dates.empty:
            return None
        
        # Get the most recent available date (closest to target)
        latest_available_date = available_dates['date_only'].max()
        closest_date_row = available_dates[available_dates['date_only'] == latest_available_date].iloc[-1]
        return float(closest_date_row['close_price'])
    
    def find_index_value_by_calendar_days(self, index_df: pd.DataFrame, calculation_date: date, days_back: int) -> Optional[float]:
        """Find the closest available index value for a specific number of calendar days back"""
        if index_df.empty:
            return None
        
        target_date = calculation_date - timedelta(days=days_back)
        
        # Convert dates to date objects for comparison
        index_df_copy = index_df.copy()
        index_df_copy['date_only'] = index_df_copy['date'].dt.date
        
        # Find the closest available date on or before the target date
        available_dates = index_df_copy[index_df_copy['date_only'] <= target_date]
        
        if available_dates.empty:
            return None
        
        # Get the most recent available date (closest to target)
        latest_available_date = available_dates['date_only'].max()
        closest_date_row = available_dates[available_dates['date_only'] == latest_available_date].iloc[-1]
        return float(closest_date_row['index_value'])
    
    def get_benchmark_price_data(self, end_date: date, days_back: int = 300) -> pd.DataFrame:
        """Get benchmark (Nifty 500) price data - increased to 300 days for 200-day MA"""
        start_date = end_date - timedelta(days=days_back)
        
        # First, get the benchmark stock_id
        benchmark_stock_query = """
        SELECT id FROM stocks WHERE symbol = %s
        """
        
        result = self.db.execute_query(benchmark_stock_query, (self.benchmark_symbol,))
        if not result:
            print(f"Benchmark symbol {self.benchmark_symbol} not found in stocks table")
            return pd.DataFrame()
        
        benchmark_stock_id = result[0][0]
        
        query = """
        SELECT time::date as date, close_price
        FROM stock_prices
        WHERE stock_id = %s
        AND time::date >= %s
        AND time::date <= %s
        ORDER BY time::date
        """
        
        results = self.db.execute_query(query, (benchmark_stock_id, start_date, end_date))
        
        if results:
            df = pd.DataFrame(results, columns=['date', 'close_price'])
            df['date'] = pd.to_datetime(df['date'])
            df['close_price'] = pd.to_numeric(df['close_price'])
            return df
        
        return pd.DataFrame()
    
    def get_stock_price_data(self, symbol: str, stock_id: int, end_date: date, days_back: int = 300) -> pd.DataFrame:
        """Get stock price data for relative strength calculation - increased to 300 days for 200-day MA"""
        start_date = end_date - timedelta(days=days_back)
        
        query = """
        SELECT time::date as date, close_price
        FROM stock_prices
        WHERE stock_id = %s
        AND time::date >= %s
        AND time::date <= %s
        ORDER BY time::date
        """
        
        results = self.db.execute_query(query, (stock_id, start_date, end_date))
        
        if results:
            df = pd.DataFrame(results, columns=['date', 'close_price'])
            df['date'] = pd.to_datetime(df['date'])
            df['close_price'] = pd.to_numeric(df['close_price'])
            return df
        
        return pd.DataFrame()
    
    def get_industry_index_data(self, industry: str, end_date: date, days_back: int = 300) -> pd.DataFrame:
        """Get industry index data for relative strength calculation - increased to 300 days for 200-day MA"""
        start_date = end_date - timedelta(days=days_back)
        
        query = """
        SELECT date, index_value
        FROM equiweighted_index
        WHERE industry = %s
        AND date >= %s
        AND date <= %s
        ORDER BY date
        """
        
        results = self.db.execute_query(query, (industry, start_date, end_date))
        
        if results:
            df = pd.DataFrame(results, columns=['date', 'index_value'])
            df['date'] = pd.to_datetime(df['date'])
            df['index_value'] = pd.to_numeric(df['index_value'])
            return df
        
        return pd.DataFrame()
    
    def calculate_stock_relative_strength(self, stock: Dict, benchmark_df: pd.DataFrame, calculation_date: date) -> Optional[Dict]:
        """Calculate Mansfield Relative Strength for a single stock"""
        try:
            # Get stock price data (need more history for 200-day MA)
            stock_df = self.get_stock_price_data(stock['symbol'], stock['id'], calculation_date)
            
            if stock_df.empty or len(stock_df) < 200 or benchmark_df.empty or len(benchmark_df) < 30:
                return None
            
            # Get current prices
            current_price = float(stock_df.iloc[-1]['close_price'])
            
            # Find corresponding benchmark price for the same date
            stock_current_date = stock_df.iloc[-1]['date'].date()
            benchmark_current = benchmark_df[benchmark_df['date'].dt.date == stock_current_date]
            
            if benchmark_current.empty:
                # If exact date not found, get the closest date
                benchmark_current = benchmark_df.iloc[-1:]
            
            benchmark_price = float(benchmark_current.iloc[-1]['close_price'])
            
            # Calculate current 200-day moving averages
            stock_prices = stock_df['close_price'].tolist()
            benchmark_prices = benchmark_df['close_price'].tolist()
            
            stock_ma_200 = self.calculate_moving_average(stock_prices, 200)
            benchmark_ma_200 = self.calculate_moving_average(benchmark_prices, min(200, len(benchmark_prices)//2))
            
            if not stock_ma_200 or not benchmark_ma_200:
                return None
            
            # Calculate MA trends for Weinstein stage analysis
            stock_ma_trend_up = self.calculate_ma_trend(stock_prices, 200, 20)
            benchmark_ma_trend_up = self.calculate_ma_trend(benchmark_prices, 200, 20)
            
            # Determine Weinstein stage
            stock_weinstein_stage = self.determine_weinstein_stage(current_price, stock_ma_200, stock_ma_trend_up or False)
            benchmark_weinstein_stage = self.determine_weinstein_stage(benchmark_price, benchmark_ma_200, benchmark_ma_trend_up or False)
            
            # Calculate Mansfield RS for current period
            current_rs = self.calculate_mansfield_relative_strength(
                current_price, stock_ma_200, benchmark_price, benchmark_ma_200
            )
            
            # Calculate Mansfield RS for different periods (30d, 90d, 180d ago)
            rs_30d = self.calculate_historical_mansfield_rs(stock_df, benchmark_df, calculation_date, 30)
            rs_90d = self.calculate_historical_mansfield_rs(stock_df, benchmark_df, calculation_date, 90)
            rs_180d = self.calculate_historical_mansfield_rs(stock_df, benchmark_df, calculation_date, 180)
            
            # Also calculate legacy returns for compatibility
            stock_price_30d = self.find_price_by_calendar_days(stock_df, calculation_date, 30)
            stock_price_90d = self.find_price_by_calendar_days(stock_df, calculation_date, 90)
            stock_price_180d = self.find_price_by_calendar_days(stock_df, calculation_date, 180)
            
            benchmark_price_30d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 30)
            benchmark_price_90d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 90)
            benchmark_price_180d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 180)
            
            symbol_return_30d = self.calculate_return(current_price, stock_price_30d)
            symbol_return_90d = self.calculate_return(current_price, stock_price_90d)
            symbol_return_180d = self.calculate_return(current_price, stock_price_180d)
            
            benchmark_return_30d = self.calculate_return(benchmark_price, benchmark_price_30d)
            benchmark_return_90d = self.calculate_return(benchmark_price, benchmark_price_90d)
            benchmark_return_180d = self.calculate_return(benchmark_price, benchmark_price_180d)
            
            return {
                'symbol': stock['symbol'],
                'entity_type': 'STOCK',
                'entity_name': stock['name'],
                'date': calculation_date,
                'benchmark_symbol': self.benchmark_symbol,
                'current_price': current_price,
                'benchmark_price': benchmark_price,
                'price_30d': stock_price_30d,
                'price_90d': stock_price_90d,
                'price_180d': stock_price_180d,
                'benchmark_price_30d': benchmark_price_30d,
                'benchmark_price_90d': benchmark_price_90d,
                'benchmark_price_180d': benchmark_price_180d,
                'symbol_return_30d': symbol_return_30d,
                'symbol_return_90d': symbol_return_90d,
                'symbol_return_180d': symbol_return_180d,
                'benchmark_return_30d': benchmark_return_30d,
                'benchmark_return_90d': benchmark_return_90d,
                'benchmark_return_180d': benchmark_return_180d,
                # Use Mansfield RS values (30d/90d/180d represent RS calculated for those historical periods)
                'relative_strength_30d': rs_30d or current_rs,  # Fallback to current if historical not available
                'relative_strength_90d': rs_90d or current_rs,
                'relative_strength_180d': rs_180d or current_rs,
                # Weinstein stage analysis data
                'stock_ma_200': stock_ma_200,
                'stock_ma_trend_up': stock_ma_trend_up,
                'weinstein_stage': stock_weinstein_stage,
                'benchmark_weinstein_stage': benchmark_weinstein_stage
            }
            
        except Exception as e:
            print(f"Error calculating relative strength for {stock['symbol']}: {e}")
            return None
    
    def calculate_industry_relative_strength(self, industry: str, benchmark_df: pd.DataFrame, calculation_date: date) -> Optional[Dict]:
        """Calculate Mansfield Relative Strength for an industry index"""
        try:
            # Get industry index data
            industry_df = self.get_industry_index_data(industry, calculation_date)
            
            if industry_df.empty or len(industry_df) < 30 or benchmark_df.empty or len(benchmark_df) < 30:
                return None
            
            # Get current values
            current_value = float(industry_df.iloc[-1]['index_value'])
            
            # Find corresponding benchmark price for the same date
            industry_current_date = industry_df.iloc[-1]['date'].date()
            benchmark_current = benchmark_df[benchmark_df['date'].dt.date == industry_current_date]
            
            if benchmark_current.empty:
                # If exact date not found, get the closest date
                benchmark_current = benchmark_df.iloc[-1:]
            
            benchmark_price = float(benchmark_current.iloc[-1]['close_price'])
            
            # Calculate current 200-day moving averages
            industry_values = industry_df['index_value'].tolist()
            benchmark_prices = benchmark_df['close_price'].tolist()
            
            industry_ma_200 = self.calculate_moving_average(industry_values, min(200, len(industry_values)//2))
            benchmark_ma_200 = self.calculate_moving_average(benchmark_prices, min(200, len(benchmark_prices)//2))
            
            if not industry_ma_200 or not benchmark_ma_200:
                return None
            
            # Calculate MA trends for Weinstein stage analysis
            industry_ma_trend_up = self.calculate_ma_trend(industry_values, 200, 20)
            benchmark_ma_trend_up = self.calculate_ma_trend(benchmark_prices, 200, 20)
            
            # Determine Weinstein stage
            industry_weinstein_stage = self.determine_weinstein_stage(current_value, industry_ma_200, industry_ma_trend_up or False)
            benchmark_weinstein_stage = self.determine_weinstein_stage(benchmark_price, benchmark_ma_200, benchmark_ma_trend_up or False)
            
            # Calculate Mansfield RS for current period
            current_rs = self.calculate_mansfield_relative_strength(
                current_value, industry_ma_200, benchmark_price, benchmark_ma_200
            )
            
            # Calculate Mansfield RS for different periods (30d, 90d, 180d ago)
            rs_30d = self.calculate_historical_mansfield_rs_industry(industry_df, benchmark_df, calculation_date, 30)
            rs_90d = self.calculate_historical_mansfield_rs_industry(industry_df, benchmark_df, calculation_date, 90)
            rs_180d = self.calculate_historical_mansfield_rs_industry(industry_df, benchmark_df, calculation_date, 180)
            
            # Also calculate legacy values for compatibility
            industry_value_30d = self.find_index_value_by_calendar_days(industry_df, calculation_date, 30)
            industry_value_90d = self.find_index_value_by_calendar_days(industry_df, calculation_date, 90)
            industry_value_180d = self.find_index_value_by_calendar_days(industry_df, calculation_date, 180)
            
            benchmark_price_30d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 30)
            benchmark_price_90d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 90)
            benchmark_price_180d = self.find_price_by_calendar_days(benchmark_df, calculation_date, 180)
            
            # Calculate returns
            symbol_return_30d = self.calculate_return(current_value, industry_value_30d)
            symbol_return_90d = self.calculate_return(current_value, industry_value_90d)
            symbol_return_180d = self.calculate_return(current_value, industry_value_180d)
            
            benchmark_return_30d = self.calculate_return(benchmark_price, benchmark_price_30d)
            benchmark_return_90d = self.calculate_return(benchmark_price, benchmark_price_90d)
            benchmark_return_180d = self.calculate_return(benchmark_price, benchmark_price_180d)
            
            return {
                'symbol': industry,
                'entity_type': 'INDUSTRY_INDEX',
                'entity_name': f"{industry} Industry Index",
                'date': calculation_date,
                'benchmark_symbol': self.benchmark_symbol,
                'current_price': current_value,
                'benchmark_price': benchmark_price,
                'price_30d': industry_value_30d,
                'price_90d': industry_value_90d,
                'price_180d': industry_value_180d,
                'benchmark_price_30d': benchmark_price_30d,
                'benchmark_price_90d': benchmark_price_90d,
                'benchmark_price_180d': benchmark_price_180d,
                'symbol_return_30d': symbol_return_30d,
                'symbol_return_90d': symbol_return_90d,
                'symbol_return_180d': symbol_return_180d,
                'benchmark_return_30d': benchmark_return_30d,
                'benchmark_return_90d': benchmark_return_90d,
                'benchmark_return_180d': benchmark_return_180d,
                # Use Mansfield RS values
                'relative_strength_30d': rs_30d or current_rs,  # Fallback to current if historical not available
                'relative_strength_90d': rs_90d or current_rs,
                'relative_strength_180d': rs_180d or current_rs,
                # Weinstein stage analysis data
                'industry_ma_200': industry_ma_200,
                'industry_ma_trend_up': industry_ma_trend_up,
                'weinstein_stage': industry_weinstein_stage,
                'benchmark_weinstein_stage': benchmark_weinstein_stage
            }
            
        except Exception as e:
            print(f"Error calculating relative strength for industry {industry}: {e}")
            return None
    
    def calculate_all_relative_strength(self, calculation_date: Optional[date] = None) -> Dict:
        """Calculate relative strength for all stocks and industry indices"""
        if calculation_date is None:
            calculation_date = datetime.now().date()
        
        print(f"=== Calculating Relative Strength for {calculation_date} ===")
        print(f"Benchmark: {self.benchmark_symbol}")
        print()
        
        all_rs_data = []
        
        # Get benchmark data first
        print("1. Loading benchmark data...")
        benchmark_df = self.get_benchmark_price_data(calculation_date)
        
        if benchmark_df.empty:
            print(f"❌ No benchmark data found for {self.benchmark_symbol}")
            return {'success': False, 'error': 'No benchmark data'}
        
        print(f"✅ Loaded {len(benchmark_df)} benchmark price records")
        
        # 2. Calculate stock relative strength
        print("\n2. Calculating stock relative strength...")
        stocks = self.stock_model.get_all_stocks()
        
        # Filter out indices from stocks and exclude the benchmark itself
        regular_stocks = [s for s in stocks if not s['symbol'].startswith('^') 
                         and s.get('sector') != 'INDEX' 
                         and s['symbol'] != self.benchmark_symbol]
        
        print(f"   Found {len(regular_stocks)} regular stocks")
        
        stock_success = 0
        for i, stock in enumerate(regular_stocks, 1):
            if i % 100 == 0:
                print(f"   Progress: {i}/{len(regular_stocks)} stocks")
            
            rs_data = self.calculate_stock_relative_strength(stock, benchmark_df, calculation_date)
            if rs_data:
                all_rs_data.append(rs_data)
                stock_success += 1
        
        print(f"   ✓ Successfully calculated relative strength for {stock_success} stocks")
        
        # 3. Calculate industry index relative strength
        print("\n3. Calculating industry index relative strength...")
        industries = self.index_model.get_industries_with_stocks()
        
        print(f"   Found {len(industries)} industries")
        
        industry_success = 0
        for industry_info in industries:
            industry = industry_info['industry']
            rs_data = self.calculate_industry_relative_strength(industry, benchmark_df, calculation_date)
            if rs_data:
                all_rs_data.append(rs_data)
                industry_success += 1
        
        print(f"   ✓ Successfully calculated relative strength for {industry_success} industry indices")
        
        # 4. Store in database
        print(f"\n4. Storing relative strength data...")
        if all_rs_data:
            inserted_count = self.rs_model.insert_relative_strength_data(all_rs_data)
            print(f"   ✓ Stored {inserted_count} relative strength records")
        else:
            print("   ⚠️  No relative strength data to store")
        
        # Summary
        print(f"\n=== Summary ===")
        print(f"Calculation date: {calculation_date}")
        print(f"Benchmark: {self.benchmark_symbol}")
        print(f"Stocks processed: {stock_success}/{len(regular_stocks)}")
        print(f"Industry indices processed: {industry_success}/{len(industries)}")
        print(f"Total relative strength records: {len(all_rs_data)}")
        
        return {
            'success': True,
            'calculation_date': calculation_date,
            'benchmark_symbol': self.benchmark_symbol,
            'total_records': len(all_rs_data),
            'stocks_processed': stock_success,
            'industries_processed': industry_success,
            'stocks_failed': len(regular_stocks) - stock_success,
            'industries_failed': len(industries) - industry_success
        }
    
    def update_relative_strength_for_symbol(self, symbol: str, calculation_date: Optional[date] = None) -> bool:
        """Update relative strength for a specific symbol"""
        if calculation_date is None:
            calculation_date = datetime.now().date()
        
        # Get benchmark data
        benchmark_df = self.get_benchmark_price_data(calculation_date)
        if benchmark_df.empty:
            print(f"No benchmark data found for {self.benchmark_symbol}")
            return False
        
        # Find the symbol in database
        stocks = self.stock_model.get_all_stocks()
        stock = next((s for s in stocks if s['symbol'] == symbol), None)
        
        if not stock:
            print(f"Symbol {symbol} not found in database")
            return False
        
        # Check if it's an industry index
        industries = self.index_model.get_industries_with_stocks()
        industry_names = [ind['industry'] for ind in industries]
        
        rs_data = None
        
        if symbol in industry_names:
            # It's an industry index
            rs_data = self.calculate_industry_relative_strength(symbol, benchmark_df, calculation_date)
        else:
            # It's a stock
            rs_data = self.calculate_stock_relative_strength(stock, benchmark_df, calculation_date)
        
        if rs_data:
            inserted = self.rs_model.insert_relative_strength_data([rs_data])
            if inserted > 0:
                print(f"✓ Updated relative strength for {symbol}")
                return True
        
        print(f"✗ Failed to update relative strength for {symbol}")
        return False
    
    def generate_industry_relative_strength_historical_2years(self, end_date: Optional[date] = None) -> Dict:
        """Generate all relative strength data for industry indices for the last 2 years"""
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = end_date - timedelta(days=730)  # 2 years
        
        print(f"=== Generating 2-Year Historical Relative Strength for Industry Indices ===")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Benchmark: {self.benchmark_symbol}")
        print(f"Total days: 730\n")
        
        # Get all industries from equiweighted_index table
        industries_query = """
        SELECT DISTINCT industry 
        FROM equiweighted_index 
        WHERE date >= %s AND date <= %s
        ORDER BY industry
        """
        
        industry_results = self.db.execute_query(industries_query, (start_date, end_date))
        if not industry_results:
            return {
                'success': False,
                'error': 'No industry data found in equiweighted_index table',
                'date_range': f"{start_date} to {end_date}"
            }
        
        industries = [row[0] for row in industry_results]
        print(f"Found {len(industries)} industries: {', '.join(industries[:5])}{'...' if len(industries) > 5 else ''}\n")
        
        # Get all dates that need relative strength calculation
        dates_query = """
        SELECT DISTINCT date 
        FROM equiweighted_index 
        WHERE date >= %s AND date <= %s
        ORDER BY date
        """
        
        date_results = self.db.execute_query(dates_query, (start_date, end_date))
        if not date_results:
            return {
                'success': False,
                'error': 'No date data found in equiweighted_index table'
            }
        
        calculation_dates = [row[0] for row in date_results]
        print(f"Found {len(calculation_dates)} trading days to calculate\n")
        
        # Track progress
        total_calculations = len(industries) * len(calculation_dates)
        successful_calculations = 0
        failed_calculations = 0
        processed_count = 0
        
        print("Starting relative strength calculations...")
        
        # Process each date
        for date_idx, calc_date in enumerate(calculation_dates, 1):
            if date_idx % 10 == 0 or date_idx == 1:
                print(f"Processing date {date_idx}/{len(calculation_dates)}: {calc_date}")
            
            # Get benchmark data for this date
            benchmark_df = self.get_benchmark_price_data(calc_date, days_back=270)
            
            if benchmark_df.empty:
                print(f"   No benchmark data for {calc_date}, skipping...")
                failed_calculations += len(industries)
                processed_count += len(industries)
                continue
            
            rs_batch = []
            
            # Calculate relative strength for each industry on this date
            for industry in industries:
                try:
                    # Calculate industry relative strength
                    rs_data = self.calculate_industry_relative_strength(industry, benchmark_df, calc_date)
                    
                    if rs_data:
                        rs_batch.append(rs_data)
                        successful_calculations += 1
                    else:
                        failed_calculations += 1
                    
                except Exception as e:
                    print(f"Error calculating relative strength for {industry} on {calc_date}: {e}")
                    failed_calculations += 1
                
                processed_count += 1
                
                # Progress update
                if processed_count % 500 == 0:
                    progress = (processed_count / total_calculations) * 100
                    print(f"   Progress: {processed_count}/{total_calculations} ({progress:.1f}%)")
            
            # Insert batch for this date
            if rs_batch:
                try:
                    inserted_count = self.rs_model.insert_relative_strength_data(rs_batch)
                    if date_idx % 30 == 0:  # Progress update every 30 days
                        print(f"   ✓ Inserted {inserted_count} records for {calc_date}")
                except Exception as e:
                    print(f"   ✗ Error inserting batch for {calc_date}: {e}")
        
        # Final summary
        print(f"\n=== 2-Year Historical Relative Strength Generation Complete ===")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Benchmark: {self.benchmark_symbol}")
        print(f"Industries processed: {len(industries)}")
        print(f"Trading days processed: {len(calculation_dates)}")
        print(f"Successful calculations: {successful_calculations:,}")
        print(f"Failed calculations: {failed_calculations:,}")
        print(f"Success rate: {(successful_calculations/total_calculations*100):.1f}%")
        
        return {
            'success': True,
            'date_range': f"{start_date} to {end_date}",
            'benchmark_symbol': self.benchmark_symbol,
            'industries_count': len(industries),
            'trading_days': len(calculation_dates),
            'total_calculations': total_calculations,
            'successful_calculations': successful_calculations,
            'failed_calculations': failed_calculations,
            'success_rate': round((successful_calculations/total_calculations*100), 1)
        }