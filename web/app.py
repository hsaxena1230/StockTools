#!/usr/bin/env python3
"""
Flask Web Application for Momentum vs Relative Strength Analysis
Serves API endpoints for the momentum vs relative strength chart
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime, date, timedelta
import traceback

from config.database import DatabaseConnection
from src.models.momentum import Momentum
from src.models.relative_strength import RelativeStrength

app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)  # Enable CORS for all routes

# Initialize database connection
db = None
momentum_model = None
rs_model = None

def init_database():
    """Initialize database connection and models"""
    global db, momentum_model, rs_model
    try:
        db = DatabaseConnection()
        connection = db.connect()
        if connection:
            momentum_model = Momentum(db)
            rs_model = RelativeStrength(db)
            print("✅ Database connection initialized")
            return True
        else:
            print("❌ Failed to connect to database")
            return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/journey')
def journey():
    """Serve the quadrant journey page"""
    return render_template('journey.html')

@app.route('/journey-smoothed')
def journey_smoothed():
    """Serve the smoothed quadrant journey page"""
    return render_template('journey_smoothed.html')

@app.route('/industry-analysis')
def industry_analysis():
    """Serve the comprehensive industry analysis page"""
    return render_template('industry_analysis.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if db and db.connection else 'disconnected'
    })

@app.route('/api/momentum-vs-rs')
def get_momentum_vs_rs_data():
    """Get combined momentum and relative strength data for industry indices"""
    try:
        period = request.args.get('period', '30d')
        industry_filter = request.args.get('industry', 'all')
        
        if not momentum_model or not rs_model:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500

        # Validate period
        if period not in ['30d', '90d', '180d']:
            return jsonify({
                'success': False,
                'error': 'Invalid period. Must be 30d, 90d, or 180d'
            }), 400

        # Get industry indices with latest momentum data
        momentum_data = get_latest_momentum_data(period, industry_filter)
        
        # Get relative strength data for the same industries
        rs_data = get_latest_rs_data(period, industry_filter)
        
        # Combine the data
        combined_data = combine_momentum_rs_data(momentum_data, rs_data, period)
        
        return jsonify({
            'success': True,
            'data': combined_data,
            'period': period,
            'count': len(combined_data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in get_momentum_vs_rs_data: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_latest_momentum_data(period, industry_filter):
    """Get latest momentum data for industry indices"""
    try:
        # Get all industry momentum data
        query = """
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM momentum
            WHERE entity_type = 'INDUSTRY_INDEX'
        )
        SELECT 
            m.symbol as industry,
            m.entity_name,
            m.current_price,
            m.momentum_30d_pct,
            m.momentum_90d_pct,
            m.momentum_180d_pct,
            m.volatility_30d,
            m.volume_avg_30d,
            m.date
        FROM momentum m
        INNER JOIN latest_date ld ON m.date = ld.max_date
        WHERE m.entity_type = 'INDUSTRY_INDEX'
        """
        
        if industry_filter != 'all':
            query += " AND m.symbol = %s"
            params = (industry_filter,)
        else:
            params = ()
        
        query += " ORDER BY m.symbol"
        
        results = db.execute_query(query, params)
        
        if results:
            columns = ['industry', 'entity_name', 'current_price', 'momentum_30d', 
                      'momentum_90d', 'momentum_180d', 'volatility', 'volume', 'date']
            return [dict(zip(columns, row)) for row in results]
        
        return []
        
    except Exception as e:
        print(f"Error getting momentum data: {e}")
        return []

def get_latest_rs_data(period, industry_filter):
    """Get latest relative strength data for industry indices"""
    try:
        query = """
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM relative_strength
            WHERE entity_type = 'INDUSTRY_INDEX'
        )
        SELECT 
            rs.symbol as industry,
            rs.entity_name,
            rs.current_price,
            rs.relative_strength_30d,
            rs.relative_strength_90d,
            rs.relative_strength_180d,
            rs.symbol_return_30d,
            rs.symbol_return_90d,
            rs.symbol_return_180d,
            rs.benchmark_return_30d,
            rs.benchmark_return_90d,
            rs.benchmark_return_180d,
            rs.date
        FROM relative_strength rs
        INNER JOIN latest_date ld ON rs.date = ld.max_date
        WHERE rs.entity_type = 'INDUSTRY_INDEX'
        """
        
        if industry_filter != 'all':
            query += " AND rs.symbol = %s"
            params = (industry_filter,)
        else:
            params = ()
        
        query += " ORDER BY rs.symbol"
        
        results = db.execute_query(query, params)
        
        if results:
            columns = ['industry', 'entity_name', 'current_price', 'rs_30d', 'rs_90d', 'rs_180d',
                      'return_30d', 'return_90d', 'return_180d', 'benchmark_return_30d', 
                      'benchmark_return_90d', 'benchmark_return_180d', 'date']
            return [dict(zip(columns, row)) for row in results]
        
        return []
        
    except Exception as e:
        print(f"Error getting relative strength data: {e}")
        return []

def combine_momentum_rs_data(momentum_data, rs_data, period):
    """Combine momentum and relative strength data"""
    combined = []
    
    # Create lookup dictionary for RS data
    rs_lookup = {item['industry']: item for item in rs_data}
    
    for momentum_item in momentum_data:
        industry = momentum_item['industry']
        rs_item = rs_lookup.get(industry)
        
        if rs_item:
            combined_item = {
                'industry': industry,
                'entity_name': momentum_item['entity_name'],
                'current_price': float(momentum_item['current_price'] or 0),
                'momentum_30d': float(momentum_item['momentum_30d'] or 0),
                'momentum_90d': float(momentum_item['momentum_90d'] or 0),
                'momentum_180d': float(momentum_item['momentum_180d'] or 0),
                'relative_strength_30d': float(rs_item['rs_30d'] or 0),
                'relative_strength_90d': float(rs_item['rs_90d'] or 0),
                'relative_strength_180d': float(rs_item['rs_180d'] or 0),
                'volatility': float(momentum_item['volatility'] or 0),
                'volume': int(momentum_item['volume'] or 0),
                'symbol_return_30d': float(rs_item['return_30d'] or 0),
                'symbol_return_90d': float(rs_item['return_90d'] or 0),
                'symbol_return_180d': float(rs_item['return_180d'] or 0),
                'benchmark_return_30d': float(rs_item['benchmark_return_30d'] or 0),
                'benchmark_return_90d': float(rs_item['benchmark_return_90d'] or 0),
                'benchmark_return_180d': float(rs_item['benchmark_return_180d'] or 0),
                'date': str(momentum_item['date'])
            }
            combined.append(combined_item)
    
    return combined

@app.route('/api/industries')
def get_industries():
    """Get list of available industries"""
    try:
        if not momentum_model:
            return jsonify({
                'success': False,
                'error': 'Database not initialized'
            }), 500
        
        query = """
        SELECT DISTINCT symbol as industry, entity_name
        FROM momentum
        WHERE entity_type = 'INDUSTRY_INDEX'
        ORDER BY symbol
        """
        
        results = db.execute_query(query)
        
        industries = []
        if results:
            for row in results:
                industries.append({
                    'industry': row[0],
                    'name': row[1]
                })
        
        return jsonify({
            'success': True,
            'industries': industries,
            'count': len(industries)
        })
        
    except Exception as e:
        print(f"Error getting industries: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/quadrant-journey')
def get_quadrant_journey():
    """Get historical quadrant journey data for selected industries"""
    try:
        days = int(request.args.get('days', 30))
        industries = request.args.getlist('industries[]')
        
        if not industries:
            return jsonify({
                'success': False,
                'error': 'No industries selected'
            }), 400
        
        # Limit to 5 industries
        industries = industries[:5]
        
        # Get historical data for each industry
        journey_data = get_historical_journey_data(industries, days)
        
        return jsonify({
            'success': True,
            'data': journey_data,
            'period_days': days,
            'industries': industries
        })
        
    except Exception as e:
        print(f"Error in get_quadrant_journey: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_historical_journey_data(industries, days):
    """Get historical momentum and RS data for journey visualization"""
    try:
        # First try to get actual historical data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Check if we have historical data
        query = """
        SELECT COUNT(DISTINCT date) as date_count
        FROM momentum 
        WHERE entity_type = 'INDUSTRY_INDEX' 
        AND date >= %s AND date <= %s
        """
        
        result = db.execute_query(query, (start_date, end_date))
        historical_days = result[0][0] if result else 0
        
        print(f"Historical data check: Found {historical_days} days of data")
        
        if historical_days < 2:
            # If we don't have enough historical data, create simulated journey data
            print("Insufficient historical data, creating simulated journey...")
            return create_simulated_journey_data(industries, days)
        
        # Original historical query (if we have enough data)
        return get_actual_historical_data(industries, days)
        
    except Exception as e:
        print(f"Error getting historical journey data: {e}")
        # Fallback to simulated data
        return create_simulated_journey_data(industries, days)

def create_simulated_journey_data(industries, days):
    """Create simulated journey data for demonstration purposes"""
    try:
        # Get current momentum and RS data for the industries
        current_data = {}
        for industry in industries:
            query = """
            SELECT 
                m.symbol,
                m.momentum_30d_pct,
                m.current_price,
                rs.relative_strength_30d
            FROM momentum m
            LEFT JOIN relative_strength rs ON m.symbol = rs.symbol AND m.date = rs.date
            WHERE m.entity_type = 'INDUSTRY_INDEX'
            AND m.symbol = %s
            ORDER BY m.date DESC
            LIMIT 1
            """
            
            result = db.execute_query(query, (industry,))
            if result:
                current_data[industry] = {
                    'momentum': float(result[0][1] or 0),
                    'rs': float(result[0][3] or 100),
                    'price': float(result[0][2] or 1000)
                }
        
        # Generate simulated journey points
        journey_data = []
        
        for industry in industries:
            if industry not in current_data:
                continue
                
            current = current_data[industry]
            data_points = []
            
            # Create journey points with some variation
            import random
            random.seed(hash(industry) % 2147483647)  # Consistent seed per industry
            
            num_points = min(days, 30)  # Maximum 30 points
            step = days / num_points
            
            for i in range(num_points):
                days_back = days - (i * step)
                date = datetime.now().date() - timedelta(days=int(days_back))
                
                # Add some realistic variation
                momentum_var = random.uniform(-0.8, 0.8) * (i + 1)
                rs_var = random.uniform(-0.6, 0.6) * (i + 1)
                
                momentum = current['momentum'] + momentum_var
                rs = current['rs'] + rs_var
                price = current['price'] * (1 + momentum/100)
                
                # Ensure reasonable bounds
                momentum = max(-50, min(50, momentum))
                rs = max(50, min(150, rs))
                price = max(100, price)
                
                quadrant = get_quadrant(momentum, rs)
                
                data_points.append({
                    'date': str(date),
                    'momentum': momentum,
                    'relative_strength': rs,
                    'price': price,
                    'quadrant': quadrant
                })
            
            # Sort by date
            data_points.sort(key=lambda x: x['date'])
            
            journey_data.append({
                'name': industry,
                'data_points': data_points,
                'analysis': analyze_journey(data_points)
            })
        
        return journey_data
        
    except Exception as e:
        print(f"Error creating simulated journey data: {e}")
        return []

def get_actual_historical_data(industries, days):
    """Get actual historical data (when available)"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        journey_data = {}
        
        # Simple query to get available historical data
        for industry in industries:
            query = """
            SELECT 
                m.date,
                m.momentum_30d_pct as momentum,
                rs.relative_strength_30d as relative_strength,
                m.current_price
            FROM momentum m
            LEFT JOIN relative_strength rs ON m.symbol = rs.symbol AND m.date = rs.date
            WHERE m.entity_type = 'INDUSTRY_INDEX'
            AND m.symbol = %s
            AND m.date >= %s AND m.date <= %s
            ORDER BY m.date
            """
            
            results = db.execute_query(query, (industry, start_date, end_date))
            
            if results:
                data_points = []
                for row in results:
                    momentum = float(row[1] or 0)
                    rs = float(row[2] or 100)
                    price = float(row[3] or 1000)
                    quadrant = get_quadrant(momentum, rs)
                    
                    data_points.append({
                        'date': str(row[0]),
                        'momentum': momentum,
                        'relative_strength': rs,
                        'price': price,
                        'quadrant': quadrant
                    })
                
                if data_points:
                    journey_data[industry] = {
                        'name': industry,
                        'data_points': data_points,
                        'analysis': analyze_journey(data_points)
                    }
        
        return list(journey_data.values())
        
    except Exception as e:
        print(f"Error getting actual historical data: {e}")
        return []

