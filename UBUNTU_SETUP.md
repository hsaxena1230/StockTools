# StockTools - Ubuntu Setup Guide

## System Requirements
- Ubuntu 20.04 LTS or newer (tested on 20.04, 22.04, 24.04)
- Minimum 4GB RAM (8GB recommended)
- At least 10GB free disk space
- Active internet connection

## Prerequisites Installation

### Step 1: Update System Packages
```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Python and Development Tools
```bash
# Install Python 3.8+ and pip
sudo apt install python3 python3-pip python3-venv -y

# Install development tools
sudo apt install build-essential python3-dev -y

# Verify Python installation
python3 --version
pip3 --version
```

### Step 3: Install PostgreSQL and TimescaleDB
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Add TimescaleDB repository
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -cs) main' > /etc/apt/sources.list.d/timescaledb.list"

# Add TimescaleDB GPG key
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Update package list
sudo apt update

# Install TimescaleDB
# For PostgreSQL 14 (Ubuntu 22.04)
sudo apt install timescaledb-2-postgresql-14 -y

# For PostgreSQL 15 (Ubuntu 23.04+)
# sudo apt install timescaledb-2-postgresql-15 -y

# For PostgreSQL 16 (Ubuntu 24.04)
# sudo apt install timescaledb-2-postgresql-16 -y

# Configure PostgreSQL for TimescaleDB
sudo timescaledb-tune --quiet --yes

# Start and enable PostgreSQL service
sudo systemctl restart postgresql
sudo systemctl enable postgresql

# Verify PostgreSQL is running
sudo systemctl status postgresql
```

### Step 4: Install Git (if not already installed)
```bash
sudo apt install git -y
```

## Database Setup

### Step 1: Configure PostgreSQL
```bash
# Switch to postgres user
sudo -i -u postgres

# Access PostgreSQL prompt
psql

# Create database and user (run these commands in psql prompt)
CREATE DATABASE stock_tools;
CREATE USER stockuser WITH PASSWORD 'StrongPassword123!';
GRANT ALL PRIVILEGES ON DATABASE stock_tools TO stockuser;
ALTER USER stockuser CREATEDB;
\q

# Exit from postgres user
exit
```

### Step 2: Configure PostgreSQL for Local Connections
```bash
# Edit PostgreSQL configuration to allow password authentication
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Find the line that looks like:
# local   all             all                                     peer

# Change it to:
# local   all             all                                     md5

# Save and exit (Ctrl+X, Y, Enter)

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Project Setup

### Step 1: Clone the Repository
```bash
# Create a workspace directory
mkdir -p ~/projects
cd ~/projects

# Clone the repository
git clone https://github.com/hsaxena1230/StockTools.git
cd StockTools
```

### Step 2: Set Up Python Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install Python Dependencies
```bash
# Install main project dependencies
pip install -r requirements.txt

# Install web application dependencies
pip install -r web/requirements.txt

# If you encounter issues with psycopg2, install system dependencies:
sudo apt install libpq-dev -y
pip install psycopg2-binary --no-cache-dir
```

### Step 4: Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file
nano .env

# Update with your database credentials:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=stock_tools
# DB_USER=stockuser
# DB_PASSWORD=StrongPassword123!

# Save and exit (Ctrl+X, Y, Enter)
```

## Initial Data Setup

### Step 1: Initialize Database Tables with TimescaleDB
```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Create all tables with TimescaleDB hypertables
psql -h localhost -U stockuser -d stock_tools -f create_tables.sql

# Or manually in psql:
psql -h localhost -U stockuser -d stock_tools
\i create_tables.sql
\q

# Verify TimescaleDB is enabled
psql -h localhost -U stockuser -d stock_tools -c "\dx"
# Should show timescaledb in the list of extensions

# Verify hypertable was created
psql -h localhost -U stockuser -d stock_tools -c "SELECT * FROM timescaledb_information.hypertables;"
# Should show stock_prices as a hypertable
```

### Step 2: Load Stock Data
```bash
# Load NSE stocks
python3 load_nse_stocks.py

# Load BSE stocks
python3 main.py

# Load Nifty 500 data
python3 fetch_nifty_500_data.py
```

### Step 3: Fetch Historical Price Data
```bash
# This will take 2-4 hours depending on internet speed
# Consider running in screen or tmux for long-running process
screen -S stock_fetch
python3 fetch_historical_prices.py

# To detach from screen: Ctrl+A, then D
# To reattach: screen -r stock_fetch
```

### Step 4: Create Indices and Calculate Indicators
```bash
# Create industry indices
python3 create_indices.py

# Calculate historical momentum (180-day)
echo "180" | python3 calculate_momentum.py --action historical

# Calculate current momentum
python3 calculate_momentum.py --action calculate

# Calculate historical relative strength
python3 calculate_relative_strength.py --action historical

# Calculate current relative strength
python3 calculate_relative_strength.py --action calculate
```

### Step 5: Generate Industry Analysis
```bash
# Generate 2-year industry momentum
timeout 60 python3 generate_industry_momentum_2years.py

# Generate 2-year industry relative strength
python3 generate_industry_relative_strength_2years.py
```

## Set Up Daily Automation

