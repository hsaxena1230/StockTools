import yfinance as yf
import pandas as pd
import requests
import os
from typing import List, Dict, Optional

class IndianStockFetcher:
    def __init__(self):
        self.bse_csv_path = os.path.join(os.path.dirname(__file__), 'bse_stocks.CSV')
        self.nse_csv_path = os.path.join(os.path.dirname(__file__), 'nse.csv')
        
    def get_bse_stock_list(self) -> List[str]:
        try:
            if not os.path.exists(self.bse_csv_path):
                print(f"BSE CSV file not found at: {self.bse_csv_path}")
                return []
            
            df = pd.read_csv(self.bse_csv_path)
            
            if 'SC_NAME' not in df.columns:
                print("SC_NAME column not found in BSE CSV file")
                return []
            
            stock_symbols = []
            for _, row in df.iterrows():
                company_name = str(row['SC_NAME']).strip()
                
                if company_name and company_name != 'nan':
                    # Convert company name to potential Yahoo Finance symbol
                    symbol = self._convert_to_yahoo_symbol(company_name)
                    if symbol:
                        stock_symbols.append(symbol)
            
            print(f"Loaded {len(stock_symbols)} stock symbols from BSE CSV")
            return stock_symbols
            
        except Exception as e:
            print(f"Error reading BSE CSV file: {e}")
            return []
    
    def _convert_to_yahoo_symbol(self, company_name: str) -> Optional[str]:
        try:
            # Clean up company name
            name = company_name.replace('LTD.', '').replace('LIMITED', '').replace('LTD', '')
            name = name.replace('.', '').strip()
            
            # Handle common name mappings for major companies
            name_mappings = {
                'ABB': 'ABB.BO',
                'AEGIS LOGIS': 'AEGISCHEM.BO',
                'AMAR RAJA BA': 'AMARAJABAT.BO',
                'HDFC': 'HDFCBANK.BO',
                'ANDHRA PETRO': 'ANDHRAPET.BO',
                'BOM DYEING': 'BOMDYEING.BO',
                'TCS': 'TCS.BO',
                'RELIANCE': 'RELIANCE.BO',
                'INFOSYS': 'INFY.BO',
                'WIPRO': 'WIPRO.BO',
                'ICICI BANK': 'ICICIBANK.BO',
                'BHARTI AIRTEL': 'BHARTIARTL.BO',
                'ITC': 'ITC.BO',
                'SBI': 'SBIN.BO',
                'AXIS BANK': 'AXISBANK.BO',
                'KOTAK MAHINDRA BANK': 'KOTAKBANK.BO',
                'MARUTI SUZUKI': 'MARUTI.BO',
                'BAJAJ FINANCE': 'BAJFINANCE.BO',
                'ASIAN PAINTS': 'ASIANPAINT.BO',
                'TITAN': 'TITAN.BO',
                'NESTLE INDIA': 'NESTLEIND.BO'
            }
            
            # Check if we have a direct mapping
            name_upper = name.upper()
            for key, value in name_mappings.items():
                if key in name_upper:
                    return value
            
            # For other companies, try to create a symbol by taking first few characters
            # This is a best-effort approach
            clean_name = ''.join(c for c in name if c.isalnum())
            if len(clean_name) >= 3:
                # Take first 8 characters and add .BO suffix
                symbol = clean_name[:8].upper() + '.BO'
                return symbol
            
            return None
            
        except Exception as e:
            print(f"Error converting company name '{company_name}' to symbol: {e}")
            return None
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Filter out mutual funds by checking if it's an equity
            if info.get('quoteType') == 'MUTUALFUND':
                return None
            
            # Extract relevant information
            stock_data = {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0)
            }
            
            return stock_data
            
        except Exception as e:
            print(f"Error fetching info for {symbol}: {e}")
            return None
    
    def fetch_all_indian_stocks(self) -> List[Dict]:
        print("Fetching Indian stock symbols from BSE CSV...")
        symbols = self.get_bse_stock_list()
        
        if not symbols:
            print("No symbols found in BSE CSV file")
            return []
        
        print(f"Found {len(symbols)} symbols. Fetching stock information...")
        stocks_data = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"Processing {i}/{len(symbols)}: {symbol}")
            stock_info = self.get_stock_info(symbol)
            
            if stock_info and stock_info['name']:  # Only add if we have valid data
                stocks_data.append(stock_info)
                print(f"  ✓ Added: {stock_info['name']}")
            else:
                print(f"  ✗ Skipped: {symbol}")
        
        print(f"\nSuccessfully fetched {len(stocks_data)} stock records")
        return stocks_data
    
    def get_nse_stocks_from_csv(self) -> List[Dict]:
        """Read NSE stocks directly from CSV file with complete information"""
        try:
            if not os.path.exists(self.nse_csv_path):
                print(f"NSE CSV file not found at: {self.nse_csv_path}")
                return []
            
            df = pd.read_csv(self.nse_csv_path)
            
            required_columns = ['symbol', 'company_name', 'sector', 'industry', 'market_cap']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"Missing columns in NSE CSV: {missing_columns}")
                return []
            
            stocks_data = []
            for _, row in df.iterrows():
                stock_data = {
                    'symbol': str(row['symbol']).strip(),
                    'name': str(row['company_name']).strip(),
                    'sector': str(row['sector']).strip() if pd.notna(row['sector']) else '',
                    'industry': str(row['industry']).strip() if pd.notna(row['industry']) else '',
                    'market_cap': int(row['market_cap']) if pd.notna(row['market_cap']) else 0
                }
                
                # Only add if we have a valid symbol and name
                if stock_data['symbol'] and stock_data['name'] and stock_data['symbol'] != 'nan' and stock_data['name'] != 'nan':
                    stocks_data.append(stock_data)
            
            print(f"Loaded {len(stocks_data)} NSE stocks from CSV")
            return stocks_data
            
        except Exception as e:
            print(f"Error reading NSE CSV file: {e}")
            return []
    
    def fetch_all_stocks_with_deduplication(self) -> List[Dict]:
        """Fetch both BSE and NSE stocks, merging by company name to avoid duplicates"""
        print("=== Fetching Indian stocks from both BSE and NSE ===\n")
        
        # First, get NSE stocks from CSV (already has complete info)
        print("1. Loading NSE stocks from CSV...")
        nse_stocks = self.get_nse_stocks_from_csv()
        
        # Create a dictionary to track unique companies by normalized name
        unique_companies = {}
        
        # Add NSE stocks first (they already have complete information)
        for stock in nse_stocks:
            normalized_name = self._normalize_company_name(stock['name'])
            if normalized_name not in unique_companies:
                unique_companies[normalized_name] = stock
                print(f"  Added NSE: {stock['name']} ({stock['symbol']})")
        
        print(f"\nTotal NSE stocks added: {len(unique_companies)}")
        
        # Now fetch BSE stocks
        print("\n2. Fetching BSE stocks...")
        bse_symbols = self.get_bse_stock_list()
        
        if bse_symbols:
            print(f"Found {len(bse_symbols)} BSE symbols. Fetching information...")
            
            added_count = 0
            duplicate_count = 0
            
            for i, symbol in enumerate(bse_symbols, 1):
                if i % 100 == 0:
                    print(f"  Progress: {i}/{len(bse_symbols)}")
                
                stock_info = self.get_stock_info(symbol)
                
                if stock_info and stock_info['name']:
                    normalized_name = self._normalize_company_name(stock_info['name'])
                    
                    if normalized_name not in unique_companies:
                        unique_companies[normalized_name] = stock_info
                        added_count += 1
                        print(f"  ✓ Added BSE: {stock_info['name']} ({symbol})")
                    else:
                        duplicate_count += 1
                        # Optionally update if BSE has better data
                        existing = unique_companies[normalized_name]
                        if not existing.get('sector') and stock_info.get('sector'):
                            existing['sector'] = stock_info['sector']
                        if not existing.get('industry') and stock_info.get('industry'):
                            existing['industry'] = stock_info['industry']
            
            print(f"\nBSE stocks added: {added_count}")
            print(f"BSE duplicates skipped: {duplicate_count}")
        
        # Convert back to list
        all_stocks = list(unique_companies.values())
        
        print(f"\n=== Summary ===")
        print(f"Total unique companies: {len(all_stocks)}")
        
        return all_stocks
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for comparison"""
        if not name:
            return ""
        
        # Convert to uppercase and remove common suffixes
        normalized = name.upper()
        
        # Remove common suffixes and words
        remove_words = [
            'LIMITED', 'LTD', 'LTD.', 'PVT', 'PRIVATE', 'INC', 'INCORPORATED',
            'CORPORATION', 'CORP', 'CO.', 'COMPANY', 'PUBLIC', 'PLC'
        ]
        
        for word in remove_words:
            normalized = normalized.replace(f' {word}', '')
            normalized = normalized.replace(f'{word}', '')
        
        # Remove special characters and extra spaces
        normalized = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in normalized)
        normalized = ' '.join(normalized.split())  # Remove extra spaces
        
        return normalized.strip()
    
    def load_nse_stocks_only(self) -> List[Dict]:
        """Load only NSE stocks from CSV file - for use when BSE stocks are already in database"""
        print("=== Loading NSE stocks from CSV ===\n")
        
        nse_stocks = self.get_nse_stocks_from_csv()
        
        if not nse_stocks:
            print("No NSE stocks found in CSV file")
            return []
        
        print(f"\nLoaded {len(nse_stocks)} NSE stocks from CSV")
        print("\nSample stocks:")
        for i, stock in enumerate(nse_stocks[:5]):
            print(f"  {i+1}. {stock['name']} ({stock['symbol']}) - {stock['sector']}")
        
        if len(nse_stocks) > 5:
            print(f"  ... and {len(nse_stocks) - 5} more")
        
        return nse_stocks