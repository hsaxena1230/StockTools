#!/usr/bin/env python3
"""
Daily Stock Market Calculations
Complete daily workflow for:
1. Update stock prices
2. Calculate equiweighted indices
3. Calculate momentum
4. Calculate relative strength

Designed to be run daily via cron job after market close
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.models.equiweighted_index import EquiweightedIndex
from src.models.momentum import Momentum
from src.models.relative_strength import RelativeStrength
from src.data.price_fetcher import PriceFetcher
from src.data.index_fetcher import IndexFetcher
from src.utils.momentum_calculator import MomentumCalculator
from src.utils.relative_strength_calculator import RelativeStrengthCalculator
import logging
import traceback

# Set up logging
def setup_logging():
    """Setup logging configuration"""
    os.makedirs('logs', exist_ok=True)
    
    # Create a unique log file for each day
    log_date = datetime.now().strftime('%Y-%m-%d')
    log_file = f'logs/daily_calculations_{log_date}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def update_stock_prices(db, logger):
    """Step 1: Update daily stock prices"""
    logger.info("=" * 60)
    logger.info("STEP 1: UPDATING STOCK PRICES")
    logger.info("=" * 60)
    
    try:
        stock_model = Stock(db)
        stock_price_model = StockPrice(db)
        price_fetcher = PriceFetcher()  # No database parameter
        index_fetcher = IndexFetcher()  # No database parameter
        
        calculation_date = datetime.now().date()
        logger.info(f"Updating stock prices for {calculation_date}")
        
        # Get all stocks
        stocks = stock_model.get_all_stocks()
        regular_stocks = [s for s in stocks if not s['symbol'].startswith('^') and s.get('sector') != 'INDEX']
        indices = [s for s in stocks if s['symbol'].startswith('^') or s.get('sector') == 'INDEX']
        
        logger.info(f"Found {len(regular_stocks)} regular stocks and {len(indices)} indices")
        
        # Update stock prices using batch method
        logger.info("Fetching latest stock prices...")
        stock_price_data = price_fetcher.fetch_latest_prices(regular_stocks)
        
        # Insert stock price data 
        stock_success = 0
        if stock_price_data:
            # Convert to the format expected by insert_price_data
            formatted_data = []
            for price_data in stock_price_data:
                if price_data.get('close_price'):
                    formatted_data.append({
                        'stock_id': price_data['stock_id'],
                        'close_price': price_data['close_price'],
                        'volume': price_data.get('volume', 0),
                        'date': calculation_date
                    })
            
            if formatted_data:
                stock_success = stock_price_model.insert_price_data(formatted_data)
        
        # Update index prices
        index_success = 0
        for index in indices:
            try:
                price_data = index_fetcher.fetch_latest_index_price(index['symbol'])
                if price_data and price_data.get('close_price'):
                    stock_price_model.insert_price_data([{
                        'stock_id': index['id'],
                        'close_price': price_data['close_price'],
                        'volume': price_data.get('volume', 0),
                        'date': calculation_date
                    }])
                    index_success += 1
            except Exception as e:
                logger.warning(f"Failed to update index {index['symbol']}: {e}")
        
        logger.info(f"✅ Stock prices updated: {stock_success} stocks, {index_success}/{len(indices)} indices")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating stock prices: {e}")
        logger.error(traceback.format_exc())
        return False

def calculate_equiweighted_indices(db, logger):
    """Step 2: Calculate equiweighted indices"""
    logger.info("=" * 60)
    logger.info("STEP 2: CALCULATING EQUIWEIGHTED INDICES")
    logger.info("=" * 60)
    
    try:
        from src.utils.index_calculator import IndexCalculator
        
        index_model = EquiweightedIndex(db)
        calculator = IndexCalculator(db)
        
        logger.info("Calculating equiweighted indices for recent period")
        
        # Create tables if needed
        index_model.create_table()
        
        # Calculate indices for last 30 days (this will include today if there's new data)
        # Using a shorter period for daily updates to be more efficient
        results = calculator.calculate_all_industry_indices(period_days=30, base_value=1000.0)
        
        if results and results.get('success'):
            industries_calculated = results.get('industries_calculated', 0)
            total_records = results.get('total_records', 0)
            logger.info(f"✅ Equiweighted indices calculated: {industries_calculated} industries, {total_records} records")
            return True
        else:
            error_msg = results.get('error', 'Unknown error') if results else 'No results returned'
            logger.error(f"❌ Failed to calculate equiweighted indices: {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error calculating equiweighted indices: {e}")
        logger.error(traceback.format_exc())
        return False

def calculate_momentum(db, logger):
    """Step 3: Calculate momentum"""
    logger.info("=" * 60)
    logger.info("STEP 3: CALCULATING MOMENTUM")
    logger.info("=" * 60)
    
    try:
        momentum_model = Momentum(db)
        calculator = MomentumCalculator(db)
        calculation_date = datetime.now().date()
        
        logger.info(f"Calculating momentum for {calculation_date}")
        
        # Create tables if needed
        momentum_model.create_table()
        
        # Calculate momentum for all entities
        results = calculator.calculate_all_momentum(calculation_date)
        
        if results and results.get('success'):
            total_records = results.get('total_records', 0)
            stocks_processed = results.get('stocks_processed', 0)
            industries_processed = results.get('industries_processed', 0)
            market_indices_processed = results.get('market_indices_processed', 0)
            
            logger.info(f"✅ Momentum calculated: {total_records} total records")
            logger.info(f"   - Stocks: {stocks_processed}")
            logger.info(f"   - Industries: {industries_processed}")
            logger.info(f"   - Market indices: {market_indices_processed}")
            return True
        else:
            logger.error("❌ Failed to calculate momentum")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error calculating momentum: {e}")
        logger.error(traceback.format_exc())
        return False

def calculate_relative_strength(db, logger):
    """Step 4: Calculate relative strength"""
    logger.info("=" * 60)
    logger.info("STEP 4: CALCULATING RELATIVE STRENGTH")
    logger.info("=" * 60)
    
    try:
        rs_model = RelativeStrength(db)
        calculator = RelativeStrengthCalculator(db)
        calculation_date = datetime.now().date()
        
        logger.info(f"Calculating relative strength for {calculation_date}")
        
        # Create tables if needed
        rs_model.create_table()
        
        # Calculate relative strength for all entities
        results = calculator.calculate_all_relative_strength(calculation_date)
        
        if results and results.get('success'):
            total_records = results.get('total_records', 0)
            stocks_processed = results.get('stocks_processed', 0)
            industries_processed = results.get('industries_processed', 0)
            
            logger.info(f"✅ Relative strength calculated: {total_records} total records")
            logger.info(f"   - Stocks: {stocks_processed}")
            logger.info(f"   - Industries: {industries_processed}")
            return True
        else:
            logger.error("❌ Failed to calculate relative strength")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error calculating relative strength: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main execution function"""
    logger = setup_logging()
    
    start_time = datetime.now()
    logger.info("🚀 STARTING DAILY STOCK MARKET CALCULATIONS")
    logger.info(f"Start time: {start_time}")
    logger.info("=" * 80)
    
    # Initialize database connection
    logger.info("Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        logger.error("❌ Failed to connect to database")
        return
    
    logger.info("✅ Connected to database")
    
    # Track success/failure of each step
    steps_results = {}
    
    try:
        # Step 1: Update stock prices
        steps_results['stock_prices'] = update_stock_prices(db, logger)
        
        # Step 2: Calculate equiweighted indices (only if stock prices succeeded)
        if steps_results['stock_prices']:
            steps_results['equiweighted_indices'] = calculate_equiweighted_indices(db, logger)
        else:
            logger.warning("⚠️ Skipping equiweighted indices due to stock price update failure")
            steps_results['equiweighted_indices'] = False
        
        # Step 3: Calculate momentum (only if previous steps succeeded)
        if steps_results['stock_prices'] and steps_results['equiweighted_indices']:
            steps_results['momentum'] = calculate_momentum(db, logger)
        else:
            logger.warning("⚠️ Skipping momentum calculation due to previous failures")
            steps_results['momentum'] = False
        
        # Step 4: Calculate relative strength (only if previous steps succeeded)
        if all(steps_results.values()):
            steps_results['relative_strength'] = calculate_relative_strength(db, logger)
        else:
            logger.warning("⚠️ Skipping relative strength calculation due to previous failures")
            steps_results['relative_strength'] = False
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in main execution: {e}")
        logger.error(traceback.format_exc())
    
    finally:
        # Clean up database connection
        db.close()
        logger.info("Database connection closed")
    
    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=" * 80)
    logger.info("📊 DAILY CALCULATIONS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Start time: {start_time}")
    logger.info(f"End time: {end_time}")
    logger.info(f"Duration: {duration}")
    logger.info("")
    logger.info("Step Results:")
    logger.info(f"  1. Stock Prices: {'✅ SUCCESS' if steps_results.get('stock_prices') else '❌ FAILED'}")
    logger.info(f"  2. Equiweighted Indices: {'✅ SUCCESS' if steps_results.get('equiweighted_indices') else '❌ FAILED'}")
    logger.info(f"  3. Momentum: {'✅ SUCCESS' if steps_results.get('momentum') else '❌ FAILED'}")
    logger.info(f"  4. Relative Strength: {'✅ SUCCESS' if steps_results.get('relative_strength') else '❌ FAILED'}")
    logger.info("")
    
    # Overall status
    all_success = all(steps_results.values())
    if all_success:
        logger.info("🎉 ALL DAILY CALCULATIONS COMPLETED SUCCESSFULLY!")
    else:
        failed_steps = [step for step, success in steps_results.items() if not success]
        logger.warning(f"⚠️ SOME STEPS FAILED: {', '.join(failed_steps)}")
    
    logger.info("=" * 80)
    
    # Exit with appropriate code
    sys.exit(0 if all_success else 1)

if __name__ == '__main__':
    main()