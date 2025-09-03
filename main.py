#!/usr/bin/env python3
import os
import random
from datetime import datetime
import csv
from flask import Flask, render_template_string, request, redirect, url_for, flash, session

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "health-whisperer-secret-key-2025")

# CSV file for logging interactions
CSV_FILE = 'wellness_interactions.csv'

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

def log_interaction(mood_input, suggestion):
    """Log user interaction to CSV file"""
    try:
        file_exists = os.path.isfile(CSV_FILE)
        session_id = session.get('session_id', f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Timestamp', 'Session_ID', 'Mood_Input', 'AI_Suggestion'])
            writer.writerow([datetime.now().isoformat(), session_id, mood_input, suggestion])
    except Exception as e:
        print(f"Error logging interaction: {e}")

def get_wellness_suggestion(mood_input):
    """Get wellness suggestion - using fallback for now"""
    return random.choice(WELLNESS_SUGGESTIONS)

@app.route('/')
def home():
    """Home page"""
    if 'session_id' not in session:
        session['session_id'] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Whisperer - Your AI Wellness Coach</title>
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
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            padding: 2rem;
        }
        h1 { font-size: 3rem; margin-bottom: 1rem; }
        .subtitle { font-size: 1.3rem; margin-bottom: 2rem; opacity: 0.9; }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin: 2rem 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
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
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        .feature {
            background: rgba(255, 255, 255, 0.1);
            padding: 1.5rem;
            border-radius: 15px;
            text-align: left;
        }
        .emoji { font-size: 2rem; margin-bottom: 0.5rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 Health Whisperer</h1>
        <p class="subtitle">Your AI-Powered Wellness Coach</p>
        
        <div class="card">
            <h2>Welcome to Your Wellness Journey!</h2>
            <p>Share how you're feeling and get personalized suggestions to improve your wellbeing.</p>
            <a href="{{ url_for('check_in') }}" class="btn">💭 Start Your Check-In</a>
            <a href="{{ url_for('history') }}" class="btn">📊 View Your History</a>
        </div>
        
        <div class="features">
            <div class="feature">
                <div class="emoji">💚</div>
                <h3>Personalized Suggestions</h3>
                <p>Get tailored wellness advice based on your current mood and feelings.</p>
            </div>
            <div class="feature">
                <div class="emoji">📈</div>
                <h3>Track Progress</h3>
                <p>Monitor your wellness journey over time with our history feature.</p>
            </div>
            <div class="feature">
                <div class="emoji">🎯</div>
                <h3>Quick Actions</h3>
                <p>Receive actionable suggestions you can complete in just 5-10 minutes.</p>
            </div>
        </div>
    </div>
</body>
</html>''')

@app.route('/check-in', methods=['GET', 'POST'])
def check_in():
    """Mood check-in page"""
    if request.method == 'POST':
        mood_input = request.form.get('mood_input', '').strip()
        if mood_input:
            suggestion = get_wellness_suggestion(mood_input)
            log_interaction(mood_input, suggestion)
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
                <a href="{{ url_for('home') }}" class="btn">🏠 Home</a>
            </div>
        </div>
    </div>
</body>
</html>''', mood=mood, suggestion=suggestion)

@app.route('/history')
def history():
    """View interaction history"""
    interactions = []
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                interactions = list(reader)
                interactions.reverse()  # Most recent first
        except Exception as e:
            flash(f'Error reading history: {e}', 'error')
    
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
        <a href="{{ url_for('home') }}" class="back-link">← Back to Home</a>
        
        <div class="card">
            <h1>📊 Your Wellness Journey</h1>
            
            {% if interactions %}
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{{ interactions|length }}</div>
                        <div>Total Check-ins</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{{ interactions[0]['Timestamp'][:10] if interactions else 'N/A' }}</div>
                        <div>Last Check-in</div>
                    </div>
                </div>
                
                {% for interaction in interactions %}
                <div class="interaction">
                    <div class="date">📅 {{ interaction['Timestamp'][:19] }}</div>
                    <div class="mood">
                        <strong>💭 How you felt:</strong><br>
                        "{{ interaction['Mood_Input'] }}"
                    </div>
                    <div class="suggestion">
                        <strong>✨ Suggestion given:</strong><br>
                        {{ interaction['AI_Suggestion'] }}
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