#!/bin/bash

# Setup cron job for complete daily stock market calculations
# This includes: stock prices, equiweighted indices, momentum, and relative strength
# Run this script to install the cron job

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

echo "🚀 Setting up comprehensive daily stock market calculations cron job..."
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Make the daily calculations script executable
chmod +x "$SCRIPT_DIR/daily_calculations.py"

# Create main cron job entry
# Runs every weekday at 6:30 PM IST (after market close)
# Only runs Monday-Friday (1-5) to avoid weekends
MAIN_CRON_JOB="30 18 * * 1-5 cd $SCRIPT_DIR && $PYTHON_PATH daily_calculations.py >> logs/cron.log 2>&1"

# Create a backup/cleanup job that runs weekly on Sunday at 2 AM
# This helps manage log files and can run maintenance tasks
CLEANUP_CRON_JOB="0 2 * * 0 cd $SCRIPT_DIR && find logs/ -name '*.log' -mtime +30 -delete && echo \"\$(date): Cleaned old log files\" >> logs/maintenance.log 2>&1"

echo "📋 Cron jobs to be installed:"
echo "1. Daily calculations: Monday-Friday at 6:30 PM IST"
echo "2. Weekly cleanup: Sunday at 2:00 AM IST"
echo ""

# Remove old cron jobs if they exist
echo "🧹 Removing any existing related cron jobs..."
(crontab -l 2>/dev/null | grep -v "update_daily_prices.py" | grep -v "daily_calculations.py" | grep -v "find logs/") | crontab -

# Add new cron jobs
echo "📅 Installing new cron jobs..."
(crontab -l 2>/dev/null; echo "$MAIN_CRON_JOB"; echo "$CLEANUP_CRON_JOB") | crontab -

echo ""
echo "✅ Cron jobs installed successfully!"
echo ""
echo "📊 Daily Calculations Schedule:"
echo "   • Time: 6:30 PM IST (18:30)"
echo "   • Days: Monday through Friday (weekdays only)"
echo "   • Script: daily_calculations.py"
echo ""
echo "🧹 Maintenance Schedule:"
echo "   • Time: 2:00 AM IST (02:00)"
echo "   • Days: Sunday (weekly)"
echo "   • Action: Clean log files older than 30 days"
echo ""
echo "📝 What runs daily:"
echo "   1. 📈 Update stock prices"
echo "   2. ⚖️ Calculate equiweighted indices"
echo "   3. 🚀 Calculate momentum (30d, 90d, 180d)"
echo "   4. 📊 Calculate relative strength (30d, 90d, 180d)"
echo ""
echo "🔍 Monitoring & Management:"
echo "   • View current cron jobs: crontab -l"
echo "   • View daily logs: tail -f logs/daily_calculations_$(date +%Y-%m-%d).log"
echo "   • View cron execution log: tail -f logs/cron.log"
echo "   • View maintenance log: tail -f logs/maintenance.log"
echo ""
echo "🗑️ To remove all jobs:"
echo "   crontab -l | grep -v 'daily_calculations.py' | grep -v 'find logs/' | crontab -"
echo ""
echo "⚙️ Prerequisites verified:"
echo "   ✓ Logs directory created: $SCRIPT_DIR/logs"
echo "   ✓ Script permissions set: daily_calculations.py"
echo "   ✓ Python path detected: $PYTHON_PATH"
echo ""
echo "🎯 Your momentum and relative strength data will now be updated"
echo "   automatically every trading day, ensuring your journey charts"
echo "   always show the latest market movements!"