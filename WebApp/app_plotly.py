from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load data with absolute paths
dataset = pd.read_csv(os.path.join(BASE_DIR, "ArrowSpine3.csv"))
datasetArrowGPIs = pd.read_csv(os.path.join(BASE_DIR, "ArrowGPIs.csv"))

# Aggregate Linear Regression Values (from notebook analysis)
aggregateRegValuesSlopeSlope = -0.001
aggregateRegValuesSlopeIntercept = -0.174
aggregateRegValuesIntSlope = -3.885
aggregateRegValuesIntIntercept = 237.637

def calculate_speed(initial_velocity, area_cross_section, coefficient_drag, arrow_mass, distance):
    """Calculate arrow velocity at given distance using drag model"""
    air_density = 0.0752  # lb/ft^3
    
    if isinstance(initial_velocity, (int, float)):
        runtime = 3
        time_of_flight = 0
        distance_traveled = 0
        acceleration = lambda v: -0.5 * air_density * area_cross_section * coefficient_drag * v**2 / arrow_mass
        velocity = initial_velocity
        dt = 0.001
        
        for t in range(int(runtime/dt)):
            velocity += acceleration(velocity) * dt
            time_of_flight += dt
            distance_traveled += velocity * dt
            if distance_traveled >= distance:
                break
        return velocity
    
    # Handle array input
    v_list = []
    for i in range(len(initial_velocity)):
        velocity = calculate_speed(initial_velocity[i], area_cross_section, 
                                 coefficient_drag, arrow_mass[i], distance)
        v_list.append(velocity)
    return np.array(v_list)

def calculate_time(initial_velocity, area_cross_section, coefficient_drag, arrow_mass, distance):
    """Calculate time of flight to given distance"""
    air_density = 0.0752  # lb/ft^3
    
    if isinstance(initial_velocity, (int, float)):
        runtime = 3
        time_of_flight = 0
        distance_traveled = 0
        acceleration = lambda v: -0.5 * air_density * area_cross_section * coefficient_drag * v**2 / arrow_mass
        velocity = initial_velocity
        dt = 0.001
        
        for t in range(int(runtime/dt)):
            velocity += acceleration(velocity) * dt
            time_of_flight += dt
            distance_traveled += velocity * dt
            if distance_traveled >= distance:
                break
        return time_of_flight
    
    # Handle array input
    t_list = []
    for i in range(len(initial_velocity)):
        time = calculate_time(initial_velocity[i], area_cross_section, 
                            coefficient_drag, arrow_mass[i], distance)
        t_list.append(time)
    return np.array(t_list)

