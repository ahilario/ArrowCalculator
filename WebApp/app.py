from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from bokeh.plotting import figure
from bokeh.layouts import column, gridplot
from bokeh.embed import json_item
from bokeh.models import Band, ColumnDataSource, Label
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
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/images/<path:filename>')
def send_image(filename):
    """Serve images from parent directory"""
    parent_dir = os.path.dirname(BASE_DIR)
    return send_from_directory(parent_dir, filename)

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

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        
        # Extract all parameters with defaults
        params = {
            'chosenSpine': float(data.get('spine', 200)),
            'chosenArrowGPI': float(data.get('arrowGPI', 10.7)),
            'chosenPoundage': float(data.get('poundage', 71)),
            'chosenIBO': float(data.get('ibo', 335)),
            'chosenArrowLength': float(data.get('arrowLength', 28.25)),
            'chosenNockThroatAdder': float(data.get('nockThroatAdder', 0.5)),
            'chosenNockWeight': float(data.get('nockWeight', 6)),
            'chosenArrowWrapWeight': float(data.get('arrowWrapWeight', 0)),
            'chosenArrowWrapLength': float(data.get('arrowWrapLength', 4)),
            'chosenFletchDistanceFromShaftEnd': float(data.get('fletchDistance', 0.75)),
            'chosenFletchNumber': int(data.get('fletchNumber', 4)),
            'chosenFletchWeight': float(data.get('fletchWeight', 5)),
            'chosenFletchLength': float(data.get('fletchLength', 2.25)),
            'chosenFletchHeight': float(data.get('fletchHeight', 0.465)),
            'chosenDrawLength': float(data.get('drawLength', 29)),
            'chosenCoefDrag': float(data.get('coefDrag', 2)),
            'chosenArrowDiam': float(data.get('arrowDiam', 0.166)),
            'chosenFletchOffset': float(data.get('fletchOffset', 3))
        }
        
        # Calculate poundage range
        calcPoundage = np.linspace(30, 90, 30)
        
        # Calculate optimal point weight
        calcOpPointWeight = 150 + 25/5 * (-0.252 * params['chosenIBO'] + 81.8 - calcPoundage + 
                           (aggregateRegValuesSlopeSlope * params['chosenArrowLength'] + 
                            aggregateRegValuesSlopeIntercept) * params['chosenSpine'] + 
                           aggregateRegValuesIntSlope * params['chosenArrowLength'] + 
                           aggregateRegValuesIntIntercept)
        
        # Calculate total arrow mass
        calcTotalArrowMass = (params['chosenNockWeight'] + params['chosenArrowWrapWeight'] + 
                             params['chosenFletchNumber'] * params['chosenFletchWeight'] + 
                             params['chosenArrowGPI'] * params['chosenArrowLength'] + calcOpPointWeight)
        
        # Calculate FOC
        totalFletchWeight = params['chosenFletchNumber'] * params['chosenFletchWeight']
        totalShaftWeight = params['chosenArrowGPI'] * params['chosenArrowLength']
        
        centroidNock = params['chosenNockThroatAdder']
        centroidArrowWrap = params['chosenNockThroatAdder'] + params['chosenArrowWrapLength']/2
        centroidFletch = params['chosenFletchDistanceFromShaftEnd'] + params['chosenFletchLength']/3
        centroidShaft = params['chosenNockThroatAdder'] + params['chosenArrowLength']/2
        centroidPointWeight = params['chosenNockThroatAdder'] + params['chosenArrowLength']
        
        arrowLengthTotal = params['chosenArrowLength'] + params['chosenNockThroatAdder']
        
        calcFOC = (100 * ((params['chosenNockWeight'] * centroidNock + 
                          params['chosenArrowWrapWeight'] * centroidArrowWrap + 
                          totalFletchWeight * centroidFletch + 
                          totalShaftWeight * centroidShaft + 
                          calcOpPointWeight * centroidPointWeight) / calcTotalArrowMass - 
                         arrowLengthTotal/2)) / arrowLengthTotal
        
        # Calculate kinetic energy and FPS
        calcKENominal = 0.5 * ((350/15.43)/1000) * ((params['chosenIBO'] - 10*(30-params['chosenDrawLength']) - 
                                                     2*(70-calcPoundage)) * 0.3048)**2
        calcFPS = np.sqrt(calcKENominal * 2 / ((calcTotalArrowMass/15.43)/1000)) / 0.3048
        calcKE = 0.5 * ((calcTotalArrowMass/15.43)/1000) * (calcFPS * 0.3048)**2
        calcMomentum = ((calcTotalArrowMass/15.43)/1000) * (calcFPS * 0.3048)
        
        # Calculate arrow cross-sectional area
        area_cross_section = (np.pi * ((params['chosenArrowDiam']/12)/2)**2 + 
                             params['chosenFletchNumber'] * 0.5 * params['chosenFletchLength']/12 * 
                             params['chosenFletchHeight']/12 * params['chosenFletchOffset']/90)
        
        # Calculate velocities at different distances
        calcFPS20yd = calculate_speed(calcFPS, area_cross_section, params['chosenCoefDrag'], 
                                     calcTotalArrowMass/7000, 60)
        calcFPS40yd = calculate_speed(calcFPS, area_cross_section, params['chosenCoefDrag'], 
                                     calcTotalArrowMass/7000, 120)
        calcFPS60yd = calculate_speed(calcFPS, area_cross_section, params['chosenCoefDrag'], 
                                     calcTotalArrowMass/7000, 180)
        
        # Create plots
        plots = create_plots(calcPoundage, calcOpPointWeight, calcTotalArrowMass, calcFOC, 
                           calcKE, calcFPS, calcMomentum, calcFPS20yd, calcFPS40yd, calcFPS60yd)
        
        # Calculate single point values for selected poundage
        selectedPoundage = params['chosenPoundage']
        idx = np.argmin(np.abs(calcPoundage - selectedPoundage))
        
        return jsonify({
            'success': True,
            'plots': plots,
            'values': {
                'optimalPointWeight': float(calcOpPointWeight[idx]),
                'totalArrowMass': float(calcTotalArrowMass[idx]),
                'foc': float(calcFOC[idx]),
                'fps': float(calcFPS[idx]),
                'ke': float(calcKE[idx]),
                'momentum': float(calcMomentum[idx])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def create_comparison_plots(data1, data2, params1, params2):
    """Create comparison plots showing both setups"""
    plots = {}
    
    # Extract data for both setups
    calcPoundage = data1['calcPoundage']
    
    # Optimal Point Weight Plot
    p1 = figure(title="Poundage vs Optimal Point Weight [grains]",
                x_axis_label="Poundage", y_axis_label="Point Weight [gr]",
                sizing_mode='stretch_both', min_width=350, min_height=350)
    p1.title.text_font_size = "18pt"
    p1.xaxis.axis_label_text_font_size = "14pt"
    p1.yaxis.axis_label_text_font_size = "14pt"
    p1.xaxis.major_label_text_font_size = "12pt"
    p1.yaxis.major_label_text_font_size = "12pt"
    p1.legend.label_text_font_size = "12pt"
    p1.line(calcPoundage, data1['calcOpPointWeight'], line_width=4, color="#1976D2", legend_label="Setup 1")
    p1.line(calcPoundage, data2['calcOpPointWeight'], line_width=4, color="#FF9800", legend_label="Setup 2")
    
    # Find indices for current poundage values
    idx1 = np.argmin(np.abs(calcPoundage - params1['poundage']))
    idx2 = np.argmin(np.abs(calcPoundage - params2['poundage']))
    
    # Add points with exact values from the arrays
    p1.circle([calcPoundage[idx1]], [data1['calcOpPointWeight'][idx1]], 
             size=16, color="#1976D2", legend_label="Current 1")
    p1.circle([calcPoundage[idx2]], [data2['calcOpPointWeight'][idx2]], 
             size=16, color="#FF9800", legend_label="Current 2")
    
    # Add labels for the points
    label1 = Label(x=calcPoundage[idx1], y=data1['calcOpPointWeight'][idx1], 
                   text=f"{data1['calcOpPointWeight'][idx1]:.0f}gr",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcOpPointWeight'][idx2], 
                   text=f"{data2['calcOpPointWeight'][idx2]:.0f}gr",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p1.add_layout(label1)
    p1.add_layout(label2)
    p1.legend.location = "top_right"
    plots['pointWeight'] = json.dumps(json_item(p1))
    
    # Total Arrow Mass Plot
    p2 = figure(title="Poundage vs Total Arrow Mass [grains]",
                x_axis_label="Poundage", y_axis_label="Total Mass [gr]",
                sizing_mode='stretch_both', min_width=350, min_height=350)
    p2.title.text_font_size = "14pt"
    p2.xaxis.axis_label_text_font_size = "12pt"
    p2.yaxis.axis_label_text_font_size = "12pt"
    p2.xaxis.major_label_text_font_size = "11pt"
    p2.yaxis.major_label_text_font_size = "11pt"
    p2.legend.label_text_font_size = "11pt"
    p2.line(calcPoundage, data1['calcTotalArrowMass'], line_width=4, color="#1976D2", legend_label="Setup 1")
    p2.line(calcPoundage, data2['calcTotalArrowMass'], line_width=4, color="#FF9800", legend_label="Setup 2")
    
    # Add points with exact values
    p2.circle([calcPoundage[idx1]], [data1['calcTotalArrowMass'][idx1]], 
             size=16, color="#1976D2")
    p2.circle([calcPoundage[idx2]], [data2['calcTotalArrowMass'][idx2]], 
             size=16, color="#FF9800")
    
    # Add labels
    label1 = Label(x=calcPoundage[idx1], y=data1['calcTotalArrowMass'][idx1], 
                   text=f"{data1['calcTotalArrowMass'][idx1]:.0f}gr",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcTotalArrowMass'][idx2], 
                   text=f"{data2['calcTotalArrowMass'][idx2]:.0f}gr",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p2.add_layout(label1)
    p2.add_layout(label2)
    p2.legend.location = "top_right"
    plots['totalMass'] = json.dumps(json_item(p2))
    
    # FOC Plot with bands
    p3 = figure(title="Poundage vs FOC [%]",
                x_axis_label="Poundage", y_axis_label="FOC [%]",
                sizing_mode='stretch_both', min_width=300, min_height=250, y_range=[0, 35])
    p3.title.text_font_size = "14pt"
    p3.xaxis.axis_label_text_font_size = "12pt"
    p3.yaxis.axis_label_text_font_size = "12pt"
    p3.xaxis.major_label_text_font_size = "11pt"
    p3.yaxis.major_label_text_font_size = "11pt"
    p3.legend.label_text_font_size = "11pt"
    
    # Add FOC bands
    source = ColumnDataSource({
        'base': calcPoundage,
        'bottom': np.zeros_like(calcPoundage),
        'normal': np.full_like(calcPoundage, 12),
        'high': np.full_like(calcPoundage, 19),
        'extreme': np.full_like(calcPoundage, 30),
        'top': np.full_like(calcPoundage, 50)
    })
    
    p3.add_layout(Band(base='base', lower='bottom', upper='normal', source=source, 
                      fill_alpha=0.4, level='underlay', fill_color="red"))
    p3.add_layout(Band(base='base', lower='normal', upper='high', source=source, 
                      fill_alpha=0.4, level='underlay', fill_color="#90CAF9"))
    p3.add_layout(Band(base='base', lower='high', upper='extreme', source=source, 
                      fill_alpha=0.4, level='underlay', fill_color="#42A5F5"))
    p3.add_layout(Band(base='base', lower='extreme', upper='top', source=source, 
                      fill_alpha=0.4, level='underlay', fill_color="#1E88E5"))
    
    p3.line(calcPoundage, data1['calcFOC'], line_width=4, color="#1976D2", legend_label="Setup 1")
    p3.line(calcPoundage, data2['calcFOC'], line_width=4, color="#FF9800", legend_label="Setup 2")
    
    # Add points
    p3.circle([calcPoundage[idx1]], [data1['calcFOC'][idx1]], 
             size=16, color="#1976D2")
    p3.circle([calcPoundage[idx2]], [data2['calcFOC'][idx2]], 
             size=16, color="#FF9800")
    
    # Add labels
    label1 = Label(x=calcPoundage[idx1], y=data1['calcFOC'][idx1], 
                   text=f"{data1['calcFOC'][idx1]:.1f}%",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcFOC'][idx2], 
                   text=f"{data2['calcFOC'][idx2]:.1f}%",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p3.add_layout(label1)
    p3.add_layout(label2)
    p3.legend.location = "top_right"
    plots['foc'] = json.dumps(json_item(p3))
    
    # Kinetic Energy Plot with bands
    p4 = figure(title="Poundage vs Kinetic Energy [J]",
                x_axis_label="Poundage", y_axis_label="KE [J]",
                sizing_mode='stretch_both', min_width=300, min_height=250, y_range=[0, 150])
    p4.title.text_font_size = "14pt"
    p4.xaxis.axis_label_text_font_size = "12pt"
    p4.yaxis.axis_label_text_font_size = "12pt"
    p4.xaxis.major_label_text_font_size = "11pt"
    p4.yaxis.major_label_text_font_size = "11pt"
    p4.legend.label_text_font_size = "11pt"
    
    # Add KE bands for game types
    ke_source = ColumnDataSource({
        'base': calcPoundage,
        'small': np.zeros_like(calcPoundage),
        'medium': np.full_like(calcPoundage, 35),
        'high': np.full_like(calcPoundage, 55),
        'extreme': np.full_like(calcPoundage, 88),
        'top': np.full_like(calcPoundage, 300)
    })
    
    p4.add_layout(Band(base='base', lower='small', upper='medium', source=ke_source, 
                      fill_alpha=0.4, level='underlay', fill_color="red"))
    p4.add_layout(Band(base='base', lower='medium', upper='high', source=ke_source, 
                      fill_alpha=0.4, level='underlay', fill_color="#90CAF9"))
    p4.add_layout(Band(base='base', lower='high', upper='extreme', source=ke_source, 
                      fill_alpha=0.4, level='underlay', fill_color="#42A5F5"))
    p4.add_layout(Band(base='base', lower='extreme', upper='top', source=ke_source, 
                      fill_alpha=0.4, level='underlay', fill_color="#1E88E5"))
    
    # Setup 1 KE lines at different distances
    p4.line(calcPoundage, data1['calcKE'], line_width=4, color="#1976D2", legend_label="Setup 1 (0yd)")
    p4.line(calcPoundage, data1['calcKE20yd'], line_width=3, color="#1976D2", line_dash="dashed", alpha=0.7)
    p4.line(calcPoundage, data1['calcKE40yd'], line_width=3, color="#1976D2", line_dash="dashdot", alpha=0.7)
    p4.line(calcPoundage, data1['calcKE60yd'], line_width=3, color="#1976D2", line_dash="dotted", alpha=0.7)
    
    # Setup 2 KE lines at different distances
    p4.line(calcPoundage, data2['calcKE'], line_width=4, color="#FF9800", legend_label="Setup 2 (0yd)")
    p4.line(calcPoundage, data2['calcKE20yd'], line_width=3, color="#FF9800", line_dash="dashed", alpha=0.7)
    p4.line(calcPoundage, data2['calcKE40yd'], line_width=3, color="#FF9800", line_dash="dashdot", alpha=0.7)
    p4.line(calcPoundage, data2['calcKE60yd'], line_width=3, color="#FF9800", line_dash="dotted", alpha=0.7)
    
    # Add points for 0yd
    p4.circle([calcPoundage[idx1]], [data1['calcKE'][idx1]], 
             size=16, color="#1976D2")
    p4.circle([calcPoundage[idx2]], [data2['calcKE'][idx2]], 
             size=16, color="#FF9800")
    
    # Add points for 60yd
    p4.circle([calcPoundage[idx1]], [data1['calcKE60yd'][idx1]], 
             size=12, color="#1976D2", alpha=0.7)
    p4.circle([calcPoundage[idx2]], [data2['calcKE60yd'][idx2]], 
             size=12, color="#FF9800", alpha=0.7)
    
    # Add labels
    label1 = Label(x=calcPoundage[idx1], y=data1['calcKE'][idx1], 
                   text=f"{data1['calcKE'][idx1]:.0f}J",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcKE'][idx2], 
                   text=f"{data2['calcKE'][idx2]:.0f}J",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p4.add_layout(label1)
    p4.add_layout(label2)
    p4.legend.location = "top_right"
    plots['ke'] = json.dumps(json_item(p4))
    
    # FPS Plot with distance lines
    p5 = figure(title="Poundage vs FPS",
                x_axis_label="Poundage", y_axis_label="FPS",
                sizing_mode='stretch_both', min_width=350, min_height=350)
    p5.title.text_font_size = "14pt"
    p5.xaxis.axis_label_text_font_size = "12pt"
    p5.yaxis.axis_label_text_font_size = "12pt"
    p5.xaxis.major_label_text_font_size = "11pt"
    p5.yaxis.major_label_text_font_size = "11pt"
    p5.legend.label_text_font_size = "11pt"
    
    # Setup 1 lines
    p5.line(calcPoundage, data1['calcFPS'], line_width=4, color="#1976D2", legend_label="Setup 1 (0yd)")
    p5.line(calcPoundage, data1['calcFPS20yd'], line_width=3, color="#1976D2", line_dash="dashed", alpha=0.7)
    p5.line(calcPoundage, data1['calcFPS40yd'], line_width=3, color="#1976D2", line_dash="dashdot", alpha=0.7)
    p5.line(calcPoundage, data1['calcFPS60yd'], line_width=3, color="#1976D2", line_dash="dotted", alpha=0.7)
    
    # Setup 2 lines
    p5.line(calcPoundage, data2['calcFPS'], line_width=4, color="#FF9800", legend_label="Setup 2 (0yd)")
    p5.line(calcPoundage, data2['calcFPS20yd'], line_width=3, color="#FF9800", line_dash="dashed", alpha=0.7)
    p5.line(calcPoundage, data2['calcFPS40yd'], line_width=3, color="#FF9800", line_dash="dashdot", alpha=0.7)
    p5.line(calcPoundage, data2['calcFPS60yd'], line_width=3, color="#FF9800", line_dash="dotted", alpha=0.7)
    
    # Current points
    p5.circle([calcPoundage[idx1]], [data1['calcFPS'][idx1]], 
             size=16, color="#1976D2")
    p5.circle([calcPoundage[idx2]], [data2['calcFPS'][idx2]], 
             size=16, color="#FF9800")
    
    # Add labels
    label1 = Label(x=calcPoundage[idx1], y=data1['calcFPS'][idx1], 
                   text=f"{data1['calcFPS'][idx1]:.0f}fps",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcFPS'][idx2], 
                   text=f"{data2['calcFPS'][idx2]:.0f}fps",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p5.add_layout(label1)
    p5.add_layout(label2)
    
    p5.legend.location = "top_right"
    plots['fps'] = json.dumps(json_item(p5))
    
    # Momentum Plot
    p6 = figure(title="Poundage vs Momentum [kg·m/s]",
                x_axis_label="Poundage", y_axis_label="Momentum",
                sizing_mode='stretch_both', min_width=350, min_height=350)
    p6.title.text_font_size = "14pt"
    p6.xaxis.axis_label_text_font_size = "12pt"
    p6.yaxis.axis_label_text_font_size = "12pt"
    p6.xaxis.major_label_text_font_size = "11pt"
    p6.yaxis.major_label_text_font_size = "11pt"
    p6.legend.label_text_font_size = "11pt"
    # Setup 1 momentum lines at different distances
    p6.line(calcPoundage, data1['calcMomentum'], line_width=4, color="#1976D2", legend_label="Setup 1 (0yd)")
    p6.line(calcPoundage, data1['calcMomentum20yd'], line_width=3, color="#1976D2", line_dash="dashed", alpha=0.7)
    p6.line(calcPoundage, data1['calcMomentum40yd'], line_width=3, color="#1976D2", line_dash="dashdot", alpha=0.7)
    p6.line(calcPoundage, data1['calcMomentum60yd'], line_width=3, color="#1976D2", line_dash="dotted", alpha=0.7)
    
    # Setup 2 momentum lines at different distances
    p6.line(calcPoundage, data2['calcMomentum'], line_width=4, color="#FF9800", legend_label="Setup 2 (0yd)")
    p6.line(calcPoundage, data2['calcMomentum20yd'], line_width=3, color="#FF9800", line_dash="dashed", alpha=0.7)
    p6.line(calcPoundage, data2['calcMomentum40yd'], line_width=3, color="#FF9800", line_dash="dashdot", alpha=0.7)
    p6.line(calcPoundage, data2['calcMomentum60yd'], line_width=3, color="#FF9800", line_dash="dotted", alpha=0.7)
    
    # Add points for 0yd
    p6.circle([calcPoundage[idx1]], [data1['calcMomentum'][idx1]], 
             size=16, color="#1976D2")
    p6.circle([calcPoundage[idx2]], [data2['calcMomentum'][idx2]], 
             size=16, color="#FF9800")
    
    # Add points for 60yd
    p6.circle([calcPoundage[idx1]], [data1['calcMomentum60yd'][idx1]], 
             size=12, color="#1976D2", alpha=0.7)
    p6.circle([calcPoundage[idx2]], [data2['calcMomentum60yd'][idx2]], 
             size=12, color="#FF9800", alpha=0.7)
    
    # Add labels
    label1 = Label(x=calcPoundage[idx1], y=data1['calcMomentum'][idx1], 
                   text=f"{data1['calcMomentum'][idx1]:.2f}",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcMomentum'][idx2], 
                   text=f"{data2['calcMomentum'][idx2]:.2f}",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p6.add_layout(label1)
    p6.add_layout(label2)
    p6.legend.location = "top_right"
    plots['momentum'] = json.dumps(json_item(p6))
    
    # Time of Flight Plot
    p7 = figure(title="Poundage vs Time of Flight [s]",
                x_axis_label="Poundage", y_axis_label="Time [s]",
                sizing_mode='stretch_both', min_width=350, min_height=350)
    p7.title.text_font_size = "14pt"
    p7.xaxis.axis_label_text_font_size = "12pt"
    p7.yaxis.axis_label_text_font_size = "12pt"
    p7.xaxis.major_label_text_font_size = "11pt"
    p7.yaxis.major_label_text_font_size = "11pt"
    p7.legend.label_text_font_size = "11pt"
    
    # Setup 1 TOF lines at different distances
    p7.line(calcPoundage, data1['calcTOF20yd'], line_width=4, color="#1976D2", legend_label="Setup 1 (20yd)")
    p7.line(calcPoundage, data1['calcTOF40yd'], line_width=3, color="#1976D2", line_dash="dashed", alpha=0.8, legend_label="Setup 1 (40yd)")
    p7.line(calcPoundage, data1['calcTOF60yd'], line_width=3, color="#1976D2", line_dash="dotted", alpha=0.7, legend_label="Setup 1 (60yd)")
    
    # Setup 2 TOF lines at different distances
    p7.line(calcPoundage, data2['calcTOF20yd'], line_width=4, color="#FF9800", legend_label="Setup 2 (20yd)")
    p7.line(calcPoundage, data2['calcTOF40yd'], line_width=3, color="#FF9800", line_dash="dashed", alpha=0.8, legend_label="Setup 2 (40yd)")
    p7.line(calcPoundage, data2['calcTOF60yd'], line_width=3, color="#FF9800", line_dash="dotted", alpha=0.7, legend_label="Setup 2 (60yd)")
    
    # Add points for 60yd
    p7.circle([calcPoundage[idx1]], [data1['calcTOF60yd'][idx1]], 
             size=16, color="#1976D2")
    p7.circle([calcPoundage[idx2]], [data2['calcTOF60yd'][idx2]], 
             size=16, color="#FF9800")
    
    # Add labels for 60yd
    label1 = Label(x=calcPoundage[idx1], y=data1['calcTOF60yd'][idx1], 
                   text=f"{data1['calcTOF60yd'][idx1]:.3f}s",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#1976D2")
    label2 = Label(x=calcPoundage[idx2], y=data2['calcTOF60yd'][idx2], 
                   text=f"{data2['calcTOF60yd'][idx2]:.3f}s",
                   x_offset=8, y_offset=8, text_font_size="12pt", text_color="#FF9800")
    p7.add_layout(label1)
    p7.add_layout(label2)
    p7.legend.location = "top_right"
    plots['tof'] = json.dumps(json_item(p7))
    
    return plots

def create_plots(calcPoundage, calcOpPointWeight, calcTotalArrowMass, calcFOC, 
                calcKE, calcFPS, calcMomentum, calcFPS20yd, calcFPS40yd, calcFPS60yd):
    """Create Bokeh plots for all calculated values"""
    plots = {}
    
    # Optimal Point Weight Plot
    p1 = figure(title="Poundage vs Optimal Point Weight [grains]",
                x_axis_label="Poundage", y_axis_label="Point Weight [gr]",
                width=400, height=300)
    p1.line(calcPoundage, calcOpPointWeight, line_width=3, color="blue")
    plots['pointWeight'] = json.dumps(json_item(p1))
    
    # Total Arrow Mass Plot
    p2 = figure(title="Poundage vs Total Arrow Mass [grains]",
                x_axis_label="Poundage", y_axis_label="Total Mass [gr]",
                width=400, height=300)
    p2.line(calcPoundage, calcTotalArrowMass, line_width=3, color="green")
    plots['totalMass'] = json.dumps(json_item(p2))
    
    # FOC Plot with bands
    p3 = figure(title="Poundage vs FOC [%]",
                x_axis_label="Poundage", y_axis_label="FOC [%]",
                width=400, height=300, y_range=[0, 35])
    
    # Add FOC bands
    source = ColumnDataSource({
        'base': calcPoundage,
        'bottom': np.zeros_like(calcPoundage),
        'normal': np.full_like(calcPoundage, 12),
        'high': np.full_like(calcPoundage, 19),
        'extreme': np.full_like(calcPoundage, 30),
        'top': np.full_like(calcPoundage, 50)
    })
    
    p3.add_layout(Band(base='base', lower='bottom', upper='normal', source=source, 
                      fill_alpha=0.5, level='underlay', fill_color="red"))
    p3.add_layout(Band(base='base', lower='normal', upper='high', source=source, 
                      fill_alpha=0.5, level='underlay', fill_color="#90CAF9"))
    p3.add_layout(Band(base='base', lower='high', upper='extreme', source=source, 
                      fill_alpha=0.5, level='underlay', fill_color="#42A5F5"))
    p3.add_layout(Band(base='base', lower='extreme', upper='top', source=source, 
                      fill_alpha=0.5, level='underlay', fill_color="#1E88E5"))
    
    p3.line(calcPoundage, calcFOC, line_width=3, color="black")
    plots['foc'] = json.dumps(json_item(p3))
    
    # Kinetic Energy Plot with bands
    p4 = figure(title="Poundage vs Kinetic Energy [J]",
                x_axis_label="Poundage", y_axis_label="KE [J]",
                width=400, height=300, y_range=[0, 150])
    
    # Add KE bands for game types
    ke_source = ColumnDataSource({
        'base': calcPoundage,
        'small': np.zeros_like(calcPoundage),
        'medium': np.full_like(calcPoundage, 35),
        'high': np.full_like(calcPoundage, 55),
        'extreme': np.full_like(calcPoundage, 88),
        'top': np.full_like(calcPoundage, 300)
    })
    
    p4.add_layout(Band(base='base', lower='small', upper='medium', source=ke_source, 
                      fill_alpha=0.5, level='underlay', fill_color="red"))
    p4.add_layout(Band(base='base', lower='medium', upper='high', source=ke_source, 
                      fill_alpha=0.5, level='underlay', fill_color="#90CAF9"))
    p4.add_layout(Band(base='base', lower='high', upper='extreme', source=ke_source, 
                      fill_alpha=0.5, level='underlay', fill_color="#42A5F5"))
    p4.add_layout(Band(base='base', lower='extreme', upper='top', source=ke_source, 
                      fill_alpha=0.5, level='underlay', fill_color="#1E88E5"))
    
    p4.line(calcPoundage, calcKE, line_width=3, color="black", legend_label="0 yd")
    plots['ke'] = json.dumps(json_item(p4))
    
    # FPS Plot
    p5 = figure(title="Poundage vs FPS",
                x_axis_label="Poundage", y_axis_label="FPS",
                width=400, height=300)
    p5.line(calcPoundage, calcFPS, line_width=3, color="blue", legend_label="0 yd")
    p5.line(calcPoundage, calcFPS20yd, line_width=3, color="green", line_dash="dashed", legend_label="20 yd")
    p5.line(calcPoundage, calcFPS40yd, line_width=3, color="orange", line_dash="dashdot", legend_label="40 yd")
    p5.line(calcPoundage, calcFPS60yd, line_width=3, color="red", line_dash="dotted", legend_label="60 yd")
    plots['fps'] = json.dumps(json_item(p5))
    
    # Momentum Plot
    p6 = figure(title="Poundage vs Momentum [kg·m/s]",
                x_axis_label="Poundage", y_axis_label="Momentum",
                width=400, height=300)
    p6.line(calcPoundage, calcMomentum, line_width=3, color="purple")
    plots['momentum'] = json.dumps(json_item(p6))
    
    return plots

if __name__ == '__main__':
    # For development
    app.run(debug=False, host='0.0.0.0', port=5001)
    
# For production deployment
# Use a WSGI server like gunicorn:
# gunicorn -w 4 -b 0.0.0.0:5000 app:app