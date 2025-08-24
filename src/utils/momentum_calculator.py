import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.models.equiweighted_index import EquiweightedIndex
from src.models.momentum import Momentum

class MomentumCalculator:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.stock_model = Stock(db_connection)
        self.stock_price_model = StockPrice(db_connection)
        self.index_model = EquiweightedIndex(db_connection)
        self.momentum_model = Momentum(db_connection)
    
    def calculate_price_momentum(self, prices: List[float], current_price: float, target_price: float) -> Tuple[float, float]:
        """Calculate momentum and percentage change with validation"""
        if target_price is None or target_price == 0:
            return None, None
        
        try:
            momentum = current_price - target_price
            momentum_pct = (momentum / target_price) * 100
            
            # Validate momentum values to prevent database overflow
            # Cap extreme values to reasonable ranges
            if abs(momentum) > 999999:  # Cap absolute momentum
                momentum = 999999 if momentum > 0 else -999999
            
            if abs(momentum_pct) > 9999:  # Cap percentage momentum to +/- 9999%
                momentum_pct = 9999 if momentum_pct > 0 else -9999
            
            # Handle NaN or infinite values
            if not (np.isfinite(momentum) and np.isfinite(momentum_pct)):
                return None, None
            
            return momentum, momentum_pct
            
        except (ZeroDivisionError, OverflowError, ValueError):
            return None, None
    
    def find_price_by_calendar_days(self, price_df: pd.DataFrame, calculation_date: date, days_back: int, price_column: str = 'close_price') -> Optional[float]:
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
        # Fix the idxmax issue by using proper index selection
        max_date = available_dates['date_only'].max()
        closest_date_row = available_dates[available_dates['date_only'] == max_date].iloc[0]
        
        return float(closest_date_row[price_column])
    
    def calculate_volatility_by_calendar_days(self, price_df: pd.DataFrame, calculation_date: date, days_back: int = 30) -> Optional[float]:
        """Calculate volatility using calendar days lookback"""
        if price_df.empty:
            return None
        
        start_date = calculation_date - timedelta(days=days_back)
        
        # Convert dates to date objects for comparison
        price_df_copy = price_df.copy()
        price_df_copy['date_only'] = price_df_copy['date'].dt.date
        
        # Filter data for the specified calendar period
        period_data = price_df_copy[
            (price_df_copy['date_only'] >= start_date) & 
            (price_df_copy['date_only'] <= calculation_date)
        ]
        
        if len(period_data) < 2:
            return None
        
        # Get prices and calculate volatility
        period_prices = period_data['close_price'].tolist()
        return self.calculate_volatility(period_prices)
    
    def calculate_volume_by_calendar_days(self, price_df: pd.DataFrame, calculation_date: date, days_back: int = 30) -> Optional[int]:
        """Calculate average volume using calendar days lookback"""
        if price_df.empty:
            return None
        
        start_date = calculation_date - timedelta(days=days_back)
        
        # Convert dates to date objects for comparison
        price_df_copy = price_df.copy()
        price_df_copy['date_only'] = price_df_copy['date'].dt.date
        
        # Filter data for the specified calendar period
        period_data = price_df_copy[
            (price_df_copy['date_only'] >= start_date) & 
            (price_df_copy['date_only'] <= calculation_date)
        ]
        
        if period_data.empty:
            return None
        
        # Calculate average volume
        avg_volume = period_data['volume'].dropna().mean()
        return int(avg_volume) if pd.notna(avg_volume) else None
    
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
        closest_date_row = available_dates.loc[available_dates['date_only'].idxmax()]
        return float(closest_date_row['index_value'])
    
    def calculate_index_volatility_by_calendar_days(self, index_df: pd.DataFrame, calculation_date: date, days_back: int = 30) -> Optional[float]:
        """Calculate index volatility using calendar days lookback"""
        if index_df.empty:
            return None
        
        start_date = calculation_date - timedelta(days=days_back)
        
        # Convert dates to date objects for comparison
        index_df_copy = index_df.copy()
        index_df_copy['date_only'] = index_df_copy['date'].dt.date
        
        # Filter data for the specified calendar period
        period_data = index_df_copy[
            (index_df_copy['date_only'] >= start_date) & 
            (index_df_copy['date_only'] <= calculation_date)
        ]
        
        if len(period_data) < 2:
            return None
        
        # Get values and calculate volatility
        period_values = period_data['index_value'].tolist()
        return self.calculate_volatility(period_values)
    
    def calculate_volatility(self, prices: List[float]) -> Optional[float]:
        """Calculate 30-day volatility (standard deviation of returns) with validation"""
        if len(prices) < 2:
            return None
        
        try:
            # Calculate daily returns
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] != 0 and np.isfinite(prices[i]) and np.isfinite(prices[i-1]):
                    return_val = (prices[i] - prices[i-1]) / prices[i-1]
                    if np.isfinite(return_val) and abs(return_val) < 10:  # Cap extreme daily returns
                        returns.append(return_val)
            
            if len(returns) < 2:
                return None
            
            # Calculate standard deviation and annualize it
            volatility = np.std(returns) * np.sqrt(252)  # 252 trading days per year
            volatility_pct = float(volatility * 100)  # Convert to percentage
            
            # Cap volatility to reasonable range
            if volatility_pct > 999:
                volatility_pct = 999
            elif volatility_pct < 0:
                volatility_pct = 0
            
            return volatility_pct if np.isfinite(volatility_pct) else None
            
        except (ValueError, OverflowError):
            return None
    
    def get_stock_price_data(self, symbol: str, stock_id: int, end_date: date, days_back: int = 270) -> pd.DataFrame:
        """Get stock price data for momentum calculation"""
        start_date = end_date - timedelta(days=days_back)
        
        query = """
        SELECT time::date as date, close_price, volume
        FROM stock_prices
        WHERE stock_id = %s
        AND time::date >= %s
        AND time::date <= %s
        ORDER BY time::date
        """
        
        results = self.db.execute_query(query, (stock_id, start_date, end_date))
        
        if results:
            df = pd.DataFrame(results, columns=['date', 'close_price', 'volume'])
            df['date'] = pd.to_datetime(df['date'])
            df['close_price'] = pd.to_numeric(df['close_price'])
            df['volume'] = pd.to_numeric(df['volume'])
            return df
        
        return pd.DataFrame()
    
    def get_industry_index_data(self, industry: str, end_date: date, days_back: int = 270) -> pd.DataFrame:
        """Get industry index data for momentum calculation"""
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
    
    def calculate_stock_momentum(self, stock: Dict, calculation_date: date) -> Optional[Dict]:
        """Calculate momentum for a single stock"""
        try:
            # Get price data
            price_df = self.get_stock_price_data(stock['symbol'], stock['id'], calculation_date)
            
            if price_df.empty or len(price_df) < 30:
                return None
            
            # Get current price (most recent)
            current_price = float(price_df.iloc[-1]['close_price'])
            
            # Find prices for different periods using calendar days
            price_30d = self.find_price_by_calendar_days(price_df, calculation_date, 30)
            price_90d = self.find_price_by_calendar_days(price_df, calculation_date, 90)
            price_180d = self.find_price_by_calendar_days(price_df, calculation_date, 180)
            
            # Calculate momentum
            momentum_30d, momentum_30d_pct = self.calculate_price_momentum([], current_price, price_30d)
            momentum_90d, momentum_90d_pct = self.calculate_price_momentum([], current_price, price_90d)
            momentum_180d, momentum_180d_pct = self.calculate_price_momentum([], current_price, price_180d)
            
            # Calculate volatility (last 30 calendar days)
            volatility_30d = self.calculate_volatility_by_calendar_days(price_df, calculation_date, 30)
            
            # Calculate average volume (last 30 calendar days)
            volume_avg_30d = self.calculate_volume_by_calendar_days(price_df, calculation_date, 30)
            
            return {
                'symbol': stock['symbol'],
                'entity_type': 'STOCK',
                'entity_name': stock['name'],
                'date': calculation_date,
                'current_price': current_price,
                'price_30d': price_30d,
                'momentum_30d': momentum_30d,
                'momentum_30d_pct': momentum_30d_pct,
                'price_90d': price_90d,
                'momentum_90d': momentum_90d,
                'momentum_90d_pct': momentum_90d_pct,
                'price_180d': price_180d,
                'momentum_180d': momentum_180d,
                'momentum_180d_pct': momentum_180d_pct,
                'volatility_30d': volatility_30d,
                'volume_avg_30d': volume_avg_30d
            }
            
        except Exception as e:
            print(f"Error calculating momentum for {stock['symbol']}: {e}")
            return None
    
    def calculate_industry_momentum(self, industry: str, calculation_date: date) -> Optional[Dict]:
        """Calculate momentum for an industry index"""
        try:
            # Get index data
            index_df = self.get_industry_index_data(industry, calculation_date)
            
            if index_df.empty or len(index_df) < 30:
                return None
            
            # Get current index value (most recent)
            current_value = float(index_df.iloc[-1]['index_value'])
            
            # Find values for different periods using calendar days
            value_30d = self.find_index_value_by_calendar_days(index_df, calculation_date, 30)
            value_90d = self.find_index_value_by_calendar_days(index_df, calculation_date, 90)
            value_180d = self.find_index_value_by_calendar_days(index_df, calculation_date, 180)
            
            # Calculate momentum
            momentum_30d, momentum_30d_pct = self.calculate_price_momentum([], current_value, value_30d)
            momentum_90d, momentum_90d_pct = self.calculate_price_momentum([], current_value, value_90d)
            momentum_180d, momentum_180d_pct = self.calculate_price_momentum([], current_value, value_180d)
            
            # Calculate volatility (last 30 calendar days)
            volatility_30d = self.calculate_index_volatility_by_calendar_days(index_df, calculation_date, 30)
            
            return {
                'symbol': industry,
                'entity_type': 'INDUSTRY_INDEX',
                'entity_name': f"{industry} Industry Index",
                'date': calculation_date,
                'current_price': current_value,
                'price_30d': value_30d,
                'momentum_30d': momentum_30d,
                'momentum_30d_pct': momentum_30d_pct,
                'price_90d': value_90d,
                'momentum_90d': momentum_90d,
                'momentum_90d_pct': momentum_90d_pct,
                'price_180d': value_180d,
                'momentum_180d': momentum_180d,
                'momentum_180d_pct': momentum_180d_pct,
                'volatility_30d': volatility_30d,
                'volume_avg_30d': None  # Not applicable for indices
            }
            
        except Exception as e:
            print(f"Error calculating momentum for industry {industry}: {e}")
            return None
    
    def calculate_market_index_momentum(self, symbol: str, stock_id: int, name: str, calculation_date: date) -> Optional[Dict]:
        """Calculate momentum for market indices (Nifty, Sensex, etc.)"""
        try:
            # Get price data (same as stock but different entity type)
            price_df = self.get_stock_price_data(symbol, stock_id, calculation_date)
            
            if price_df.empty or len(price_df) < 30:
                return None
            
            # Get current price (most recent)
            current_price = float(price_df.iloc[-1]['close_price'])
            
            # Find prices for different periods using calendar days
            price_30d = self.find_price_by_calendar_days(price_df, calculation_date, 30)
            price_90d = self.find_price_by_calendar_days(price_df, calculation_date, 90)
            price_180d = self.find_price_by_calendar_days(price_df, calculation_date, 180)
            
            # Calculate momentum
            momentum_30d, momentum_30d_pct = self.calculate_price_momentum([], current_price, price_30d)
            momentum_90d, momentum_90d_pct = self.calculate_price_momentum([], current_price, price_90d)
            momentum_180d, momentum_180d_pct = self.calculate_price_momentum([], current_price, price_180d)
            
            # Calculate volatility (last 30 calendar days)
            volatility_30d = self.calculate_volatility_by_calendar_days(price_df, calculation_date, 30)
            
            return {
                'symbol': symbol,
                'entity_type': 'MARKET_INDEX',
                'entity_name': name,
                'date': calculation_date,
                'current_price': current_price,
                'price_30d': price_30d,
                'momentum_30d': momentum_30d,
                'momentum_30d_pct': momentum_30d_pct,
                'price_90d': price_90d,
                'momentum_90d': momentum_90d,
                'momentum_90d_pct': momentum_90d_pct,
                'price_180d': price_180d,
                'momentum_180d': momentum_180d,
                'momentum_180d_pct': momentum_180d_pct,
                'volatility_30d': volatility_30d,
                'volume_avg_30d': None  # Not applicable for indices
            }
            
        except Exception as e:
            print(f"Error calculating momentum for market index {symbol}: {e}")
            return None
    
    def calculate_all_momentum(self, calculation_date: Optional[date] = None) -> Dict:
        """Calculate momentum for all stocks and indices"""
        if calculation_date is None:
            calculation_date = datetime.now().date()
        
        print(f"=== Calculating Momentum for {calculation_date} ===\n")
        
        all_momentum_data = []
        
        # 1. Calculate stock momentum
        print("1. Calculating stock momentum...")
        stocks = self.stock_model.get_all_stocks()
        
        # Filter out indices from stocks
        regular_stocks = [s for s in stocks if not s['symbol'].startswith('^') and s.get('sector') != 'INDEX']
        
        print(f"   Found {len(regular_stocks)} regular stocks")
        
        stock_success = 0
        for i, stock in enumerate(regular_stocks, 1):
            if i % 100 == 0:
                print(f"   Progress: {i}/{len(regular_stocks)} stocks")
            
            momentum_data = self.calculate_stock_momentum(stock, calculation_date)
            if momentum_data:
                all_momentum_data.append(momentum_data)
                stock_success += 1
        
        print(f"   ✓ Successfully calculated momentum for {stock_success} stocks")
        
        # 2. Calculate industry index momentum
        print("\n2. Calculating industry index momentum...")
        industries = self.index_model.get_industries_with_stocks()
        
        print(f"   Found {len(industries)} industries")
        
        industry_success = 0
        for industry_info in industries:
            industry = industry_info['industry']
            momentum_data = self.calculate_industry_momentum(industry, calculation_date)
            if momentum_data:
                all_momentum_data.append(momentum_data)
                industry_success += 1
        
        print(f"   ✓ Successfully calculated momentum for {industry_success} industry indices")
        
        # 3. Calculate market index momentum
        print("\n3. Calculating market index momentum...")
        market_indices = [s for s in stocks if s['symbol'].startswith('^') or s.get('sector') == 'INDEX']
        
        print(f"   Found {len(market_indices)} market indices")
        
        market_success = 0
        for index in market_indices:
            momentum_data = self.calculate_market_index_momentum(
                index['symbol'], 
                index['id'], 
                index['name'], 
                calculation_date
            )
            if momentum_data:
                all_momentum_data.append(momentum_data)
                market_success += 1
        
        print(f"   ✓ Successfully calculated momentum for {market_success} market indices")
        
        # 4. Store in database
        print(f"\n4. Storing momentum data...")
        if all_momentum_data:
            inserted_count = self.momentum_model.insert_momentum_data(all_momentum_data)
            print(f"   ✓ Stored {inserted_count} momentum records")
        else:
            print("   ⚠️  No momentum data to store")
        
        # Summary
        print(f"\n=== Summary ===")
        print(f"Calculation date: {calculation_date}")
        print(f"Stocks processed: {stock_success}/{len(regular_stocks)}")
        print(f"Industry indices processed: {industry_success}/{len(industries)}")
        print(f"Market indices processed: {market_success}/{len(market_indices)}")
        print(f"Total momentum records: {len(all_momentum_data)}")
        
        return {
            'success': True,
            'calculation_date': calculation_date,
            'total_records': len(all_momentum_data),
            'stocks_processed': stock_success,
            'industries_processed': industry_success,
            'market_indices_processed': market_success,
            'stocks_failed': len(regular_stocks) - stock_success,
            'industries_failed': len(industries) - industry_success,
            'market_indices_failed': len(market_indices) - market_success
        }
    
    def update_momentum_for_symbol(self, symbol: str, calculation_date: Optional[date] = None) -> bool:
        """Update momentum for a specific symbol"""
        if calculation_date is None:
            calculation_date = datetime.now().date()
        
        # Find the symbol in database
        stocks = self.stock_model.get_all_stocks()
        stock = next((s for s in stocks if s['symbol'] == symbol), None)
        
        if not stock:
            print(f"Symbol {symbol} not found in database")
            return False
        
        momentum_data = None
        
        # Determine entity type and calculate accordingly
        if stock['symbol'].startswith('^') or stock.get('sector') == 'INDEX':
            momentum_data = self.calculate_market_index_momentum(
                stock['symbol'], stock['id'], stock['name'], calculation_date
            )
        else:
            momentum_data = self.calculate_stock_momentum(stock, calculation_date)
        
        if momentum_data:
            inserted = self.momentum_model.insert_momentum_data([momentum_data])
            if inserted > 0:
                print(f"✓ Updated momentum for {symbol}")
                return True
        
        print(f"✗ Failed to update momentum for {symbol}")
        return False
    
    def generate_industry_momentum_historical_2years(self, end_date: Optional[date] = None) -> Dict:
        """Generate all momentum data for industry indices for the last 2 years"""
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = end_date - timedelta(days=730)  # 2 years
        
        print(f"=== Generating 2-Year Historical Momentum for Industry Indices ===")
        print(f"Date range: {start_date} to {end_date}")
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
        
        # Get all dates that need momentum calculation
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
        
        print("Starting momentum calculations...")
        
        # Process each date
        for date_idx, calc_date in enumerate(calculation_dates, 1):
            if date_idx % 10 == 0 or date_idx == 1:
                print(f"Processing date {date_idx}/{len(calculation_dates)}: {calc_date}")
            
            momentum_batch = []
            
            # Calculate momentum for each industry on this date
            for industry in industries:
                try:
                    # Get industry index data
                    price_df = self.get_industry_index_data(industry, calc_date, days_back=270)
                    
                    if price_df.empty or len(price_df) < 30:
                        failed_calculations += 1
                        continue
                    
                    # Get current price (for this calculation date)
                    current_price = float(price_df.iloc[-1]['index_value'])
                    
                    # Calculate momentum periods (use 'index_value' column for industry indices)
                    momentum_30d = self.find_price_by_calendar_days(price_df, calc_date, 30, 'index_value')
                    momentum_90d = self.find_price_by_calendar_days(price_df, calc_date, 90, 'index_value')
                    momentum_180d = self.find_price_by_calendar_days(price_df, calc_date, 180, 'index_value')
                    
                    # Calculate momentum values
                    mom_30d, mom_30d_pct = self.calculate_price_momentum([], current_price, momentum_30d)
                    mom_90d, mom_90d_pct = self.calculate_price_momentum([], current_price, momentum_90d)
                    mom_180d, mom_180d_pct = self.calculate_price_momentum([], current_price, momentum_180d)
                    
                    # Calculate volatility and volume (simplified for indices)
                    volatility = self.calculate_volatility(price_df['index_value'].tolist())
                    volume_avg = 0  # Industry indices don't have volume
                    
                    # Create momentum record
                    momentum_data = {
                        'symbol': industry,
                        'entity_name': f"{industry} Industry Index",
                        'entity_type': 'INDUSTRY_INDEX',
                        'current_price': current_price,
                        'momentum_30d': mom_30d,
                        'momentum_30d_pct': mom_30d_pct,
                        'momentum_90d': mom_90d,
                        'momentum_90d_pct': mom_90d_pct,
                        'momentum_180d': mom_180d,
                        'momentum_180d_pct': mom_180d_pct,
                        'volatility_30d': volatility,
                        'volume_avg_30d': volume_avg,
                        'date': calc_date
                    }
                    
                    momentum_batch.append(momentum_data)
                    successful_calculations += 1
                    
                except Exception as e:
                    print(f"Error calculating momentum for {industry} on {calc_date}: {e}")
                    failed_calculations += 1
                
                processed_count += 1
                
                # Progress update
                if processed_count % 500 == 0:
                    progress = (processed_count / total_calculations) * 100
                    print(f"   Progress: {processed_count}/{total_calculations} ({progress:.1f}%)")
            
            # Insert batch for this date
            if momentum_batch:
                try:
                    inserted_count = self.momentum_model.insert_momentum_data(momentum_batch)
                    if date_idx % 30 == 0:  # Progress update every 30 days
                        print(f"   ✓ Inserted {inserted_count} records for {calc_date}")
                except Exception as e:
                    print(f"   ✗ Error inserting batch for {calc_date}: {e}")
        
        # Final summary
        print(f"\n=== 2-Year Historical Momentum Generation Complete ===")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Industries processed: {len(industries)}")
        print(f"Trading days processed: {len(calculation_dates)}")
        print(f"Successful calculations: {successful_calculations:,}")
        print(f"Failed calculations: {failed_calculations:,}")
        print(f"Success rate: {(successful_calculations/total_calculations*100):.1f}%")
        
        return {
            'success': True,
            'date_range': f"{start_date} to {end_date}",
            'industries_count': len(industries),
            'trading_days': len(calculation_dates),
            'total_calculations': total_calculations,
            'successful_calculations': successful_calculations,
            'failed_calculations': failed_calculations,
            'success_rate': round((successful_calculations/total_calculations*100), 1)
        }