def calculate_single_setup(params):
    """Calculate results for a single arrow setup"""
    # Extract all parameters with defaults
    p = {
        'chosenSpine': float(params.get('spine', 200)),
        'chosenArrowGPI': float(params.get('arrowGPI', 10.7)),
        'chosenPoundage': float(params.get('poundage', 71)),
        'chosenIBO': float(params.get('ibo', 335)),
        'chosenArrowLength': float(params.get('arrowLength', 28.25)),
        'chosenNockThroatAdder': float(params.get('nockThroatAdder', 0.5)),
        'chosenNockWeight': float(params.get('nockWeight', 6)),
        'chosenArrowWrapWeight': float(params.get('arrowWrapWeight', 0)),
        'chosenArrowWrapLength': float(params.get('arrowWrapLength', 4)),
        'chosenFletchDistanceFromShaftEnd': float(params.get('fletchDistance', 0.75)),
        'chosenFletchNumber': int(params.get('fletchNumber', 4)),
        'chosenFletchWeight': float(params.get('fletchWeight', 5)),
        'chosenFletchLength': float(params.get('fletchLength', 2.25)),
        'chosenFletchHeight': float(params.get('fletchHeight', 0.465)),
        'chosenDrawLength': float(params.get('drawLength', 29)),
        'chosenCoefDrag': float(params.get('coefDrag', 2)),
        'chosenArrowDiam': float(params.get('arrowDiam', 0.166)),
        'chosenFletchOffset': float(params.get('fletchOffset', 3))
    }
    
    # Calculate poundage range
    calcPoundage = np.linspace(30, 90, 30)
    
    # Calculate optimal point weight
    calcOpPointWeight = 150 + 25/5 * (-0.252 * p['chosenIBO'] + 81.8 - calcPoundage + 
                       (aggregateRegValuesSlopeSlope * p['chosenArrowLength'] + 
                        aggregateRegValuesSlopeIntercept) * p['chosenSpine'] + 
                       aggregateRegValuesIntSlope * p['chosenArrowLength'] + 
                       aggregateRegValuesIntIntercept)
    
    # Calculate total arrow mass
    calcTotalArrowMass = (p['chosenNockWeight'] + p['chosenArrowWrapWeight'] + 
                         p['chosenFletchNumber'] * p['chosenFletchWeight'] + 
                         p['chosenArrowGPI'] * p['chosenArrowLength'] + calcOpPointWeight)
    
    # Calculate FOC
    totalFletchWeight = p['chosenFletchNumber'] * p['chosenFletchWeight']
    totalShaftWeight = p['chosenArrowGPI'] * p['chosenArrowLength']
    
    centroidNock = p['chosenNockThroatAdder']
    centroidArrowWrap = p['chosenNockThroatAdder'] + p['chosenArrowWrapLength']/2
    centroidFletch = p['chosenFletchDistanceFromShaftEnd'] + p['chosenFletchLength']/3
    centroidShaft = p['chosenNockThroatAdder'] + p['chosenArrowLength']/2
    centroidPointWeight = p['chosenNockThroatAdder'] + p['chosenArrowLength']
    
    arrowLengthTotal = p['chosenArrowLength'] + p['chosenNockThroatAdder']
    
    calcFOC = (100 * ((p['chosenNockWeight'] * centroidNock + 
                      p['chosenArrowWrapWeight'] * centroidArrowWrap + 
                      totalFletchWeight * centroidFletch + 
                      totalShaftWeight * centroidShaft + 
                      calcOpPointWeight * centroidPointWeight) / calcTotalArrowMass - 
                     arrowLengthTotal/2)) / arrowLengthTotal
    
    # Calculate kinetic energy and FPS
    calcKENominal = 0.5 * ((350/15.43)/1000) * ((p['chosenIBO'] - 10*(30-p['chosenDrawLength']) - 
                                                 2*(70-calcPoundage)) * 0.3048)**2
    calcFPS = np.sqrt(calcKENominal * 2 / ((calcTotalArrowMass/15.43)/1000)) / 0.3048
    calcKE = 0.5 * ((calcTotalArrowMass/15.43)/1000) * (calcFPS * 0.3048)**2
    calcMomentum = ((calcTotalArrowMass/15.43)/1000) * (calcFPS * 0.3048)
    
    # Calculate arrow cross-sectional area
    area_cross_section = (np.pi * ((p['chosenArrowDiam']/12)/2)**2 + 
                         p['chosenFletchNumber'] * 0.5 * p['chosenFletchLength']/12 * 
                         p['chosenFletchHeight']/12 * p['chosenFletchOffset']/90)
    
    # Calculate velocities at different distances
    calcFPS20yd = calculate_speed(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                 calcTotalArrowMass/7000, 60)
    calcFPS40yd = calculate_speed(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                 calcTotalArrowMass/7000, 120)
    calcFPS60yd = calculate_speed(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                 calcTotalArrowMass/7000, 180)
    
    # Calculate time of flight at different distances
    calcTOF20yd = calculate_time(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                calcTotalArrowMass/7000, 60)
    calcTOF40yd = calculate_time(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                calcTotalArrowMass/7000, 120)
    calcTOF60yd = calculate_time(calcFPS, area_cross_section, p['chosenCoefDrag'], 
                                calcTotalArrowMass/7000, 180)
    
    # Calculate KE at different distances
    calcKE20yd = 0.5 * ((calcTotalArrowMass/15.43)/1000) * (calcFPS20yd * 0.3048)**2
    calcKE40yd = 0.5 * ((calcTotalArrowMass/15.43)/1000) * (calcFPS40yd * 0.3048)**2
    calcKE60yd = 0.5 * ((calcTotalArrowMass/15.43)/1000) * (calcFPS60yd * 0.3048)**2
    
    # Calculate momentum at different distances
    calcMomentum20yd = ((calcTotalArrowMass/15.43)/1000) * (calcFPS20yd * 0.3048)
    calcMomentum40yd = ((calcTotalArrowMass/15.43)/1000) * (calcFPS40yd * 0.3048)
    calcMomentum60yd = ((calcTotalArrowMass/15.43)/1000) * (calcFPS60yd * 0.3048)
    
    # Calculate single point values for selected poundage
    selectedPoundage = p['chosenPoundage']
    idx = np.argmin(np.abs(calcPoundage - selectedPoundage))
    
    return {
        'data': {
            'calcPoundage': calcPoundage,
            'calcOpPointWeight': calcOpPointWeight,
            'calcTotalArrowMass': calcTotalArrowMass,
            'calcFOC': calcFOC,
            'calcKE': calcKE,
            'calcFPS': calcFPS,
            'calcMomentum': calcMomentum,
            'calcFPS20yd': calcFPS20yd,
            'calcFPS40yd': calcFPS40yd,
            'calcFPS60yd': calcFPS60yd,
            'calcTOF20yd': calcTOF20yd,
            'calcTOF40yd': calcTOF40yd,
            'calcTOF60yd': calcTOF60yd,
            'calcKE20yd': calcKE20yd,
            'calcKE40yd': calcKE40yd,
            'calcKE60yd': calcKE60yd,
            'calcMomentum20yd': calcMomentum20yd,
            'calcMomentum40yd': calcMomentum40yd,
            'calcMomentum60yd': calcMomentum60yd
        },
        'values': {
            'optimalPointWeight': float(calcOpPointWeight[idx]),
            'totalArrowMass': float(calcTotalArrowMass[idx]),
            'foc': float(calcFOC[idx]),
            'fps': float(calcFPS[idx]),
            'ke': float(calcKE[idx]),
            'momentum': float(calcMomentum[idx])
        }
    }