### Step 1: Create Log Directory
```bash
mkdir -p ~/projects/StockTools/logs
```

### Step 2: Set Up Cron Job
```bash
# Make the setup script executable
chmod +x setup_cron.sh

# Run the setup script
./setup_cron.sh

# Verify cron job is set up
crontab -l

# The cron job will run daily at 6:30 PM IST (Mon-Fri)
```

### Step 3: Manual Daily Update (Optional)
```bash
# If you want to run updates manually
python3 daily_calculations.py
```

## Running the Web Application

### Step 1: Start the Flask Application
```bash
# Activate virtual environment
source venv/bin/activate

# Start the web application
python3 web/app.py

# The application will be available at http://localhost:5000
```

### Step 2: Run as a System Service (Optional)
```bash
# Create a systemd service file
sudo nano /etc/systemd/system/stocktools.service

# Add the following content:
```

```ini
[Unit]
Description=StockTools Web Application
After=network.target postgresql.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/projects/StockTools
Environment="PATH=/home/YOUR_USERNAME/projects/StockTools/venv/bin"
ExecStart=/home/YOUR_USERNAME/projects/StockTools/venv/bin/python web/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Replace YOUR_USERNAME with your actual username

# Reload systemd and start the service
sudo systemctl daemon-reload
sudo systemctl start stocktools
sudo systemctl enable stocktools

# Check service status
sudo systemctl status stocktools
```

## Firewall Configuration (if needed)

```bash
# Allow port 5000 for web application
sudo ufw allow 5000/tcp

# If running behind a reverse proxy (nginx/apache)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## Troubleshooting

### Common Issues and Solutions

#### 1. PostgreSQL Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U stockuser -d stock_tools

# If authentication fails, check pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Ensure local connections use md5 authentication
```

#### 2. Python Module Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install --upgrade -r requirements.txt

# For psycopg2 issues
sudo apt install libpq-dev python3-dev -y
pip install psycopg2-binary --no-cache-dir
```

#### 3. Permission Denied Errors
```bash
# Fix ownership of project directory
sudo chown -R $USER:$USER ~/projects/StockTools

# Fix permissions
chmod -R 755 ~/projects/StockTools
```

#### 4. Out of Memory During Data Fetch
```bash
# Check available memory
free -h

# Add swap space if needed (4GB example)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

#### 5. Cron Job Not Running
```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
grep CRON /var/log/syslog

# Test script manually
cd ~/projects/StockTools
source venv/bin/activate
python3 daily_calculations.py
```

## Performance Optimization

### Database Optimization
```bash
# Connect to database
psql -h localhost -U stockuser -d stock_tools

# Run these SQL commands for better performance:
VACUUM ANALYZE stocks;
VACUUM ANALYZE stock_prices;
VACUUM ANALYZE momentum;
VACUUM ANALYZE relative_strength;

# Create indices for faster queries (if not exists)
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_date ON stock_prices(stock_id, date);
CREATE INDEX IF NOT EXISTS idx_momentum_stock_date ON momentum(stock_id, calculation_date);
CREATE INDEX IF NOT EXISTS idx_rs_stock_date ON relative_strength(stock_id, calculation_date);
```

### System Resource Monitoring
```bash
# Install monitoring tools
sudo apt install htop iotop -y

# Monitor system resources
htop  # CPU and memory usage
iotop  # Disk I/O usage
```

## Backup and Recovery

### Database Backup
```bash
# Create backup directory
mkdir -p ~/backups/stocktools

# Backup database
pg_dump -h localhost -U stockuser -d stock_tools > ~/backups/stocktools/backup_$(date +%Y%m%d).sql

# Compress backup
gzip ~/backups/stocktools/backup_$(date +%Y%m%d).sql
```

### Database Restore
```bash
# Restore from backup
gunzip < ~/backups/stocktools/backup_20240101.sql.gz | psql -h localhost -U stockuser -d stock_tools
```

## Security Recommendations

1. **Use Strong Passwords**: Always use strong, unique passwords for database users
2. **Firewall Rules**: Configure UFW to only allow necessary ports
3. **Regular Updates**: Keep system and packages updated
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
4. **SSL/TLS**: Use HTTPS for production deployments
5. **Environment Variables**: Never commit .env files to version control

## Quick Reference Commands

```bash
# Activate virtual environment
source ~/projects/StockTools/venv/bin/activate

# Start web application
python3 web/app.py

# Run daily calculations
python3 daily_calculations.py

# Check database status
psql -h localhost -U stockuser -d stock_tools -c "SELECT COUNT(*) FROM stocks;"

# View recent logs
tail -f logs/daily_calculations_$(date +%Y-%m-%d).log

# Restart services
sudo systemctl restart postgresql
sudo systemctl restart stocktools  # If using systemd service
```

## Support and Resources

- Project Repository: https://github.com/hsaxena1230/StockTools
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Python Virtual Environments: https://docs.python.org/3/tutorial/venv.html
- Ubuntu Server Guide: https://ubuntu.com/server/docs

## Notes

- Initial data fetch may take 2-4 hours depending on internet speed
- Ensure sufficient disk space for historical data (minimum 10GB recommended)
- The system is designed to run daily updates at 6:30 PM IST
- All timestamps in the database are stored in UTC