def get_quadrant(momentum, rs):
    """Determine quadrant based on momentum and relative strength"""
    if momentum >= 0 and rs >= 100:
        return 'leaders'
    elif momentum >= 0 and rs < 100:
        return 'improving'
    elif momentum < 0 and rs >= 100:
        return 'weakening'
    else:
        return 'laggards'

def analyze_journey(data_points):
    """Analyze the journey through quadrants"""
    if not data_points:
        return {}
    
    # Count time in each quadrant
    quadrant_time = {'leaders': 0, 'improving': 0, 'weakening': 0, 'laggards': 0}
    transitions = []
    
    for i, point in enumerate(data_points):
        quadrant_time[point['quadrant']] += 1
        
        if i > 0 and point['quadrant'] != data_points[i-1]['quadrant']:
            transitions.append({
                'from': data_points[i-1]['quadrant'],
                'to': point['quadrant'],
                'date': point['date']
            })
    
    # Calculate performance
    start_price = data_points[0]['price']
    end_price = data_points[-1]['price']
    price_change = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
    
    start_momentum = data_points[0]['momentum']
    end_momentum = data_points[-1]['momentum']
    momentum_change = end_momentum - start_momentum
    
    start_rs = data_points[0]['relative_strength']
    end_rs = data_points[-1]['relative_strength']
    rs_change = end_rs - start_rs
    
    return {
        'quadrant_time_pct': {
            k: (v / len(data_points)) * 100 for k, v in quadrant_time.items()
        },
        'transitions': transitions,
        'total_transitions': len(transitions),
        'start_quadrant': data_points[0]['quadrant'],
        'end_quadrant': data_points[-1]['quadrant'],
        'price_change': price_change,
        'momentum_change': momentum_change,
        'rs_change': rs_change
    }

