# TimescaleDB Setup for Stock Prices

## Prerequisites

1. PostgreSQL must be installed
2. TimescaleDB extension must be installed

## Installing TimescaleDB

### macOS
```bash
brew install timescaledb
brew services restart postgresql
```

### Ubuntu/Debian
```bash
# Add TimescaleDB PPA
sudo add-apt-repository ppa:timescale/timescaledb-ppa
sudo apt update

# Install TimescaleDB
sudo apt install timescaledb-postgresql-14

# Run TimescaleDB tune script
sudo timescaledb-tune

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Enable TimescaleDB in Database
```sql
-- Connect to your database
psql -U postgres -d stock_tools

-- Enable extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
```

## Usage

### 1. Fetch Historical Prices (One-time setup)
```bash
python fetch_historical_prices.py
```

This will:
- Create TimescaleDB hypertable `stock_prices`
- Fetch 10 years of historical data for all stocks
- Store data in time-series optimized format

### 2. Daily Updates
```bash
python update_daily_prices.py
```

This will:
- Check which stocks need updates
- Fetch latest closing prices
- Update the database
- Log results to `logs/daily_price_update.log`

### 3. Set Up Automated Daily Updates

#### Option A: Using provided script
```bash
chmod +x setup_cron.sh
./setup_cron.sh
```

#### Option B: Manual cron setup
```bash
# Edit crontab
crontab -e

# Add this line (runs at 6:30 PM daily)
30 18 * * * cd /path/to/StockTools && python3 update_daily_prices.py >> logs/cron.log 2>&1
```

## Database Schema

The `stock_prices` hypertable:
```sql
CREATE TABLE stock_prices (
    time TIMESTAMP NOT NULL,
    stock_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    volume BIGINT,
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    open DECIMAL(10, 2),
    PRIMARY KEY (time, stock_id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

## Querying Time-Series Data

### Get latest price for a stock
```sql
SELECT * FROM stock_prices 
WHERE symbol = 'TCS.BO' 
ORDER BY time DESC 
LIMIT 1;
```

### Get daily prices for last month
```sql
SELECT time, close_price 
FROM stock_prices 
WHERE symbol = 'RELIANCE.BO' 
  AND time >= NOW() - INTERVAL '1 month'
ORDER BY time;
```

### Calculate weekly averages
```sql
SELECT 
    time_bucket('1 week', time) AS week,
    symbol,
    AVG(close_price) as avg_price,
    MAX(high) as week_high,
    MIN(low) as week_low
FROM stock_prices
WHERE symbol = 'INFY.BO'
  AND time >= NOW() - INTERVAL '3 months'
GROUP BY week, symbol
ORDER BY week DESC;
```

## Monitoring

Check logs:
```bash
# Daily update logs
tail -f logs/daily_price_update.log

# Cron logs
tail -f logs/cron.log
```

Check cron job status:
```bash
crontab -l
```