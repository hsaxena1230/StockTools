# Stock Tools - Complete Setup and Usage Guide

## System Requirements
- Python 3.8+
- PostgreSQL 12+
- 4GB+ RAM recommended
- Internet connection for data fetching

## Initial Setup

### 1. Clone and Set Up Project
```bash
# Clone the repository (if using git)
git clone https://github.com/hsaxena1230/StockTools.git
cd StockTools

# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. PostgreSQL Database Setup
```bash
# Create database and user
psql -U postgres
CREATE DATABASE stock_tools;
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE stock_tools TO your_username;
\q
```

### 4. Configure Environment Variables
```bash
# Create .env file from example
cp .env.example .env

# Edit .env with your database credentials:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=stock_tools
# DB_USER=your_username
# DB_PASSWORD=your_password
```

## Data Loading Commands

### Step 1: Load Stock Lists
```bash
# Load NSE stocks
python load_nse_stocks.py

# Load BSE stocks
python main.py

# Load Nifty 500 data
python fetch_nifty_500_data.py
```

### Step 2: Fetch Historical Stock Prices
```bash
# Fetch 10 years of historical data (first-time setup)
python fetch_historical_prices.py

# This may take several hours depending on the number of stocks
```

### Step 3: Create Industry Indices
```bash
# Create equiweighted industry indices
python create_indices.py
```

### Step 4: Calculate Historical Momentum
```bash
# Calculate 180-day historical momentum
echo "180" | python calculate_momentum.py --action historical

# Calculate current momentum for all periods
python calculate_momentum.py --action calculate
```

### Step 5: Calculate Relative Strength
```bash
# Calculate historical relative strength
python calculate_relative_strength.py --action historical

# Calculate current relative strength
python calculate_relative_strength.py --action calculate
```

### Step 6: Generate Industry Analysis (2-Year)
```bash
# Generate 2-year industry momentum
timeout 60 python3 generate_industry_momentum_2years.py

# Generate 2-year industry relative strength
python generate_industry_relative_strength_2years.py

# If needed, continue or fix calculations
python continue_industry_relative_strength_2years.py
python fix_industry_relative_strength_2years.py
```

## Daily Operations

### Manual Daily Update
```bash
# Update daily stock prices
python update_daily_prices.py

# Run complete daily calculations (prices + indices + momentum + RS)
python daily_calculations.py
```

### Automated Daily Updates (Cron)
```bash
# Set up automated daily updates (runs at 6:30 PM IST Mon-Fri)
./setup_cron.sh

# View current cron jobs
crontab -l

# Monitor daily execution logs
tail -f logs/daily_calculations_$(date +%Y-%m-%d).log
```

## Web Interface

### Start the Web Application
```bash
# Using virtual environment
/Users/harshitsaxena/Desktop/StockTools/.venv/bin/python web/app.py

# OR standard Python
python web/app.py
```

The web interface will be available at `http://localhost:5000` and provides:
- Stock momentum and relative strength visualization
- Industry analysis dashboard
- Journey charts (smoothed and regular)
- Quadrant analysis

## Visualization and Analysis

### Generate Plots and Charts
```bash
# The web interface provides interactive charts at:
# http://localhost:5000/ - Main dashboard
# http://localhost:5000/industry_analysis - Industry analysis
# http://localhost:5000/journey - Stock journey visualization
# http://localhost:5000/journey_smoothed - Smoothed journey charts
```

## Utility Commands

### Data Validation and Fixes
```bash
# Find stocks without prices
python find_stocks_without_prices.py

# Find missing sector stocks
python find_missing_sector_stocks.py

# Query missing stocks
python query_missing_stocks.py

# Resolve missing symbols
python resolve_missing_symbols.py
```

### Testing
```bash
# Test daily calculations interactively
python test_daily_calculations.py --interactive

# Quick test daily operations
python quick_test_daily.py

# Test journey API
python test_journey_api.py
```

## Database Queries

### Check Data Status
```bash
psql -d stock_tools -c "SELECT COUNT(*) FROM stocks;"
psql -d stock_tools -c "SELECT COUNT(*) FROM stock_prices;"
psql -d stock_tools -c "SELECT COUNT(*) FROM momentum;"
psql -d stock_tools -c "SELECT COUNT(*) FROM relative_strength;"
```

### View Recent Calculations
```bash
psql -d stock_tools -c "SELECT * FROM momentum ORDER BY calculation_date DESC LIMIT 10;"
psql -d stock_tools -c "SELECT * FROM relative_strength ORDER BY calculation_date DESC LIMIT 10;"
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running: `pg_ctl status`
   - Check .env file credentials
   - Test connection: `psql -h localhost -U your_username -d stock_tools`

2. **Missing Data**
   - Run `python find_stocks_without_prices.py` to identify gaps
   - Re-run `python fetch_historical_prices.py` for missing stocks

3. **Cron Job Not Running**
   - Check cron service: `service cron status` (Linux) or `launchctl list | grep cron` (macOS)
   - Review logs: `tail -f logs/cron.log`
   - Test manually: `python3 daily_calculations.py`

4. **Web Interface Not Loading**
   - Check if port 5000 is available: `lsof -i :5000`
   - Kill existing process if needed: `pkill -f "python.*app.py"`
   - Check Flask logs: `tail -f flask.log`

## Maintenance

### Log Management
```bash
# View log files
ls -la logs/

# Clean old logs (automatically done weekly if cron is set up)
find logs/ -name '*.log' -mtime +30 -delete
```

### Database Maintenance
```bash
# Vacuum and analyze tables for performance
psql -d stock_tools -c "VACUUM ANALYZE stocks;"
psql -d stock_tools -c "VACUUM ANALYZE stock_prices;"
psql -d stock_tools -c "VACUUM ANALYZE momentum;"
psql -d stock_tools -c "VACUUM ANALYZE relative_strength;"
```

## Quick Start Summary

For a new machine, run these commands in order:

```bash
# 1. Setup environment
cd StockTools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure database
cp .env.example .env
# Edit .env with your credentials

# 3. Load initial data
python load_nse_stocks.py
python main.py
python fetch_nifty_500_data.py

# 4. Fetch historical prices (this takes time)
python fetch_historical_prices.py

# 5. Calculate indicators
python create_indices.py
echo "180" | python calculate_momentum.py --action historical
python calculate_relative_strength.py --action historical

# 6. Set up daily automation
./setup_cron.sh

# 7. Start web interface
python web/app.py
```

## Support Files

- Configuration: `.env`, `config/database.py`
- Logs: `logs/` directory
- Data files: `src/data/nse.csv`, `src/data/bse_stocks.CSV`
- Web assets: `web/static/`, `web/templates/`

## Notes

- Initial historical data fetch can take 2-4 hours
- Daily updates run automatically at 6:30 PM IST if cron is configured
- The system handles NSE and BSE stocks with automatic symbol resolution
- All timestamps are stored in UTC in the database