@app.route('/')
def index():
    return render_template('index_plotly.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/images/<path:filename>')
def send_image(filename):
    """Serve images from current directory or parent directory"""
    # First try current directory
    if os.path.exists(os.path.join(BASE_DIR, filename)):
        return send_from_directory(BASE_DIR, filename)
    # Then try parent directory
    parent_dir = os.path.dirname(BASE_DIR)
    return send_from_directory(parent_dir, filename)

@app.route('/readme')
def get_readme():
    """Serve README.md content"""
    try:
        # Try to read the main README first (copied from parent directory)
        readme_path = os.path.join(BASE_DIR, 'README_main.md')
        if not os.path.exists(readme_path):
            # Fallback to local README if main doesn't exist
            readme_path = os.path.join(BASE_DIR, 'README.md')
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/calculate_comparison', methods=['POST'])
def calculate_comparison():
    """Handle comparison calculations for two setups"""
    try:
        data = request.json
        
        # Calculate for both setups
        setup1_params = data.get('setup1', {})
        setup2_params = data.get('setup2', {})
        
        setup1_results = calculate_single_setup(setup1_params)
        setup2_results = calculate_single_setup(setup2_params)
        
        # Create comparison plots
        comparison_plots = create_comparison_plots(
            setup1_results['data'], setup2_results['data'],
            setup1_params, setup2_params
        )
        
        return jsonify({
            'success': True,
            'setup1': {
                'values': setup1_results['values']
            },
            'setup2': {
                'values': setup2_results['values']
            },
            'plots': comparison_plots
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def create_comparison_plots(data1, data2, params1, params2):
    """Create comparison plots showing both setups using Plotly"""
    plots = {}
    
    # Extract data for both setups
    calcPoundage = data1['calcPoundage']
    
    # Find indices for current poundage values
    idx1 = np.argmin(np.abs(calcPoundage - params1['poundage']))
    idx2 = np.argmin(np.abs(calcPoundage - params2['poundage']))
    
    # Define colors
    color1 = '#1976D2'
    color2 = '#FF9800'
    
    # Create all plots with larger fonts and clearer styling
    default_layout = dict(
        font=dict(size=12),
        xaxis=dict(
            title_font=dict(size=14), 
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='black'
        ),
        yaxis=dict(
            title_font=dict(size=14), 
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='black'
        ),
        title_font=dict(size=16),
        showlegend=False,  # Default to no legend
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode=False,  # Disable hover tooltips
        margin=dict(l=60, r=20, t=50, b=50)  # Reduced right margin for larger plots
    )
    
    # Layout for plots with distance legends
    distance_legend_layout = dict(
        font=dict(size=12),
        xaxis=dict(
            title_font=dict(size=14), 
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='black'
        ),
        yaxis=dict(
            title_font=dict(size=14), 
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='black'
        ),
        title_font=dict(size=16),
        showlegend=True,
        legend=dict(
            font=dict(size=12),
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode=False,  # Disable hover tooltips
        margin=dict(l=60, r=20, t=50, b=80)  # Reduced right margin, extra bottom for legend
    )
    
    # 1. Optimal Point Weight Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcOpPointWeight'], 
                            mode='lines', name='Setup 1', 
                            line=dict(color=color1, width=3)))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcOpPointWeight'], 
                            mode='lines', name='Setup 2', 
                            line=dict(color=color2, width=3)))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcOpPointWeight'][idx1]], 
                            mode='markers+text', name='Current 1',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcOpPointWeight'][idx1]:.0f}gr"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcOpPointWeight'][idx2]], 
                            mode='markers+text', name='Current 2',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcOpPointWeight'][idx2]:.0f}gr"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs Optimal Point Weight [grains]",
                     xaxis_title="Poundage", yaxis_title="Point Weight [gr]",
                     **default_layout)
    plots['pointWeight'] = fig.to_json()
    
    # 2. Total Arrow Mass Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcTotalArrowMass'], 
                            mode='lines', name='Setup 1', 
                            line=dict(color=color1, width=3)))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcTotalArrowMass'], 
                            mode='lines', name='Setup 2', 
                            line=dict(color=color2, width=3)))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcTotalArrowMass'][idx1]], 
                            mode='markers+text', name='Current 1',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcTotalArrowMass'][idx1]:.0f}gr"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcTotalArrowMass'][idx2]], 
                            mode='markers+text', name='Current 2',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcTotalArrowMass'][idx2]:.0f}gr"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs Total Arrow Mass [grains]",
                     xaxis_title="Poundage", yaxis_title="Total Mass [gr]",
                     **default_layout)
    plots['totalMass'] = fig.to_json()
    
    # 3. FOC Plot with bands
    fig = go.Figure()
    
    # Add FOC bands
    fig.add_shape(type="rect", x0=30, x1=90, y0=0, y1=12,
                  fillcolor="red", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=12, y1=19,
                  fillcolor="#90CAF9", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=19, y1=30,
                  fillcolor="#42A5F5", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=30, y1=35,
                  fillcolor="#1E88E5", opacity=0.3, layer="below", line_width=0)
    
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcFOC'], 
                            mode='lines', name='Setup 1', 
                            line=dict(color=color1, width=3)))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcFOC'], 
                            mode='lines', name='Setup 2', 
                            line=dict(color=color2, width=3)))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcFOC'][idx1]], 
                            mode='markers+text', name='Current 1',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcFOC'][idx1]:.1f}%"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcFOC'][idx2]], 
                            mode='markers+text', name='Current 2',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcFOC'][idx2]:.1f}%"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs FOC [%]",
                     xaxis_title="Poundage", yaxis_title="FOC [%]",
                     yaxis_range=[0, 35],
                     **default_layout)
    plots['foc'] = fig.to_json()
    
    # 4. FPS Plot with distance lines
    fig = go.Figure()
    
    # Add a dummy trace for the legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='0yd', line=dict(color='gray', width=3),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='20yd', line=dict(color='gray', width=2, dash='dash'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='40yd', line=dict(color='gray', width=2, dash='dashdot'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='60yd', line=dict(color='gray', width=2, dash='dot'),
                            showlegend=True))
    
    # Setup 1 lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcFPS'], 
                            mode='lines', name='Setup 1 (0yd)', 
                            line=dict(color=color1, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcFPS20yd'], 
                            mode='lines', name='Setup 1 (20yd)', 
                            line=dict(color=color1, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcFPS40yd'], 
                            mode='lines', name='Setup 1 (40yd)', 
                            line=dict(color=color1, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcFPS60yd'], 
                            mode='lines', name='Setup 1 (60yd)', 
                            line=dict(color=color1, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Setup 2 lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcFPS'], 
                            mode='lines', name='Setup 2 (0yd)', 
                            line=dict(color=color2, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcFPS20yd'], 
                            mode='lines', name='Setup 2 (20yd)', 
                            line=dict(color=color2, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcFPS40yd'], 
                            mode='lines', name='Setup 2 (40yd)', 
                            line=dict(color=color2, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcFPS60yd'], 
                            mode='lines', name='Setup 2 (60yd)', 
                            line=dict(color=color2, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcFPS'][idx1]], 
                            mode='markers+text', 
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcFPS'][idx1]:.0f}fps"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcFPS'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcFPS'][idx2]:.0f}fps"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    # Add 60yd points with labels
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcFPS60yd'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=10),
                            text=[f"{data1['calcFPS60yd'][idx1]:.0f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color1),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcFPS60yd'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=10),
                            text=[f"{data2['calcFPS60yd'][idx2]:.0f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color2),
                            opacity=0.7,
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs FPS",
                     xaxis_title="Poundage", yaxis_title="FPS",
                     **distance_legend_layout)
    plots['fps'] = fig.to_json()
    
    # 5. Kinetic Energy Plot with distance lines and bands
    fig = go.Figure()
    
    # Add KE bands
    fig.add_shape(type="rect", x0=30, x1=90, y0=0, y1=35,
                  fillcolor="red", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=35, y1=55,
                  fillcolor="#90CAF9", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=55, y1=88,
                  fillcolor="#42A5F5", opacity=0.3, layer="below", line_width=0)
    fig.add_shape(type="rect", x0=30, x1=90, y0=88, y1=150,
                  fillcolor="#1E88E5", opacity=0.3, layer="below", line_width=0)
    
    # Add dummy traces for legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='0yd', line=dict(color='gray', width=3),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='20yd', line=dict(color='gray', width=2, dash='dash'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='40yd', line=dict(color='gray', width=2, dash='dashdot'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='60yd', line=dict(color='gray', width=2, dash='dot'),
                            showlegend=True))
    
    # Setup 1 KE lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcKE'], 
                            mode='lines', name='Setup 1 (0yd)', 
                            line=dict(color=color1, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcKE20yd'], 
                            mode='lines', name='Setup 1 (20yd)', 
                            line=dict(color=color1, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcKE40yd'], 
                            mode='lines', name='Setup 1 (40yd)', 
                            line=dict(color=color1, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcKE60yd'], 
                            mode='lines', name='Setup 1 (60yd)', 
                            line=dict(color=color1, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Setup 2 KE lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcKE'], 
                            mode='lines', name='Setup 2 (0yd)', 
                            line=dict(color=color2, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcKE20yd'], 
                            mode='lines', name='Setup 2 (20yd)', 
                            line=dict(color=color2, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcKE40yd'], 
                            mode='lines', name='Setup 2 (40yd)', 
                            line=dict(color=color2, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcKE60yd'], 
                            mode='lines', name='Setup 2 (60yd)', 
                            line=dict(color=color2, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcKE'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcKE'][idx1]:.0f}J"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcKE'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcKE'][idx2]:.0f}J"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    # Add 60yd points with labels
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcKE60yd'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=10),
                            text=[f"{data1['calcKE60yd'][idx1]:.0f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color1),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcKE60yd'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=10),
                            text=[f"{data2['calcKE60yd'][idx2]:.0f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color2),
                            opacity=0.7,
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs Kinetic Energy [J]",
                     xaxis_title="Poundage", yaxis_title="KE [J]",
                     yaxis_range=[0, 150],
                     **distance_legend_layout)
    plots['ke'] = fig.to_json()
    
    # 6. Momentum Plot with distance lines
    fig = go.Figure()
    
    # Add dummy traces for legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='0yd', line=dict(color='gray', width=3),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='20yd', line=dict(color='gray', width=2, dash='dash'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='40yd', line=dict(color='gray', width=2, dash='dashdot'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='60yd', line=dict(color='gray', width=2, dash='dot'),
                            showlegend=True))
    
    # Setup 1 momentum lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcMomentum'], 
                            mode='lines', name='Setup 1 (0yd)', 
                            line=dict(color=color1, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcMomentum20yd'], 
                            mode='lines', name='Setup 1 (20yd)', 
                            line=dict(color=color1, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcMomentum40yd'], 
                            mode='lines', name='Setup 1 (40yd)', 
                            line=dict(color=color1, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcMomentum60yd'], 
                            mode='lines', name='Setup 1 (60yd)', 
                            line=dict(color=color1, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Setup 2 momentum lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcMomentum'], 
                            mode='lines', name='Setup 2 (0yd)', 
                            line=dict(color=color2, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcMomentum20yd'], 
                            mode='lines', name='Setup 2 (20yd)', 
                            line=dict(color=color2, width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcMomentum40yd'], 
                            mode='lines', name='Setup 2 (40yd)', 
                            line=dict(color=color2, width=2, dash='dashdot'),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcMomentum60yd'], 
                            mode='lines', name='Setup 2 (60yd)', 
                            line=dict(color=color2, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Add current points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcMomentum'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcMomentum'][idx1]:.2f}"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcMomentum'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcMomentum'][idx2]:.2f}"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    # Add 60yd points with labels
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcMomentum60yd'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=10),
                            text=[f"{data1['calcMomentum60yd'][idx1]:.2f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color1),
                            opacity=0.7,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcMomentum60yd'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=10),
                            text=[f"{data2['calcMomentum60yd'][idx2]:.2f}"],
                            textposition="bottom center",
                            textfont=dict(size=11, color=color2),
                            opacity=0.7,
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs Momentum [kg·m/s]",
                     xaxis_title="Poundage", yaxis_title="Momentum",
                     **distance_legend_layout)
    plots['momentum'] = fig.to_json()
    
    # 7. Time of Flight Plot
    fig = go.Figure()
    
    # Add dummy traces for legend
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='20yd', line=dict(color='gray', width=3),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='40yd', line=dict(color='gray', width=2, dash='dash'),
                            showlegend=True))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', 
                            name='60yd', line=dict(color='gray', width=2, dash='dot'),
                            showlegend=True))
    
    # Setup 1 TOF lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcTOF20yd'], 
                            mode='lines', name='Setup 1 (20yd)', 
                            line=dict(color=color1, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcTOF40yd'], 
                            mode='lines', name='Setup 1 (40yd)', 
                            line=dict(color=color1, width=2, dash='dash'),
                            opacity=0.8,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data1['calcTOF60yd'], 
                            mode='lines', name='Setup 1 (60yd)', 
                            line=dict(color=color1, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Setup 2 TOF lines
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcTOF20yd'], 
                            mode='lines', name='Setup 2 (20yd)', 
                            line=dict(color=color2, width=3),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcTOF40yd'], 
                            mode='lines', name='Setup 2 (40yd)', 
                            line=dict(color=color2, width=2, dash='dash'),
                            opacity=0.8,
                            showlegend=False))
    fig.add_trace(go.Scatter(x=calcPoundage, y=data2['calcTOF60yd'], 
                            mode='lines', name='Setup 2 (60yd)', 
                            line=dict(color=color2, width=2, dash='dot'),
                            opacity=0.7,
                            showlegend=False))
    
    # Add 60yd points
    fig.add_trace(go.Scatter(x=[calcPoundage[idx1]], y=[data1['calcTOF60yd'][idx1]], 
                            mode='markers+text',
                            marker=dict(color=color1, size=15),
                            text=[f"{data1['calcTOF60yd'][idx1]:.3f}s"],
                            textposition="top right",
                            textfont=dict(size=12, color=color1),
                            showlegend=False))
    fig.add_trace(go.Scatter(x=[calcPoundage[idx2]], y=[data2['calcTOF60yd'][idx2]], 
                            mode='markers+text',
                            marker=dict(color=color2, size=15),
                            text=[f"{data2['calcTOF60yd'][idx2]:.3f}s"],
                            textposition="top right",
                            textfont=dict(size=12, color=color2),
                            showlegend=False))
    
    fig.update_layout(title="Poundage vs Time of Flight [s]",
                     xaxis_title="Poundage", yaxis_title="Time [s]",
                     **distance_legend_layout)
    plots['tof'] = fig.to_json()
    
    return plots

if __name__ == '__main__':
    # For development
    app.run(debug=False, host='0.0.0.0', port=5001)