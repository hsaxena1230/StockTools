#!/usr/bin/env python3
"""
Daily Stock Price Update
Fetches the latest closing prices for all stocks and updates the database
Designed to be run daily via cron job
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from config.database import DatabaseConnection
from src.models.stock import Stock
from src.models.stock_price import StockPrice
from src.data.price_fetcher import PriceFetcher
from src.data.index_fetcher import IndexFetcher
from src.utils.momentum_calculator import MomentumCalculator
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_price_update.log'),
        logging.StreamHandler()
    ]
)

def update_daily_prices():
    """Update latest stock prices - to be run daily"""
    logging.info("=== Starting Daily Price Update ===")
    
    # Initialize database connection
    logging.info("Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        logging.error("Failed to connect to database")
        return
    
    # Initialize models
    stock_model = Stock(db)
    stock_price_model = StockPrice(db)
    price_fetcher = PriceFetcher()
    
    try:
        # Get all stocks
        logging.info("Fetching stock list from database...")
        all_stocks = stock_model.get_all_stocks()
        
        if not all_stocks:
            logging.warning("No stocks found in database")
            return
        
        logging.info(f"Found {len(all_stocks)} stocks to update")
        
        # Check which stocks need updating
        stocks_to_update = []
        today = datetime.now().date()
        
        for stock in all_stocks:
            latest_date = stock_price_model.get_latest_price_date(stock['id'])
            
            if latest_date is None or latest_date.date() < today:
                stocks_to_update.append(stock)
        
        logging.info(f"{len(stocks_to_update)} stocks need price updates")
        
        if not stocks_to_update:
            logging.info("All stocks are up to date")
            return
        
        # Fetch latest prices for stocks
        logging.info("Fetching latest prices from Yahoo Finance...")
        latest_prices = price_fetcher.fetch_latest_prices(stocks_to_update)
        
        if latest_prices:
            # Insert prices
            inserted = stock_price_model.insert_price_data(latest_prices)
            logging.info(f"Successfully inserted {inserted} stock price records")
            
            # Log failed updates
            successful_symbols = {p['symbol'] for p in latest_prices}
            failed_stocks = [s for s in stocks_to_update if s['symbol'] not in successful_symbols]
            
            if failed_stocks:
                logging.warning(f"Failed to update {len(failed_stocks)} stocks:")
                for stock in failed_stocks[:10]:  # Log first 10 failures
                    logging.warning(f"  - {stock['symbol']}: {stock['name']}")
        else:
            logging.error("No stock prices were fetched successfully")
        
        # Fetch latest prices for indices
        logging.info("\nFetching latest index prices...")
        index_fetcher = IndexFetcher()
        
        # Get index symbols that exist in stocks table
        index_symbols = ['^CRSLDX', '^NSEI', '^NSEBANK', '^BSESN']
        indices_to_update = []
        
        for symbol in index_symbols:
            index_stock = next((s for s in all_stocks if s['symbol'] == symbol), None)
            if index_stock:
                indices_to_update.append(index_stock)
        
        if indices_to_update:
            logging.info(f"Updating {len(indices_to_update)} indices: {[idx['symbol'] for idx in indices_to_update]}")
            
            index_prices = []
            for index in indices_to_update:
                price_data = index_fetcher.fetch_latest_index_price(index['symbol'])
                if price_data:
                    price_data['stock_id'] = index['id']
                    index_prices.append(price_data)
                    logging.info(f"  ✓ {index['symbol']}: {price_data['close_price']} on {price_data['time'].strftime('%Y-%m-%d')}")
                else:
                    logging.warning(f"  ✗ {index['symbol']}: Failed to fetch price")
            
            if index_prices:
                inserted = stock_price_model.insert_price_data(index_prices)
                logging.info(f"Successfully inserted {inserted} index price records")
        else:
            logging.info("No indices found in stocks table to update")
        
        # Summary statistics
        logging.info("\n=== Update Summary ===")
        logging.info(f"Total stocks: {len(all_stocks)}")
        logging.info(f"Stocks needing update: {len(stocks_to_update)}")
        logging.info(f"Successfully updated stocks: {len(latest_prices) if latest_prices else 0}")
        logging.info(f"Successfully updated indices: {len(index_prices) if 'index_prices' in locals() else 0}")
        logging.info(f"Failed stock updates: {len(stocks_to_update) - (len(latest_prices) if latest_prices else 0)}")
        
        # Calculate daily momentum
        logging.info("\n=== Calculating Daily Momentum ===")
        try:
            momentum_calculator = MomentumCalculator(db)
            
            # Ensure momentum table exists
            from src.models.momentum import Momentum
            momentum_model = Momentum(db)
            momentum_model.create_table()
            
            # Calculate momentum for current date
            momentum_results = momentum_calculator.calculate_all_momentum()
            
            if momentum_results and momentum_results.get('success'):
                logging.info(f"✓ Calculated momentum for {momentum_results['total_records']} entities")
                logging.info(f"  - Stocks: {momentum_results['stocks_processed']}")
                logging.info(f"  - Industry indices: {momentum_results['industries_processed']}")
                logging.info(f"  - Market indices: {momentum_results['market_indices_processed']}")
            else:
                logging.warning("Failed to calculate momentum")
                
        except Exception as momentum_error:
            logging.error(f"Error calculating momentum: {momentum_error}")
            # Don't fail the entire process if momentum calculation fails
        
        # Calculate daily relative strength
        logging.info("\n=== Calculating Daily Relative Strength ===")
        try:
            from src.utils.relative_strength_calculator import RelativeStrengthCalculator
            from src.models.relative_strength import RelativeStrength
            
            rs_calculator = RelativeStrengthCalculator(db)
            
            # Ensure relative strength table exists
            rs_model = RelativeStrength(db)
            rs_model.create_table()
            
            # Calculate relative strength for current date
            rs_results = rs_calculator.calculate_all_relative_strength()
            
            if rs_results and rs_results.get('success'):
                logging.info(f"✓ Calculated relative strength for {rs_results['total_records']} entities")
                logging.info(f"  - Stocks: {rs_results['stocks_processed']}")
                logging.info(f"  - Industry indices: {rs_results['industries_processed']}")
                logging.info(f"  - Benchmark: {rs_results['benchmark_symbol']}")
            else:
                logging.warning("Failed to calculate relative strength")
                
        except Exception as rs_error:
            logging.error(f"Error calculating relative strength: {rs_error}")
            # Don't fail the entire process if relative strength calculation fails
        
    except Exception as e:
        logging.error(f"Error during daily update: {e}", exc_info=True)
    finally:
        db.close()
        logging.info("Database connection closed")
        logging.info("=== Daily Price Update Completed ===\n")

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Run the update
    update_daily_prices()