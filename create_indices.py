#!/usr/bin/env python3
"""
Convenience script to create industry indices from project root
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main script
from src.utils.create_industry_indices import main

if __name__ == "__main__":
    main()