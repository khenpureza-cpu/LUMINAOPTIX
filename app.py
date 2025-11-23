from flask import Flask, request, jsonify, render_template
from flask_cors import CORS # type: ignore
import math
import re

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_problem():
    try:
        data = request.get_json()
        problem_text = data.get('problem', '').lower()
        
        # Extract parameters using regex
        params = {}
        
        # Refractive indices
        n1_match = re.search(r'n1\s*[=:]\s*(\d+\.?\d*)', problem_text)
        n2_match = re.search(r'n2\s*[=:]\s*(\d+\.?\d*)', problem_text)
        if n1_match: params['n1'] = float(n1_match.group(1))
        if n2_match: params['n2'] = float(n2_match.group(1))
        
        # Angles
        theta1_match = re.search(r'(?:theta1|θ1|angle)\s*[=:]\s*(\d+\.?\d*)', problem_text)
        if theta1_match: params['theta1'] = float(theta1_match.group(1))
        
        # Lens parameters
        f_match = re.search(r'f\s*[=:]\s*(\d+\.?\d*)', problem_text)
        do_match = re.search(r'do\s*[=:]\s*(\d+\.?\d*)', problem_text)
        di_match = re.search(r'di\s*[=:]\s*(\d+\.?\d*)', problem_text)
        if f_match: params['f'] = float(f_match.group(1))
        if do_match: params['do'] = float(do_match.group(1))
        if di_match: params['di'] = float(di_match.group(1))
        
        results = []
        
        # Determine problem type and solve
        if any(word in problem_text for word in ['refract', 'snell', 'angle', 'n1', 'n2']):
            # Refraction problem
            n1 = params.get('n1', 1.0)
            n2 = params.get('n2', 1.5)
            theta1 = params.get('theta1', 30.0)
            
            result = calculate_snell(n1, n2, theta1)
            results.append(result)
            
        elif any(word in problem_text for word in ['lens', 'focal', 'object', 'image']):
            # Lens problem
            f = params.get('f')
            do = params.get('do')
            di = params.get('di')
            
            result = calculate_lens(f, do, di)
            results.append(result)
        else:
            results.append({
                'Detected': 'Optical Problem',
                'Given': 'Could not identify specific problem type',
                'Formula': 'Please include keywords like: refraction, lens, focal, angle',
                'Steps': 'Try rephrasing with specific optical terms',
                'Answer': 'Unable to analyze - please provide more context'
            })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify([{
            'error': str(e),
            'Detected': 'Error',
            'Given': 'Problem parsing failed',
            'Formula': 'N/A',
            'Steps': f'Error: {str(e)}',
            'Answer': 'Calculation failed'
        }])

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        mode = data.get('mode')
        
        if mode == 'snell':
            n1 = data.get('n1', 1.0)
            n2 = data.get('n2', 1.5)
            theta1 = data.get('theta1', 0.0)
            
            result = calculate_snell(n1, n2, theta1)
            return jsonify({
                'result': result['Answer'],
                'calculation_steps': result['Steps'].split('\n'),
                'exact_value': float(re.search(r'[\d.]+', result['Answer']).group()) if 'θ₂' in result['Answer'] else result['Answer'],
                'animation_data': result.get('animationData', {})
            })
            
        elif mode == 'lens':
            f = data.get('f')
            do = data.get('do')
            di = data.get('di')
            
            result = calculate_lens(f, do, di)
            exact_value_match = re.search(r'[\d.-]+', result['Answer'])
            exact_value = float(exact_value_match.group()) if exact_value_match else None
            
            return jsonify({
                'result': result['Answer'],
                'calculation_steps': result['Steps'].split('\n'),
                'exact_value': exact_value,
                'animation_data': result.get('animationData', {})
            })
            
        else:
            return jsonify({'error': 'Invalid mode'})
            
    except Exception as e:
        return jsonify({'error': str(e)})

