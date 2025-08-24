-- Query to find stocks without price data in stock_prices table

-- 1. Stocks in stocks table but not in stock_prices table
SELECT 
    s.symbol,
    s.name,
    s.sector,
    s.industry,
    'No price data in database' as reason
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id
WHERE sp.stock_id IS NULL
ORDER BY s.symbol;

-- 2. Count of stocks without any price data
SELECT COUNT(*) as stocks_without_price_data
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id
WHERE sp.stock_id IS NULL;

-- 3. Stocks with very limited price data (less than 10 records)
SELECT 
    s.symbol,
    s.name,
    COUNT(sp.time) as price_records,
    MAX(sp.time) as latest_price_date
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id
GROUP BY s.id, s.symbol, s.name
HAVING COUNT(sp.time) < 10
ORDER BY COUNT(sp.time), s.symbol;

-- 4. Stocks with no recent price data (older than 30 days)
SELECT 
    s.symbol,
    s.name,
    MAX(sp.time) as latest_price_date,
    CURRENT_DATE - MAX(sp.time)::date as days_old
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id
GROUP BY s.id, s.symbol, s.name
HAVING MAX(sp.time) < CURRENT_DATE - INTERVAL '30 days' 
   OR MAX(sp.time) IS NULL
ORDER BY MAX(sp.time) NULLS FIRST;

-- 5. Summary statistics
SELECT 
    'Total Stocks' as category,
    COUNT(*) as count
FROM stocks
UNION ALL
SELECT 
    'Stocks with Price Data' as category,
    COUNT(DISTINCT sp.stock_id) as count
FROM stock_prices sp
UNION ALL
SELECT 
    'Stocks without Price Data' as category,
    COUNT(*) as count
FROM stocks s
LEFT JOIN stock_prices sp ON s.id = sp.stock_id
WHERE sp.stock_id IS NULL;