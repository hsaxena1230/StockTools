# Momentum vs Relative Strength Web Dashboard

Interactive web dashboard for analyzing momentum versus relative strength for industry indices.

## Features

- **Interactive Scatter Plot**: Visualize momentum vs relative strength with color-coded quadrants
- **Time Period Selection**: View data for 30, 90, or 180-day periods
- **Industry Filtering**: Filter by specific industries or view all
- **Statistics Panel**: View top performers and summary statistics
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Data**: Connects to your TimescaleDB database

## Directory Structure

```
web/
├── app.py                 # Flask application server
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Main dashboard HTML
└── static/
    ├── css/
    │   └── style.css     # Dashboard styling
    └── js/
        └── chart.js      # Chart logic and API calls
```

## Prerequisites

1. **Database Setup**: Ensure you have momentum and relative_strength data in your TimescaleDB
2. **Python Environment**: Python 3.8+ with pip
3. **Data**: Run momentum and relative strength calculations first:
   ```bash
   # From the main StockTools directory
   python calculate_momentum.py --action calculate
   python calculate_relative_strength.py --action calculate
   ```

## Installation

1. **Install Python dependencies**:
   ```bash
   cd web
   pip install -r requirements.txt
   ```

2. **Verify database connection**: Make sure your `config/database.py` is properly configured

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Access the dashboard**:
   Open your browser and go to: `http://localhost:5000`

## API Endpoints

The Flask application provides several API endpoints:

- `GET /api/health` - Health check
- `GET /api/momentum-vs-rs?period=30d&industry=all` - Get chart data
- `GET /api/industries` - Get available industries
- `GET /api/stats/<period>` - Get statistics for a period

### Example API Usage

```bash
# Get 30-day data for all industries
curl "http://localhost:5000/api/momentum-vs-rs?period=30d&industry=all"

# Get available industries
curl "http://localhost:5000/api/industries"

# Check API health
curl "http://localhost:5000/api/health"
```

## Chart Interpretation

The scatter plot shows industries plotted by their momentum (X-axis) vs relative strength (Y-axis):

### Quadrants:
- **Green (Top-Right)**: High Momentum + High Relative Strength (Strong Outperformers)
- **Blue (Top-Left)**: Low Momentum + High Relative Strength (Relative Strength Leaders)
- **Red (Bottom-Left)**: Low Momentum + Low Relative Strength (Underperformers)
- **Orange (Bottom-Right)**: High Momentum + Low Relative Strength (Momentum Leaders)

### Features:
- **Hover**: See detailed information for each industry
- **Click**: View additional industry details
- **Dropdown**: Switch between 30d, 90d, and 180d periods
- **Filter**: Show specific industries or all industries

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
python -c "from config.database import DatabaseConnection; db = DatabaseConnection(); print('✅ Connected' if db.connect() else '❌ Failed')"
```

### No Data Displayed
1. Verify momentum data exists:
   ```sql
   SELECT COUNT(*) FROM momentum WHERE entity_type = 'INDUSTRY_INDEX';
   ```

2. Verify relative strength data exists:
   ```sql
   SELECT COUNT(*) FROM relative_strength WHERE entity_type = 'INDUSTRY_INDEX';
   ```

3. Run calculations if data is missing:
   ```bash
   python calculate_momentum.py --action calculate
   python calculate_relative_strength.py --action calculate
   ```

### Port Already in Use
If port 5000 is busy, modify the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port here
```

## Customization

### Styling
- Modify `static/css/style.css` to change colors, fonts, or layout
- The CSS uses CSS Grid and Flexbox for responsive design

### Chart Configuration
- Edit `static/js/chart.js` to modify Chart.js settings
- Change colors, add new chart types, or modify interactions

### API Extensions
- Add new endpoints in `app.py`
- Extend data queries for additional metrics
- Add caching or real-time updates

## Performance Tips

1. **Database Indexing**: Ensure proper indexes exist on momentum and relative_strength tables
2. **Data Caching**: Consider adding Redis for caching API responses
3. **Pagination**: For large datasets, implement pagination in API endpoints
4. **Compression**: Enable gzip compression in Flask for faster loading

## Security Considerations

- The application runs in debug mode by default (for development)
- For production deployment:
  - Set `debug=False`
  - Use a proper WSGI server (gunicorn, uWSGI)
  - Add authentication if needed
  - Enable HTTPS
  - Validate all inputs

## Future Enhancements

- [ ] Real-time updates with WebSocket
- [ ] Export data to CSV/Excel
- [ ] Historical trend analysis
- [ ] Alert system for significant changes
- [ ] Mobile app version
- [ ] Advanced filtering options