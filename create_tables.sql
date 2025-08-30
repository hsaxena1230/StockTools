-- Create tables for StockTools database with TimescaleDB support
-- Run this script first to create all necessary tables

-- Enable TimescaleDB extension (required for time-series optimization)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 1. Create stocks table (main table)
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create stock_prices table
CREATE TABLE IF NOT EXISTS stock_prices (
    time TIMESTAMP NOT NULL,
    stock_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    close_price DECIMAL(10, 2) NOT NULL,
    volume BIGINT,
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    open DECIMAL(10, 2),
    CONSTRAINT stock_prices_pkey PRIMARY KEY (time, stock_id),
    CONSTRAINT stock_prices_stock_id_fkey FOREIGN KEY (stock_id) 
        REFERENCES stocks(id) ON DELETE CASCADE
);

-- Convert stock_prices to TimescaleDB hypertable for time-series optimization
SELECT create_hypertable('stock_prices', 'time', if_not_exists => TRUE);

-- 3. Create momentum table
CREATE TABLE IF NOT EXISTS momentum (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('STOCK', 'INDUSTRY_INDEX', 'MARKET_INDEX')),
    entity_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    current_price DECIMAL(12, 4) NOT NULL,
    
    -- 30-day momentum metrics
    price_30d DECIMAL(12, 4),
    momentum_30d DECIMAL(15, 4),
    momentum_30d_rank INTEGER,
    
    -- 60-day momentum metrics
    price_60d DECIMAL(12, 4),
    momentum_60d DECIMAL(15, 4),
    momentum_60d_rank INTEGER,
    
    -- 90-day momentum metrics
    price_90d DECIMAL(12, 4),
    momentum_90d DECIMAL(15, 4),
    momentum_90d_rank INTEGER,
    
    -- 180-day momentum metrics
    price_180d DECIMAL(12, 4),
    momentum_180d DECIMAL(15, 4),
    momentum_180d_rank INTEGER,
    
    -- 360-day momentum metrics
    price_360d DECIMAL(12, 4),
    momentum_360d DECIMAL(15, 4),
    momentum_360d_rank INTEGER,
    
    -- Composite metrics
    average_momentum DECIMAL(15, 4),
    average_momentum_rank INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Uniqueness constraint
    UNIQUE(symbol, entity_type, date)
);

-- 4. Create relative_strength table
CREATE TABLE IF NOT EXISTS relative_strength (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('STOCK', 'INDUSTRY_INDEX')),
    entity_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    benchmark_symbol VARCHAR(50) NOT NULL DEFAULT '^CRSLDX',
    
    -- Current prices
    current_price DECIMAL(12, 4) NOT NULL,
    benchmark_price DECIMAL(12, 4) NOT NULL,
    
    -- 30-day RS metrics
    price_30d DECIMAL(12, 4),
    benchmark_price_30d DECIMAL(12, 4),
    rs_30d DECIMAL(15, 6),
    rs_30d_rank INTEGER,
    
    -- 60-day RS metrics
    price_60d DECIMAL(12, 4),
    benchmark_price_60d DECIMAL(12, 4),
    rs_60d DECIMAL(15, 6),
    rs_60d_rank INTEGER,
    
    -- 90-day RS metrics
    price_90d DECIMAL(12, 4),
    benchmark_price_90d DECIMAL(12, 4),
    rs_90d DECIMAL(15, 6),
    rs_90d_rank INTEGER,
    
    -- 180-day RS metrics
    price_180d DECIMAL(12, 4),
    benchmark_price_180d DECIMAL(12, 4),
    rs_180d DECIMAL(15, 6),
    rs_180d_rank INTEGER,
    
    -- 360-day RS metrics
    price_360d DECIMAL(12, 4),
    benchmark_price_360d DECIMAL(12, 4),
    rs_360d DECIMAL(15, 6),
    rs_360d_rank INTEGER,
    
    -- Composite metrics
    average_rs DECIMAL(15, 6),
    average_rs_rank INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Uniqueness constraint
    UNIQUE(symbol, entity_type, date, benchmark_symbol)
);

-- 5. Create equiweighted_index table
CREATE TABLE IF NOT EXISTS equiweighted_index (
    id SERIAL PRIMARY KEY,
    industry VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    index_value DECIMAL(12, 6) NOT NULL,
    stock_count INTEGER NOT NULL,
    base_value DECIMAL(12, 6) DEFAULT 1000.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(industry, date)
);

-- 6. Create missing_stock_data table
CREATE TABLE IF NOT EXISTS missing_stock_data (
    id SERIAL PRIMARY KEY,
    sc_code VARCHAR(20),
    sc_name VARCHAR(255) NOT NULL,
    sc_group VARCHAR(10),
    attempted_symbol VARCHAR(50),
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sc_code)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol ON stock_prices(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_prices_time ON stock_prices(time);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_time ON stock_prices(stock_id, time);

CREATE INDEX IF NOT EXISTS idx_momentum_symbol_date ON momentum(symbol, date);
CREATE INDEX IF NOT EXISTS idx_momentum_entity_type ON momentum(entity_type);
CREATE INDEX IF NOT EXISTS idx_momentum_date ON momentum(date);

CREATE INDEX IF NOT EXISTS idx_rs_symbol_date ON relative_strength(symbol, date);
CREATE INDEX IF NOT EXISTS idx_rs_entity_type ON relative_strength(entity_type);
CREATE INDEX IF NOT EXISTS idx_rs_date ON relative_strength(date);

CREATE INDEX IF NOT EXISTS idx_equiweighted_industry_date ON equiweighted_index(industry, date);

-- Grant permissions (update username as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stockuser;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stockuser;