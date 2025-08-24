#!/usr/bin/env python3
"""
Resolve Missing Stock Symbols
Uses Yahoo Finance search to find stock symbols for companies in missing_stock_data table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import DatabaseConnection
from src.models.missing_stock import MissingStock
from src.data.symbol_resolver import SymbolResolver
import json

def resolve_missing_symbols():
    """Main function to resolve symbols for missing stocks"""
    print("=== Resolving Missing Stock Symbols ===\n")
    
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
        print("✅ No missing stocks found in database")
        db.close()
        return
    
    print(f"✅ Found {len(missing_stocks)} missing stocks")
    
    # Show sample of missing stocks
    print(f"\n2. Sample missing stocks:")
    for i, stock in enumerate(missing_stocks[:5], 1):
        print(f"   {i}. {stock['sc_name']} (Code: {stock['sc_code']})")
    
    if len(missing_stocks) > 5:
        print(f"   ... and {len(missing_stocks) - 5} more")
    
    # Ask user how many to process
    print(f"\n3. Processing options:")
    print(f"   1. Process first 10 stocks (quick test)")
    print(f"   2. Process first 50 stocks")
    print(f"   3. Process all {len(missing_stocks)} stocks")
    print(f"   4. Process specific range")
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        stocks_to_process = missing_stocks[:10]
    elif choice == "2":
        stocks_to_process = missing_stocks[:50]
    elif choice == "3":
        stocks_to_process = missing_stocks
    elif choice == "4":
        try:
            start = int(input("Start index (1-based): ")) - 1
            end = int(input("End index (1-based): "))
            stocks_to_process = missing_stocks[start:end]
        except (ValueError, IndexError):
            print("Invalid range. Using first 10 stocks.")
            stocks_to_process = missing_stocks[:10]
    else:
        print("Invalid choice. Using first 10 stocks.")
        stocks_to_process = missing_stocks[:10]
    
    print(f"\n4. Processing {len(stocks_to_process)} stocks...")
    
    # Initialize symbol resolver
    resolver = SymbolResolver()
    
    # Resolve symbols
    results = resolver.resolve_missing_symbols(stocks_to_process)
    
    # Analyze results
    print(f"\n=== Resolution Results ===")
    
    resolved_count = sum(1 for r in results if r['status'] == 'resolved')
    failed_count = len(results) - resolved_count
    
    print(f"Total processed: {len(results)}")
    print(f"Successfully resolved: {resolved_count}")
    print(f"Failed to resolve: {failed_count}")
    print(f"Success rate: {(resolved_count / len(results) * 100):.1f}%")
    
    # Show resolved symbols
    print(f"\n=== Successfully Resolved Symbols ===")
    resolved_results = [r for r in results if r['status'] == 'resolved']
    
    for i, result in enumerate(resolved_results, 1):
        best_match = result['best_match']
        print(f"{i:2d}. {result['sc_name']}")
        print(f"    Symbol: {best_match['symbol']}")
        print(f"    Yahoo Name: {best_match['verification_data']['name']}")
        print(f"    Sector: {best_match['verification_data'].get('sector', 'N/A')}")
        print(f"    Similarity Score: {best_match['similarity_score']}%")
        print()
    
    # Show failed resolutions
    failed_results = [r for r in results if r['status'] == 'failed']
    if failed_results:
        print(f"\n=== Failed Resolutions ===")
        for i, result in enumerate(failed_results, 1):
            print(f"{i:2d}. {result['sc_name']} - {result['reason']}")
    
    # Save results to file
    print(f"\n5. Saving results...")
    
    # Save detailed results to JSON
    with open('symbol_resolution_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Save summary to text file
    with open('symbol_resolution_summary.txt', 'w') as f:
        f.write("Symbol Resolution Summary\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Total processed: {len(results)}\n")
        f.write(f"Successfully resolved: {resolved_count}\n")
        f.write(f"Failed to resolve: {failed_count}\n")
        f.write(f"Success rate: {(resolved_count / len(results) * 100):.1f}%\n\n")
        
        f.write("Resolved Symbols:\n")
        f.write("-" * 30 + "\n")
        
        for result in resolved_results:
            best_match = result['best_match']
            f.write(f"Company: {result['sc_name']}\n")
            f.write(f"Code: {result['sc_code']}\n")
            f.write(f"Symbol: {best_match['symbol']}\n")
            f.write(f"Yahoo Name: {best_match['verification_data']['name']}\n")
            f.write(f"Sector: {best_match['verification_data'].get('sector', 'N/A')}\n")
            f.write(f"Similarity: {best_match['similarity_score']}%\n\n")
        
        if failed_results:
            f.write("\nFailed Resolutions:\n")
            f.write("-" * 30 + "\n")
            for result in failed_results:
                f.write(f"{result['sc_name']} - {result['reason']}\n")
    
    print("✅ Results saved to:")
    print("   - symbol_resolution_results.json (detailed)")
    print("   - symbol_resolution_summary.txt (summary)")
    
    # Option to update database with resolved symbols
    if resolved_results:
        print(f"\n6. Database Update Options:")
        print(f"   a. Insert all {len(resolved_results)} resolved symbols into stocks table")
        print(f"   b. Review and select symbols to insert")
        print(f"   c. Skip database update")
        
        update_choice = input("Enter choice (a/b/c): ").strip().lower()
        
        if update_choice == 'a':
            update_stats = update_database_with_resolved_symbols(resolved_results, db)
            
        elif update_choice == 'b':
            selected_results = select_symbols_for_insertion(resolved_results)
            if selected_results:
                update_stats = update_database_with_resolved_symbols(selected_results, db)
            else:
                print("No symbols selected for insertion")
                
        else:
            print("Skipping database update")
    
    db.close()
    print("\n✅ Symbol resolution completed!")

def update_database_with_resolved_symbols(resolved_results, db_connection):
    """Insert resolved symbols into stocks table and remove from missing_stock_data table"""
    from src.models.stock import Stock
    from src.models.missing_stock import MissingStock
    
    print(f"\nProcessing {len(resolved_results)} resolved symbols...")
    
    stock_model = Stock(db_connection)
    missing_stock_model = MissingStock(db_connection)
    
    inserted_count = 0
    removed_count = 0
    failed_count = 0
    
    for result in resolved_results:
        try:
            best_match = result['best_match']
            verification_data = best_match['verification_data']
            
            # Prepare stock data for insertion
            stock_data = {
                'symbol': best_match['symbol'],
                'name': verification_data.get('name', result['sc_name']),
                'sector': verification_data.get('sector', ''),
                'industry': verification_data.get('industry', ''),
                'market_cap': verification_data.get('market_cap', 0)
            }
            
            print(f"\nProcessing: {result['sc_name']} → {best_match['symbol']}")
            
            # Check if symbol already exists in stocks table
            existing_stock = stock_model.get_stock_by_symbol(best_match['symbol'])
            
            if existing_stock:
                print(f"  ⚠️  Symbol {best_match['symbol']} already exists in stocks table")
                # Still remove from missing_stock_data since we found it
                remove_query = "DELETE FROM missing_stock_data WHERE sc_code = %s"
                db_connection.execute_query(remove_query, (result['sc_code'],))
                removed_count += 1
                print(f"  ✓ Removed from missing_stock_data table")
            else:
                # Insert into stocks table
                if stock_model.insert_stock(stock_data):
                    inserted_count += 1
                    print(f"  ✓ Inserted into stocks table: {stock_data['name']}")
                    
                    # Remove from missing_stock_data table
                    remove_query = "DELETE FROM missing_stock_data WHERE sc_code = %s"
                    db_connection.execute_query(remove_query, (result['sc_code'],))
                    removed_count += 1
                    print(f"  ✓ Removed from missing_stock_data table")
                    
                else:
                    failed_count += 1
                    print(f"  ✗ Failed to insert into stocks table")
            
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Error processing {result['sc_name']}: {e}")
    
    print(f"\n=== Database Update Summary ===")
    print(f"Successfully inserted into stocks table: {inserted_count}")
    print(f"Records removed from missing_stock_data: {removed_count}")
    print(f"Failed operations: {failed_count}")
    print(f"Already existing symbols: {len(resolved_results) - inserted_count - failed_count}")
    
    return {
        'inserted': inserted_count,
        'removed': removed_count,
        'failed': failed_count
    }

def select_symbols_for_insertion(resolved_results):
    """Allow user to select which symbols to insert into database"""
    print(f"\n=== Select Symbols for Insertion ===")
    print(f"Review each resolved symbol and choose whether to insert:")
    
    selected = []
    
    for i, result in enumerate(resolved_results, 1):
        best_match = result['best_match']
        verification_data = best_match['verification_data']
        
        print(f"\n{i}/{len(resolved_results)}. {result['sc_name']}")
        print(f"   Symbol: {best_match['symbol']}")
        print(f"   Yahoo Name: {verification_data['name']}")
        print(f"   Sector: {verification_data.get('sector', 'N/A')}")
        print(f"   Industry: {verification_data.get('industry', 'N/A')}")
        print(f"   Similarity Score: {best_match['similarity_score']}%")
        
        choice = input("   Insert this symbol? (y/n/q to quit): ").strip().lower()
        
        if choice == 'y':
            selected.append(result)
            print("   ✓ Selected for insertion")
        elif choice == 'q':
            break
        else:
            print("   ✗ Skipped")
    
    print(f"\nSelected {len(selected)} symbols for insertion")
    return selected

def auto_resolve_and_insert():
    """Automatically resolve symbols and insert high-confidence matches"""
    print("=== Auto-Resolve and Insert High-Confidence Matches ===\n")
    
    # Initialize database connection
    db = DatabaseConnection()
    connection = db.connect()
    
    if not connection:
        print("❌ Failed to connect to database")
        return
    
    # Get missing stocks
    missing_stock_model = MissingStock(db)
    missing_stocks = missing_stock_model.get_all_missing_stocks()
    
    if not missing_stocks:
        print("✅ No missing stocks found")
        db.close()
        return
    
    print(f"Found {len(missing_stocks)} missing stocks")
    
    # Set confidence threshold
    confidence_threshold = int(input("Enter minimum similarity score threshold (1-100, recommended: 80): ") or 80)
    
    print(f"Processing with confidence threshold: {confidence_threshold}%")
    
    # Resolve symbols
    resolver = SymbolResolver()
    results = resolver.resolve_missing_symbols(missing_stocks)
    
    # Filter high-confidence matches
    high_confidence = []
    for result in results:
        if (result['status'] == 'resolved' and 
            result['best_match']['similarity_score'] >= confidence_threshold):
            high_confidence.append(result)
    
    print(f"\nFound {len(high_confidence)} high-confidence matches (>={confidence_threshold}%)")
    
    if high_confidence:
        # Show high-confidence matches
        print("\n=== High-Confidence Matches ===")
        for i, result in enumerate(high_confidence, 1):
            best_match = result['best_match']
            print(f"{i:2d}. {result['sc_name']} → {best_match['symbol']} ({best_match['similarity_score']}%)")
        
        proceed = input(f"\nAutomatically insert these {len(high_confidence)} symbols? (y/n): ").strip().lower()
        
        if proceed == 'y':
            update_stats = update_database_with_resolved_symbols(high_confidence, db)
            
            print(f"\n=== Auto-Insert Results ===")
            print(f"Successfully processed: {update_stats['inserted'] + update_stats['removed']}")
            print(f"New stocks added: {update_stats['inserted']}")
            print(f"Records cleaned up: {update_stats['removed']}")
            print(f"Failed operations: {update_stats['failed']}")
        else:
            print("Auto-insert cancelled")
    else:
        print("No high-confidence matches found")
    
    db.close()
    print("\n✅ Auto-resolve process completed!")

def test_single_company():
    """Test symbol resolution for a single company"""
    company_name = input("Enter company name to test: ").strip()
    
    if not company_name:
        print("No company name provided")
        return
    
    print(f"\nTesting symbol resolution for: {company_name}")
    
    resolver = SymbolResolver()
    
    # Search for symbols
    print("\n1. Searching Yahoo Finance...")
    search_results = resolver.search_yahoo_symbol(company_name)
    
    if search_results:
        print(f"Found {len(search_results)} potential matches:")
        for i, result in enumerate(search_results, 1):
            print(f"  {i}. {result['symbol']} - {result['name']} (Score: {result['similarity_score']}%)")
    else:
        print("No matches found in Yahoo Finance search")
        
        # Try generating suggestions
        print("\n2. Generating symbol suggestions...")
        suggestions = resolver.generate_symbol_suggestions(company_name)
        if suggestions:
            print("Possible symbol variations:")
            for suggestion in suggestions:
                print(f"  • {suggestion}")
        else:
            print("Could not generate symbol suggestions")

if __name__ == "__main__":
    print("=== Stock Symbol Resolution Tool ===")
    print("Choose an option:")
    print("1. Resolve missing symbols (manual review)")
    print("2. Auto-resolve and insert high-confidence matches")
    print("3. Test single company name")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        resolve_missing_symbols()
    elif choice == "2":
        auto_resolve_and_insert()
    elif choice == "3":
        test_single_company()
    else:
        print("Invalid choice. Running main resolution...")
        resolve_missing_symbols()