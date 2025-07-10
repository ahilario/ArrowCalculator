#!/usr/bin/env python
"""Simple runner script for the Arrow Spine Calculator"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_plotly import app

if __name__ == '__main__':
    print("\n🏹 Arrow Spine Calculator")
    print("=" * 40)
    print(f"Starting server on http://localhost:5001")
    print("Press Ctrl+C to stop the server")
    print("=" * 40 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped.")