# Stock Tools - Indian Stock Data Fetcher

A Python application that fetches Indian stock data from Yahoo Finance and stores it in a PostgreSQL database.

## Features

- Fetches major Indian stocks listed on NSE
- Retrieves stock information including name, sector, industry, and market cap
- Stores data in PostgreSQL database with proper schema
- Excludes mutual funds (equity stocks only)
- Handles duplicate entries with upsert functionality

## Project Structure

```
StockTools/
├── src/
│   ├── data/
│   │   └── stock_fetcher.py    # Yahoo Finance data fetching logic
│   ├── models/
│   │   └── stock.py            # Database model for stocks
│   └── utils/
├── config/
│   └── database.py             # Database connection and setup
├── web/
│   ├── static/
│   └── templates/
├── tests/
├── main.py                     # Main application script
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md
```

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd StockTools
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database:**
   - Create a PostgreSQL database named `stock_tools`
   - Create a user with appropriate permissions

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your database credentials:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=stock_tools
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

## Usage

Run the main script to fetch and store stock data:

```bash
python main.py
```

The script will:
1. Connect to the PostgreSQL database
2. Create the `stocks` table if it doesn't exist
3. Fetch Indian stock data from Yahoo Finance
4. Store the data in the database
5. Display a summary of the operation

## Database Schema

The `stocks` table has the following structure:

```sql
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Dependencies

- `yfinance`: For fetching stock data from Yahoo Finance
- `psycopg2-binary`: PostgreSQL adapter for Python
- `pandas`: Data manipulation and analysis
- `python-dotenv`: Load environment variables from .env file
- `requests`: HTTP library for API calls

## Notes

- The application focuses on major Indian stocks listed on NSE
- Mutual funds are automatically excluded
- The database uses an upsert operation to handle duplicate entries
- Stock data includes company name, sector, industry, and market capitalization