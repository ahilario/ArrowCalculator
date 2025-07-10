# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an archery arrow spine calculator that uses linear regression to predict optimal arrow configurations based on arrow parameters, bow specifications, and desired poundage. The project consists of:

1. **Jupyter Notebook Analysis** (`ArrowSpineCharts-withBounds-Final.ipynb`): Core research and analysis using Bokeh for interactive visualization
2. **Flask Web Application** (`WebApp/`): Simple web interface for the calculator

## Common Development Commands

### Running the Jupyter Notebook
```bash
jupyter notebook ArrowSpineCharts-withBounds-Final.ipynb
```

### Running the Flask Web App
```bash
cd WebApp
python app.py
```
The app will run on http://localhost:5000 in debug mode.

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Code Architecture

### Core Calculation Logic
The core physics calculations are based on arrow dynamics modeling with these key equations:

1. **Optimal Point Weight Calculation**: Uses aggregate linear regression values to calculate optimal point weight based on bow IBO, poundage, arrow length, and spine
2. **FOC (Front of Center) Calculation**: Calculates arrow balance point considering all components (nock, wrap, fletching, shaft, point)
3. **Kinetic Energy and Momentum**: Uses bow IBO and draw specifications to calculate arrow performance
4. **Drag Modeling**: Implements numerical integration for velocity decay over distance using drag coefficient

### Data Files
- `ArrowSpine3.csv`: Main dataset with arrow spine recommendations by manufacturer
- `ArrowGPIs.csv`: Arrow shaft GPI (grains per inch) data by manufacturer and spine
- CSV format includes: Shaft brand, spine values, arrow lengths, poundage bounds

### Key Functions in Notebook
- `performLinRegbyArrowLength()`: Linear regression for spine vs poundage relationship
- `calculateFOCdf()`: Calculates Front of Center percentage
- `calculate_speed()` / `calculate_time()`: Numerical integration for arrow flight physics

### Web App Structure
- `app.py`: Flask server with `/calculate` endpoint for spine calculations
- `static/app.js`: Frontend JavaScript using Chart.js for visualization
- `templates/index.html`: Simple form interface

The calculations assume a mass-spring system model for arrow dynamics with manufacturer-specific calibration data.