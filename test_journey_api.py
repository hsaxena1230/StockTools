#!/usr/bin/env python3
"""
Test script for the journey API functionality
"""
import sys
import os
sys.path.append('.')

from datetime import datetime, timedelta
import random

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

def create_test_journey_data(industries, days):
    """Create test journey data"""
    journey_data = []
    
    # Mock current data
    mock_current_data = {
        'Agricultural Inputs': {'momentum': 9.3, 'rs': 113.8, 'price': 1159.13},
        'Auto Parts': {'momentum': 6.3, 'rs': 105.0, 'price': 1028.01},
        'Steel': {'momentum': -2.1, 'rs': 95.5, 'price': 850.45},
        'Information Technology Services': {'momentum': 12.5, 'rs': 108.2, 'price': 1245.67},
        'Pharmaceutical': {'momentum': 4.8, 'rs': 102.3, 'price': 980.33}
    }
    
    for industry in industries:
        if industry not in mock_current_data:
            continue
            
        current = mock_current_data[industry]
        data_points = []
        
        # Create journey points with some variation
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

def test_journey_api():
    """Test the journey data generation"""
    print("🧪 Testing Journey Data Generation")
    print("=" * 50)
    
    test_industries = ['Agricultural Inputs', 'Auto Parts', 'Steel']
    days = 30
    
    # Generate test data
    journey_data = create_test_journey_data(test_industries, days)
    
    print(f"📊 Generated data for {len(journey_data)} industries")
    print()
    
    for industry_data in journey_data:
        name = industry_data['name']
        points = industry_data['data_points']
        analysis = industry_data['analysis']
        
        print(f"🏭 {name}")
        print(f"   📈 Data Points: {len(points)}")
        print(f"   📅 Date Range: {points[0]['date']} to {points[-1]['date']}")
        print(f"   🚀 Journey: {analysis['start_quadrant']} → {analysis['end_quadrant']}")
        print(f"   💰 Price Change: {analysis['price_change']:.2f}%")
        print(f"   🔄 Transitions: {analysis['total_transitions']}")
        
        # Show quadrant distribution
        quadrant_dist = analysis['quadrant_time_pct']
        for quadrant, pct in quadrant_dist.items():
            if pct > 0:
                print(f"      {quadrant}: {pct:.0f}%")
        print()
    
    print("✅ Journey data generation test completed successfully!")
    return journey_data

if __name__ == "__main__":
    test_journey_api()