def calculate_snell(n1, n2, theta1):
    """Calculate refraction using Snell's Law"""
    theta1_rad = math.radians(theta1)
    sin_theta1 = math.sin(theta1_rad)
    sin_theta2 = (n1 / n2) * sin_theta1
    
    steps = [
        f"Step 1: sinθ₂ = (n₁ / n₂) × sinθ₁ = ({n1} / {n2}) × sin({theta1}°)",
        f"Step 2: sinθ₂ = {(n1/n2):.6f} × {sin_theta1:.6f} = {sin_theta2:.8f}"
    ]
    
    if abs(sin_theta2) > 1:
        # Total Internal Reflection
        critical_angle = math.degrees(math.asin(n2/n1))
        steps.extend([
            f"Step 3: |sinθ₂| = {abs(sin_theta2):.6f} > 1 → Total Internal Reflection",
            f"Step 4: Critical Angle = arcsin(n₂/n₁) = arcsin({n2}/{n1}) = {critical_angle:.6f}°"
        ])
        
        return {
            'Detected': 'Refraction Problem - Total Internal Reflection',
            'Given': f'n₁ = {n1}, n₂ = {n2}, θ₁ = {theta1}°',
            'Formula': 'n₁ × sinθ₁ = n₂ × sinθ₂',
            'Steps': '\n'.join(steps),
            'Answer': f'Total Internal Reflection occurs\nCritical Angle: {critical_angle:.6f}°',
            'animationData': {
                'type': 'tir',
                'n1': n1,
                'n2': n2,
                'theta1': theta1,
                'critical_angle': critical_angle
            }
        }
    else:
        # Normal refraction
        theta2 = math.degrees(math.asin(sin_theta2))
        steps.append(f"Step 3: θ₂ = arcsin({sin_theta2:.6f}) = {theta2:.6f}°")
        
        return {
            'Detected': 'Refraction Problem',
            'Given': f'n₁ = {n1}, n₂ = {n2}, θ₁ = {theta1}°',
            'Formula': "Snell's Law: n₁ × sinθ₁ = n₂ × sinθ₂",
            'Steps': '\n'.join(steps),
            'Answer': f'θ₂ = {theta2:.6f}°',
            'animationData': {
                'type': 'refraction',
                'n1': n1,
                'n2': n2,
                'theta1': theta1,
                'theta2': theta2
            }
        }

def calculate_lens(f, do, di):
    """Calculate lens parameters using thin lens equation"""
    steps = []
    result_value = None
    find = ""
    animation_data = {}
    
    # Count provided values
    provided = sum(1 for val in [f, do, di] if val is not None)
    
    if provided != 2:
        return {
            'Detected': 'Lens Problem',
            'Given': f'f = {f or "?"}, do = {do or "?"}, di = {di or "?"}',
            'Formula': '1/f = 1/do + 1/di',
            'Steps': 'Error: Please provide exactly two of the three values',
            'Answer': 'Insufficient data provided'
        }
    
    if f is not None and do is not None and di is None:
        find = "di"
        di_calc = 1 / ((1/f) - (1/do))
        steps.extend([
            f"Step 1: 1/di = 1/f - 1/do = 1/{f} - 1/{do}",
            f"Step 2: 1/di = {(1/f):.6f} - {(1/do):.6f} = {(1/f - 1/do):.6f}",
            f"Step 3: di = 1 / {(1/f - 1/do):.6f} = {di_calc:.6f} cm"
        ])
        animation_data = {'type': 'lens', 'f': f, 'do': do, 'di': di_calc}
        result_value = di_calc
        
    elif f is not None and di is not None and do is None:
        find = "do"
        do_calc = 1 / ((1/f) - (1/di))
        steps.extend([
            f"Step 1: 1/do = 1/f - 1/di = 1/{f} - 1/{di}",
            f"Step 2: 1/do = {(1/f):.6f} - {(1/di):.6f} = {(1/f - 1/di):.6f}",
            f"Step 3: do = 1 / {(1/f - 1/di):.6f} = {do_calc:.6f} cm"
        ])
        animation_data = {'type': 'lens', 'f': f, 'do': do_calc, 'di': di}
        result_value = do_calc
        
    elif do is not None and di is not None and f is None:
        find = "f"
        f_calc = 1 / ((1/do) + (1/di))
        steps.extend([
            f"Step 1: 1/f = 1/do + 1/di = 1/{do} + 1/{di}",
            f"Step 2: 1/f = {(1/do):.6f} + {(1/di):.6f} = {(1/do + 1/di):.6f}",
            f"Step 3: f = 1 / {(1/do + 1/di):.6f} = {f_calc:.6f} cm"
        ])
        animation_data = {'type': 'lens', 'f': f_calc, 'do': do, 'di': di}
        result_value = f_calc
    
    return {
        'Detected': 'Lens Problem',
        'Given': f'f = {f or "?"}, do = {do or "?"}, di = {di or "?"}',
        'Formula': 'Thin Lens Equation: 1/f = 1/do + 1/di',
        'Steps': '\n'.join(steps),
        'Answer': f'{find} = {result_value:.6f} cm',
        'animationData': animation_data
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)