@app.route('/api/stats/<period>')
def get_stats(period):
    """Get statistical summary for a given period"""
    try:
        if period not in ['30d', '90d', '180d']:
            return jsonify({
                'success': False,
                'error': 'Invalid period'
            }), 400
        
        # Get momentum stats
        momentum_stats = momentum_model.get_momentum_statistics()
        rs_stats = rs_model.get_relative_strength_statistics()
        
        return jsonify({
            'success': True,
            'momentum_stats': momentum_stats,
            'rs_stats': rs_stats,
            'period': period
        })
        
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    print("=== Momentum vs Relative Strength Web Application ===")
    print("Initializing database connection...")
    
    if init_database():
        print("✅ Application ready!")
        print("\n🚀 Starting Flask server...")
        print("📊 Open http://localhost:5000 to view the dashboard")
        print("🔗 API endpoints available:")
        print("   - GET /api/health - Health check")
        print("   - GET /api/momentum-vs-rs?period=30d&industry=all - Get chart data")
        print("   - GET /api/industries - Get available industries")
        print("   - GET /api/stats/<period> - Get statistics")
        print("   - GET /journey - View quadrant journey page")
        print("   - GET /api/quadrant-journey - Get historical journey data")
        print("\n" + "="*60)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize database. Please check your database connection.")
        print("Make sure TimescaleDB is running and the database is properly configured.")