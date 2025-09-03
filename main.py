#!/usr/bin/env python3
import os
import random
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "health-whisperer-secret-key-2025")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    interactions = db.relationship('WellnessInteraction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Wellness interaction model
class WellnessInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood_input = db.Column(db.Text, nullable=False)
    ai_suggestion = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Wellness suggestions (fallback when AI isn't available)
WELLNESS_SUGGESTIONS = [
    "Take five deep breaths and stretch for two minutes to release tension.",
    "Step outside for a short walk and notice three beautiful things around you.",
    "Try the 4-7-8 breathing technique: breathe in for 4, hold for 7, exhale for 8.",
    "Take a moment to write down three things you're grateful for today.",
    "Put on your favorite song and dance or move your body for 3 minutes.",
    "Drink a glass of water slowly and mindfully, focusing on the sensation.",
    "Close your eyes and imagine a peaceful place for 2 minutes.",
    "Call or text someone you care about just to say hello.",
    "Do some gentle neck and shoulder rolls to release physical tension.",
    "Write down one thing you accomplished today, no matter how small."
]

def log_interaction(mood_input, suggestion, user_id):
    """Log user interaction to database"""
    try:
        interaction = WellnessInteraction(
            user_id=user_id,
            mood_input=mood_input,
            ai_suggestion=suggestion
        )
        db.session.add(interaction)
        db.session.commit()
    except Exception as e:
        print(f"Error logging interaction: {e}")
        db.session.rollback()

def get_wellness_suggestion(mood_input):
    """Get wellness suggestion - using fallback for now"""
    return random.choice(WELLNESS_SUGGESTIONS)

@app.route('/')
def landing():
    """Landing page with signup/login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Whisperer - Your AI-Powered Wellness Coach</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
            max-width: 600px;
        }
        h1 { 
            font-size: 4rem; 
            margin-bottom: 0.5rem;
            font-weight: 300;
            letter-spacing: -2px;
        }
        .subtitle { 
            font-size: 1.5rem; 
            margin-bottom: 3rem; 
            opacity: 0.9;
            font-weight: 300;
        }
        .auth-buttons {
            margin: 2rem 0;
        }
        .btn {
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
            padding: 18px 40px;
            border-radius: 50px;
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 15px;
            min-width: 120px;
            backdrop-filter: blur(10px);
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-3px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            border-color: rgba(255, 255, 255, 0.5);
        }
        .btn-primary {
            background: rgba(46, 139, 87, 0.8);
            border-color: rgba(46, 139, 87, 0.9);
        }
        .btn-primary:hover {
            background: rgba(46, 139, 87, 1);
            border-color: rgba(46, 139, 87, 1);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 Health Whisperer</h1>
        <p class="subtitle">Your AI-Powered Wellness Coach</p>
        
        <div class="auth-buttons">
            <a href="{{ url_for('signup') }}" class="btn btn-primary">Sign Up</a>
            <a href="{{ url_for('login') }}" class="btn">Login</a>
        </div>
    </div>
</body>
</html>''')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not email or not password:
            flash('All fields are required.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Welcome to Health Whisperer!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        h1 { text-align: center; margin-bottom: 2rem; }
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        input {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            box-sizing: border-box;
        }
        .btn {
            background: #2E8B57;
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            font-size: 1.1rem;
            cursor: pointer;
            width: 100%;
            transition: background 0.3s ease;
        }
        .btn:hover { background: #236B47; }
        .back-link {
            color: white;
            text-decoration: none;
            margin-bottom: 2rem;
            display: inline-block;
        }
        .back-link:hover { text-decoration: underline; }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .alert-error {
            background: rgba(220, 53, 69, 0.2);
            border: 1px solid rgba(220, 53, 69, 0.3);
        }
        .login-link {
            text-align: center;
            margin-top: 1rem;
        }
        .login-link a {
            color: white;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('landing') }}" class="back-link">← Back</a>
        
        <div class="card">
            <h1>🌿 Join Health Whisperer</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required minlength="6">
                </div>
                
                <button type="submit" class="btn">Create Account</button>
            </form>
            
            <div class="login-link">
                Already have an account? <a href="{{ url_for('login') }}">Login here</a>
            </div>
        </div>
    </div>
</body>
</html>''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
        else:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        h1 { text-align: center; margin-bottom: 2rem; }
        .form-group { margin-bottom: 1.5rem; }
        label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
        input {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            box-sizing: border-box;
        }
        .btn {
            background: #2E8B57;
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            font-size: 1.1rem;
            cursor: pointer;
            width: 100%;
            transition: background 0.3s ease;
        }
        .btn:hover { background: #236B47; }
        .back-link {
            color: white;
            text-decoration: none;
            margin-bottom: 2rem;
            display: inline-block;
        }
        .back-link:hover { text-decoration: underline; }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .alert-error {
            background: rgba(220, 53, 69, 0.2);
            border: 1px solid rgba(220, 53, 69, 0.3);
        }
        .alert-success {
            background: rgba(40, 167, 69, 0.2);
            border: 1px solid rgba(40, 167, 69, 0.3);
        }
        .signup-link {
            text-align: center;
            margin-top: 1rem;
        }
        .signup-link a {
            color: white;
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('landing') }}" class="back-link">← Back</a>
        
        <div class="card">
            <h1>🌿 Welcome Back</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                
                <button type="submit" class="btn">Login</button>
            </form>
            
            <div class="signup-link">
                Don't have an account? <a href="{{ url_for('signup') }}">Sign up here</a>
            </div>
        </div>
    </div>
</body>
</html>''')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    interactions = WellnessInteraction.query.filter_by(user_id=current_user.id).order_by(WellnessInteraction.timestamp.desc()).limit(5).all()
    total_checkins = WellnessInteraction.query.filter_by(user_id=current_user.id).count()
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        .logout-btn {
            background: rgba(220, 53, 69, 0.2);
            color: white;
            border: 1px solid rgba(220, 53, 69, 0.3);
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .logout-btn:hover {
            background: rgba(220, 53, 69, 0.3);
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: center;
        }
        .stat-number { font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        .recent-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .timestamp { font-size: 0.9rem; opacity: 0.8; }
        h1, h2 { margin-top: 0; }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .alert-success {
            background: rgba(40, 167, 69, 0.2);
            border: 1px solid rgba(40, 167, 69, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌿 Welcome, {{ current_user.username }}!</h1>
            <a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{{ total_checkins }}</div>
                <div>Total Check-ins</div>
            </div>
            <div class="stat">
                <div class="stat-number">{{ interactions|length }}</div>
                <div>Recent Sessions</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Ready for your wellness journey?</h2>
            <p>Share how you're feeling and get personalized suggestions to improve your wellbeing.</p>
            <a href="{{ url_for('check_in') }}" class="btn">💭 Start Check-In</a>
            <a href="{{ url_for('history') }}" class="btn">📊 View Full History</a>
        </div>
        
        {% if interactions %}
        <div class="card">
            <h2>Recent Check-ins</h2>
            {% for interaction in interactions %}
            <div class="recent-item">
                <div class="timestamp">{{ interaction.timestamp.strftime('%B %d, %Y at %I:%M %p') }}</div>
                <strong>You felt:</strong> "{{ interaction.mood_input[:100] }}{% if interaction.mood_input|length > 100 %}...{% endif %}"
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>''', total_checkins=total_checkins, interactions=interactions)

@app.route('/check-in', methods=['GET', 'POST'])
@login_required
def check_in():
    """Mood check-in page"""
    if request.method == 'POST':
        mood_input = request.form.get('mood_input', '').strip()
        if mood_input:
            suggestion = get_wellness_suggestion(mood_input)
            log_interaction(mood_input, suggestion, current_user.id)
            session['last_mood'] = mood_input
            session['last_suggestion'] = suggestion
            flash('Thank you for sharing! Here\'s your personalized suggestion:', 'success')
            return redirect(url_for('suggestion'))
        else:
            flash('Please tell us how you\'re feeling.', 'error')
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Check In - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        h1 { text-align: center; margin-bottom: 2rem; }
        .form-group { margin-bottom: 2rem; }
        label { font-size: 1.2rem; margin-bottom: 1rem; display: block; }
        textarea, select {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            box-sizing: border-box;
        }
        textarea {
            min-height: 120px;
            resize: vertical;
        }
        .btn {
            background: #2E8B57;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
        }
        .btn:hover {
            background: #236B47;
            transform: translateY(-2px);
        }
        .back-link {
            color: white;
            text-decoration: none;
            margin-bottom: 2rem;
            display: inline-block;
        }
        .back-link:hover { text-decoration: underline; }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .alert-error {
            background: rgba(220, 53, 69, 0.2);
            border: 1px solid rgba(220, 53, 69, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('home') }}" class="back-link">← Back to Home</a>
        
        <div class="card">
            <h1>💭 How are you feeling today?</h1>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                <div class="form-group">
                    <label for="mood_select">Quick mood selector:</label>
                    <select id="mood_select" onchange="updateTextarea()">
                        <option value="">Choose a mood...</option>
                        <option value="I'm feeling stressed and overwhelmed">Stressed & Overwhelmed</option>
                        <option value="I'm feeling anxious and worried">Anxious & Worried</option>
                        <option value="I'm feeling sad and down">Sad & Down</option>
                        <option value="I'm feeling tired and unmotivated">Tired & Unmotivated</option>
                        <option value="I'm feeling frustrated and angry">Frustrated & Angry</option>
                        <option value="I'm feeling lonely and isolated">Lonely & Isolated</option>
                        <option value="I'm feeling good but want to maintain it">Good - Want to Maintain</option>
                        <option value="I'm feeling grateful and positive">Grateful & Positive</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="mood_input">Or describe your feelings in your own words:</label>
                    <textarea id="mood_input" name="mood_input" 
                              placeholder="Tell me how you're feeling right now... What's on your mind? What emotions are you experiencing?"></textarea>
                </div>
                
                <button type="submit" class="btn">Get My Wellness Suggestion ✨</button>
            </form>
        </div>
    </div>
    
    <script>
        function updateTextarea() {
            const select = document.getElementById('mood_select');
            const textarea = document.getElementById('mood_input');
            if (select.value) {
                textarea.value = select.value;
            }
        }
    </script>
</body>
</html>''')

@app.route('/suggestion')
@login_required
def suggestion():
    """Display wellness suggestion"""
    mood = session.get('last_mood', '')
    suggestion = session.get('last_suggestion', '')
    
    if not mood or not suggestion:
        flash('Please complete a check-in first.', 'error')
        return redirect(url_for('check_in'))
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Wellness Suggestion - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        h1 { text-align: center; margin-bottom: 2rem; }
        .mood-display {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            font-style: italic;
        }
        .suggestion {
            background: linear-gradient(135deg, #2E8B57 0%, #20B2AA 100%);
            padding: 2rem;
            border-radius: 15px;
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 2rem;
        }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }
        .back-link {
            color: white;
            text-decoration: none;
            margin-bottom: 2rem;
            display: inline-block;
        }
        .back-link:hover { text-decoration: underline; }
        .actions {
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('home') }}" class="back-link">← Back to Home</a>
        
        <div class="card">
            <h1>✨ Your Personalized Wellness Suggestion</h1>
            
            <div class="mood-display">
                <strong>💭 You shared:</strong><br>
                "{{ mood }}"
            </div>
            
            <div class="suggestion">
                <strong>🌟 Here's what I suggest:</strong><br><br>
                {{ suggestion }}
            </div>
            
            <div class="actions">
                <a href="{{ url_for('check_in') }}" class="btn">💭 New Check-In</a>
                <a href="{{ url_for('history') }}" class="btn">📊 View History</a>
                <a href="{{ url_for('dashboard') }}" class="btn">🏠 Dashboard</a>
            </div>
        </div>
    </div>
</body>
</html>''', mood=mood, suggestion=suggestion)

@app.route('/history')
@login_required
def history():
    """View interaction history"""
    interactions = WellnessInteraction.query.filter_by(user_id=current_user.id).order_by(WellnessInteraction.timestamp.desc()).all()
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your History - Health Whisperer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        h1 { text-align: center; margin-bottom: 2rem; }
        .back-link {
            color: white;
            text-decoration: none;
            margin-bottom: 2rem;
            display: inline-block;
        }
        .back-link:hover { text-decoration: underline; }
        .interaction {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .date { font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem; }
        .mood { 
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            font-style: italic;
        }
        .suggestion {
            background: linear-gradient(135deg, #2E8B57 0%, #20B2AA 100%);
            padding: 1rem;
            border-radius: 10px;
        }
        .empty {
            text-align: center;
            font-size: 1.2rem;
            opacity: 0.8;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 15px;
            text-align: center;
        }
        .stat-number { font-size: 2rem; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('dashboard') }}" class="back-link">← Back to Dashboard</a>
        
        <div class="card">
            <h1>📊 Your Wellness Journey</h1>
            
            {% if interactions %}
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{{ interactions|length }}</div>
                        <div>Total Check-ins</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{{ interactions[0].timestamp.strftime('%b %d') if interactions else 'N/A' }}</div>
                        <div>Last Check-in</div>
                    </div>
                </div>
                
                {% for interaction in interactions %}
                <div class="interaction">
                    <div class="date">📅 {{ interaction.timestamp.strftime('%B %d, %Y at %I:%M %p') }}</div>
                    <div class="mood">
                        <strong>💭 How you felt:</strong><br>
                        "{{ interaction.mood_input }}"
                    </div>
                    <div class="suggestion">
                        <strong>✨ Suggestion given:</strong><br>
                        {{ interaction.ai_suggestion }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty">
                    <p>🌱 No check-ins yet!</p>
                    <p>Start your wellness journey by doing your first check-in.</p>
                    <br>
                    <a href="{{ url_for('check_in') }}" style="color: white; text-decoration: none; padding: 15px 30px; background: rgba(255,255,255,0.2); border-radius: 25px;">💭 Start Your First Check-In</a>
                </div>
            {% endif %}
        </div>
    </div>
</body>
</html>''', interactions=interactions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)