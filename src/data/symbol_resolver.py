import yfinance as yf
import pandas as pd
import requests
from typing import List, Dict, Optional, Tuple
import time
import re
from fuzzywuzzy import fuzz

class SymbolResolver:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def clean_company_name(self, company_name: str) -> str:
        """Clean and normalize company name for better matching"""
        if not company_name:
            return ""
        
        # Convert to uppercase and strip
        name = str(company_name).upper().strip()
        
        # Remove common suffixes
        suffixes = [
            'LIMITED', 'LTD', 'LTD.', 'PRIVATE', 'PVT', 'PVT.',
            'COMPANY', 'CO.', 'CO', 'CORPORATION', 'CORP',
            'INC', 'INCORPORATED', 'PUBLIC', 'PLC'
        ]
        
        for suffix in suffixes:
            name = re.sub(rf'\b{suffix}\b\.?$', '', name).strip()
        
        # Remove extra spaces and special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def search_yahoo_symbol(self, company_name: str, country='IN') -> List[Dict]:
        """Search for stock symbols on Yahoo Finance using company name"""
        try:
            # Clean the company name
            search_term = self.clean_company_name(company_name)
            
            # Yahoo Finance search API (unofficial)
            search_url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                'q': search_term,
                'quotesCount': 10,
                'newsCount': 0,
                'listsCount': 0,
                'quotesQueryId': 'tss_match_phrase_query'
            }
            
            # Add delay before search to avoid rate limiting
            time.sleep(1)
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                quotes = data.get('quotes', [])
                
                # Filter for Indian stocks (.NS, .BO)
                indian_quotes = []
                for quote in quotes:
                    symbol = quote.get('symbol', '')
                    if symbol.endswith('.NS') or symbol.endswith('.BO'):
                        indian_quotes.append({
                            'symbol': symbol,
                            'name': quote.get('longname', quote.get('shortname', '')),
                            'exchange': quote.get('exchange', ''),
                            'sector': quote.get('sector', ''),
                            'industry': quote.get('industry', ''),
                            'market': quote.get('market', ''),
                            'similarity_score': self.calculate_similarity(
                                search_term, 
                                quote.get('longname', quote.get('shortname', ''))
                            )
                        })
                
                # Sort by similarity score
                indian_quotes.sort(key=lambda x: x['similarity_score'], reverse=True)
                return indian_quotes[:5]  # Return top 5 matches
                
        except Exception as e:
            print(f"Error searching for {company_name}: {e}")
        
        return []
    
    def calculate_similarity(self, name1: str, name2: str) -> int:
        """Calculate similarity between two company names"""
        if not name1 or not name2:
            return 0
        
        # Clean both names
        clean1 = self.clean_company_name(name1)
        clean2 = self.clean_company_name(name2)
        
        # Use fuzzy matching
        return fuzz.ratio(clean1, clean2)
    
    def verify_symbol_data(self, symbol: str, max_retries: int = 3) -> Tuple[bool, Dict]:
        """Verify if a symbol has valid data on Yahoo Finance with retry logic"""
        for attempt in range(max_retries):
            try:
                # Add delay to avoid rate limiting
                if attempt > 0:
                    delay = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                    print(f"    Retrying {symbol} in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                
                ticker = yf.Ticker(symbol)
                
                # First try to get basic info with timeout
                try:
                    info = ticker.info
                except Exception as info_error:
                    if "429" in str(info_error) or "Too Many Requests" in str(info_error):
                        if attempt < max_retries - 1:
                            continue  # Retry on rate limit
                    raise info_error
                
                # Check if it's a valid stock (not mutual fund)
                if info.get('quoteType') == 'MUTUALFUND':
                    return False, {'reason': 'Mutual fund'}
                
                # Try to get some basic info
                name = info.get('longName', info.get('shortName', ''))
                sector = info.get('sector', '')
                
                if not name:
                    return False, {'reason': 'No company name available'}
                
                # Try to get recent price data with shorter period to reduce load
                try:
                    df = ticker.history(period="2d")  # Reduced from 5d to 2d
                except Exception as price_error:
                    if "429" in str(price_error) or "Too Many Requests" in str(price_error):
                        if attempt < max_retries - 1:
                            continue  # Retry on rate limit
                    # If we can't get price data, still consider it valid if we have basic info
                    if name:
                        return True, {
                            'name': name,
                            'sector': sector,
                            'industry': info.get('industry', ''),
                            'market_cap': info.get('marketCap', 0),
                            'latest_price': None
                        }
                    raise price_error
                
                if df.empty:
                    return False, {'reason': 'No price data available'}
                
                return True, {
                    'name': name,
                    'sector': sector,
                    'industry': info.get('industry', ''),
                    'market_cap': info.get('marketCap', 0),
                    'latest_price': float(df['Close'].iloc[-1]) if not df.empty else None
                }
                
            except Exception as e:
                error_msg = str(e)
                
                # Handle rate limiting specifically
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    if attempt < max_retries - 1:
                        continue  # Will retry with exponential backoff
                    else:
                        return False, {'reason': 'Rate limited - too many requests'}
                
                # Handle other errors
                if attempt < max_retries - 1:
                    continue  # Retry for any error
                else:
                    return False, {'reason': f'Verification error: {error_msg}'}
        
        return False, {'reason': 'Max retries exceeded'}
    
    def resolve_missing_symbols(self, missing_stocks: List[Dict]) -> List[Dict]:
        """
        Resolve symbols for missing stocks from SC_NAME
        
        Args:
            missing_stocks: List of dictionaries with 'sc_name' field
            
        Returns:
            List of resolved symbol information
        """
        results = []
        
        print(f"Resolving symbols for {len(missing_stocks)} missing stocks...")
        
        for i, stock in enumerate(missing_stocks, 1):
            sc_name = stock.get('sc_name', '')
            sc_code = stock.get('sc_code', '')
            
            print(f"\nResolving {i}/{len(missing_stocks)}: {sc_name}")
            
            # Search for symbols
            search_results = self.search_yahoo_symbol(sc_name)
            
            if not search_results:
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'failed',
                    'reason': 'No symbols found in search',
                    'candidates': []
                })
                print(f"  ✗ No symbols found")
                continue
            
            # Verify each candidate
            verified_candidates = []
            for candidate in search_results:
                symbol = candidate['symbol']
                is_valid, verification_data = self.verify_symbol_data(symbol)
                
                candidate.update({
                    'is_valid': is_valid,
                    'verification_data': verification_data
                })
                
                if is_valid:
                    verified_candidates.append(candidate)
                    print(f"  ✓ {symbol}: {verification_data.get('name', 'N/A')} (Score: {candidate['similarity_score']})")
                else:
                    print(f"  ✗ {symbol}: {verification_data.get('reason', 'Invalid')}")
            
            if verified_candidates:
                # Use the best match
                best_match = verified_candidates[0]
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'resolved',
                    'best_symbol': best_match['symbol'],
                    'best_match': best_match,
                    'all_candidates': verified_candidates
                })
                print(f"  → Best match: {best_match['symbol']}")
            else:
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'failed',
                    'reason': 'No valid symbols found',
                    'candidates': search_results
                })
                print(f"  ✗ No valid symbols found")
            
            # Enhanced rate limiting to avoid 429 errors
            if i % 5 == 0 and i > 0:  # Every 5 requests
                print(f"  ⏸️  Pausing for 10 seconds to avoid rate limiting...")
                time.sleep(10)
            else:
                time.sleep(2)  # Increased from 0.5 to 2 seconds between requests
        
        return results
    
    def generate_symbol_suggestions(self, company_name: str) -> List[str]:
        """Generate possible symbol variations for a company name"""
        suggestions = []
        
        # Clean the name
        clean_name = self.clean_company_name(company_name)
        
        if not clean_name:
            return suggestions
        
        # Method 1: Use first letters of words
        words = clean_name.split()
        if len(words) >= 2:
            # Take first 2-4 characters from each word
            acronym = ''.join(word[:2] for word in words[:3])
            if len(acronym) >= 4:
                suggestions.extend([f"{acronym}.NS", f"{acronym}.BO"])
        
        # Method 2: Use company initials
        initials = ''.join(word[0] for word in words if word)
        if len(initials) >= 3:
            suggestions.extend([f"{initials}.NS", f"{initials}.BO"])
        
        # Method 3: Use first word + abbreviated second word
        if len(words) >= 2:
            first_word = words[0][:6]  # First 6 chars of first word
            second_abbrev = words[1][:2]  # First 2 chars of second word
            combo = f"{first_word}{second_abbrev}"
            suggestions.extend([f"{combo}.NS", f"{combo}.BO"])
        
        # Method 4: Remove vowels and use consonants
        consonants = re.sub(r'[AEIOU\s]', '', clean_name)
        if len(consonants) >= 4:
            consonant_symbol = consonants[:8]
            suggestions.extend([f"{consonant_symbol}.NS", f"{consonant_symbol}.BO"])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:10]  # Return top 10 suggestions