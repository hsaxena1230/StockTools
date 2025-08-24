#!/usr/bin/env python3
"""
Safe Symbol Resolution - Conservative approach to avoid rate limiting
Processes stocks in smaller batches with longer delays
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection
from src.models.missing_stock import MissingStock
from src.data.symbol_resolver import SymbolResolver
import time
import json

def resolve_missing_symbols_safely():
    """Safe version with conservative rate limiting"""
    print("=== Safe Symbol Resolution (Rate-Limited) ===\n")
    
    # Initialize database connection
    print("1. Connecting to database...")
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    print("✅ Connected to database")
    
    # Get missing stocks
    missing_stock_model = MissingStock(db)
    missing_stocks = missing_stock_model.get_all_missing_stocks()
    
    if not missing_stocks:
        print("✅ No missing stocks found")
        db.close()
        return
    
    print(f"✅ Found {len(missing_stocks)} missing stocks")
    
    # Process in very small batches
    batch_size = 5  # Very conservative batch size
    
    print(f"\n2. Processing {len(missing_stocks)} stocks in batches of {batch_size}")
    print("   Using conservative rate limiting to avoid 429 errors")
    
    all_results = []
    
    for batch_start in range(0, len(missing_stocks), batch_size):
        batch_end = min(batch_start + batch_size, len(missing_stocks))
        batch = missing_stocks[batch_start:batch_end]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(missing_stocks) + batch_size - 1) // batch_size
        
        print(f"\n--- Processing Batch {batch_num}/{total_batches} ---")
        print(f"Stocks {batch_start + 1}-{batch_end} of {len(missing_stocks)}")
        
        # Initialize resolver with conservative settings
        resolver = SymbolResolver()
        
        # Process batch
        batch_results = process_batch_safely(batch, resolver)
        all_results.extend(batch_results)
        
        # Long pause between batches
        if batch_end < len(missing_stocks):
            pause_time = 30  # 30 seconds between batches
            print(f"\n⏸️  Pausing {pause_time} seconds before next batch to avoid rate limits...")
            time.sleep(pause_time)
    
    # Analyze results
    print(f"\n=== Final Results ===")
    resolved_count = sum(1 for r in all_results if r['status'] == 'resolved')
    failed_count = len(all_results) - resolved_count
    
    print(f"Total processed: {len(all_results)}")
    print(f"Successfully resolved: {resolved_count}")
    print(f"Failed to resolve: {failed_count}")
    print(f"Success rate: {(resolved_count / len(all_results) * 100):.1f}%")
    
    # Show resolved symbols
    resolved_results = [r for r in all_results if r['status'] == 'resolved']
    if resolved_results:
        print(f"\n=== Successfully Resolved Symbols ===")
        for i, result in enumerate(resolved_results, 1):
            best_match = result['best_match']
            print(f"{i:2d}. {result['sc_name']} → {best_match['symbol']} ({best_match['similarity_score']}%)")
    
    # Save results
    save_results(all_results)
    
    # Option to update database
    if resolved_results:
        update_choice = input(f"\nInsert {len(resolved_results)} resolved symbols into stocks table? (y/n): ").strip().lower()
        
        if update_choice == 'y':
            from resolve_missing_symbols import update_database_with_resolved_symbols
            update_stats = update_database_with_resolved_symbols(resolved_results, db)
    
    db.close()
    print("\n✅ Safe symbol resolution completed!")

def process_batch_safely(batch, resolver):
    """Process a batch of stocks with safe rate limiting"""
    results = []
    
    for i, stock in enumerate(batch, 1):
        sc_name = stock.get('sc_name', '')
        sc_code = stock.get('sc_code', '')
        
        print(f"\n  Processing {i}/{len(batch)}: {sc_name}")
        
        # Search for symbols with delay
        try:
            search_results = resolver.search_yahoo_symbol(sc_name)
            
            if not search_results:
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'failed',
                    'reason': 'No symbols found in search',
                    'candidates': []
                })
                print(f"    ✗ No symbols found")
                continue
            
            # Verify candidates with extra safety
            verified_candidates = []
            for j, candidate in enumerate(search_results[:3], 1):  # Only check top 3
                symbol = candidate['symbol']
                print(f"    Verifying {j}/3: {symbol}")
                
                # Extra delay before verification
                time.sleep(3)
                
                is_valid, verification_data = resolver.verify_symbol_data(symbol, max_retries=2)
                
                candidate.update({
                    'is_valid': is_valid,
                    'verification_data': verification_data
                })
                
                if is_valid:
                    verified_candidates.append(candidate)
                    print(f"      ✓ Valid: {verification_data.get('name', 'N/A')}")
                else:
                    print(f"      ✗ Invalid: {verification_data.get('reason', 'Unknown')}")
                
                # Pause between verifications
                if j < len(search_results[:3]):
                    time.sleep(2)
            
            if verified_candidates:
                best_match = verified_candidates[0]
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'resolved',
                    'best_symbol': best_match['symbol'],
                    'best_match': best_match,
                    'all_candidates': verified_candidates
                })
                print(f"    → Best match: {best_match['symbol']}")
            else:
                results.append({
                    'sc_code': sc_code,
                    'sc_name': sc_name,
                    'status': 'failed',
                    'reason': 'No valid symbols found',
                    'candidates': search_results
                })
                print(f"    ✗ No valid symbols found")
                
        except Exception as e:
            results.append({
                'sc_code': sc_code,
                'sc_name': sc_name,
                'status': 'failed',
                'reason': f'Processing error: {str(e)}',
                'candidates': []
            })
            print(f"    ✗ Error: {str(e)}")
        
        # Pause between stocks in batch
        if i < len(batch):
            time.sleep(5)  # 5 seconds between stocks
    
    return results

def save_results(results):
    """Save results to files"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Save detailed JSON
    with open(f'safe_resolution_results_{timestamp}.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save summary
    resolved_results = [r for r in results if r['status'] == 'resolved']
    failed_results = [r for r in results if r['status'] == 'failed']
    
    with open(f'safe_resolution_summary_{timestamp}.txt', 'w') as f:
        f.write(f"Safe Symbol Resolution Summary\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total processed: {len(results)}\n")
        f.write(f"Successfully resolved: {len(resolved_results)}\n")
        f.write(f"Failed to resolve: {len(failed_results)}\n")
        f.write(f"Success rate: {(len(resolved_results) / len(results) * 100):.1f}%\n\n")
        
        if resolved_results:
            f.write("Resolved Symbols:\n")
            f.write("-" * 30 + "\n")
            for result in resolved_results:
                best_match = result['best_match']
                f.write(f"{result['sc_name']} → {best_match['symbol']} ({best_match['similarity_score']}%)\n")
        
        if failed_results:
            f.write(f"\nFailed Resolutions:\n")
            f.write("-" * 30 + "\n")
            for result in failed_results:
                f.write(f"{result['sc_name']}: {result['reason']}\n")
    
    print(f"\n✅ Results saved:")
    print(f"   - safe_resolution_results_{timestamp}.json")
    print(f"   - safe_resolution_summary_{timestamp}.txt")

if __name__ == "__main__":
    print("⚠️  This is the SAFE version with conservative rate limiting")
    print("   - Processes 5 stocks per batch")
    print("   - 30 second pause between batches")
    print("   - 3-5 second delays between API calls")
    print("   - Only verifies top 3 candidates per stock")
    print()
    
    proceed = input("This will be slower but safer. Proceed? (y/n): ").strip().lower()
    
    if proceed == 'y':
        resolve_missing_symbols_safely()
    else:
        print("Process cancelled. Use regular resolve_missing_symbols.py for faster processing.")