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
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
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

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    water_intake = db.Column(db.Integer, default=0)  # in glasses
    meals = db.Column(db.Text, nullable=False)  # JSON string of meals
    total_calories = db.Column(db.Integer, default=0)
    nutritional_analysis = db.Column(db.Text)  # AI suggestions and analysis
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

def get_mood_chart_data(user_id):
    """Get mood data for chart visualization"""
    interactions = WellnessInteraction.query.filter_by(user_id=user_id).order_by(WellnessInteraction.timestamp.desc()).limit(30).all()
    
    mood_counts = {}
    mood_timeline = []
    
    for interaction in reversed(interactions):  # Reverse to show chronological order
        mood_category = categorize_mood(interaction.mood_input)
        
        # Count mood categories
        mood_counts[mood_category] = mood_counts.get(mood_category, 0) + 1
        
        # Timeline data (last 7 days)
        mood_timeline.append({
            'date': interaction.timestamp.strftime('%m/%d'),
            'mood': mood_category,
            'timestamp': interaction.timestamp
        })
    
    return mood_counts, mood_timeline

def analyze_food_intake(meals_text, water_glasses):
    """Analyze food intake and provide nutritional guidance"""
    import json
    import re
    
    # Simple calorie estimation based on common foods
    food_calories = {
        'rice': 130, 'bread': 80, 'pasta': 220, 'quinoa': 220,
        'chicken': 165, 'beef': 250, 'fish': 130, 'egg': 70, 'tofu': 70,
        'apple': 80, 'banana': 105, 'orange': 60, 'berries': 40,
        'salad': 20, 'vegetables': 25, 'potato': 160, 'sweet potato': 180,
        'milk': 150, 'yogurt': 100, 'cheese': 110, 'nuts': 180,
        'pizza': 285, 'burger': 540, 'fries': 365, 'soda': 140,
        'chocolate': 235, 'cake': 240, 'cookie': 50
    }
    
    meals_lower = meals_text.lower()
    total_calories = 0
    detected_foods = []
    
    # Detect foods and estimate calories
    for food, calories in food_calories.items():
        if food in meals_lower:
            detected_foods.append(food)
            # Estimate portion (simple logic)
            count = meals_lower.count(food)
            multiplier = 1.5 if any(word in meals_lower for word in ['large', 'big', 'extra', 'double']) else 1
            total_calories += int(calories * count * multiplier)
    
    # Water intake analysis
    recommended_water = 8  # glasses
    water_status = "excellent" if water_glasses >= recommended_water else "needs improvement"
    
    # Calorie analysis
    recommended_calories = 2000  # Basic recommendation
    calorie_status = "high" if total_calories > recommended_calories else "good" if total_calories > 1200 else "low"
    
    return {
        'total_calories': total_calories,
        'detected_foods': detected_foods,
        'water_status': water_status,
        'calorie_status': calorie_status,
        'recommended_water': recommended_water
    }

def get_nutritional_advice(analysis_data, meals_text):
    """Generate personalized nutritional advice based on food analysis"""
    total_calories = analysis_data['total_calories']
    water_status = analysis_data['water_status']
    calorie_status = analysis_data['calorie_status']
    detected_foods = analysis_data['detected_foods']
    meals_lower = meals_text.lower()
    
    advice = []
    
    # Calorie-based advice
    if calorie_status == "high":
        advice.append("🔥 Your calorie intake is higher than recommended today! Here are some ways to balance it out:")
        advice.append("• Try a 30-minute brisk walk (burns ~150 calories)")
        advice.append("• Do some light exercise like yoga or stretching")
        advice.append("• Consider smaller portions for your next meals")
        advice.append("• Avoid sugary drinks and snacks for the rest of the day")
        
        if any(food in meals_lower for food in ['pizza', 'burger', 'fries', 'cake', 'chocolate']):
            advice.append("• I noticed some high-calorie foods - try balancing with vegetables and lean proteins tomorrow")
    
    elif calorie_status == "low":
        advice.append("💙 Your calorie intake seems quite low today. Your body needs fuel to function well:")
        advice.append("• Add healthy snacks like nuts, fruits, or yogurt")
        advice.append("• Include more protein-rich foods like eggs, chicken, or beans")
        advice.append("• Don't forget healthy fats from avocados, olive oil, or nuts")
    
    else:
        advice.append("✨ Great job! Your calorie intake looks well-balanced today.")
    
    # Water intake advice
    if water_status == "needs improvement":
        advice.append("💧 You could use more water today! Try to reach 8 glasses:")
        advice.append("• Keep a water bottle nearby as a reminder")
        advice.append("• Add lemon or cucumber for flavor")
        advice.append("• Set hourly reminders to take a few sips")
    else:
        advice.append("🌊 Excellent hydration! You're doing great with your water intake.")
    
    # Food quality advice
    healthy_foods = ['salad', 'vegetables', 'fish', 'quinoa', 'berries', 'apple', 'yogurt']
    unhealthy_foods = ['pizza', 'burger', 'fries', 'soda', 'cake', 'chocolate']
    
    healthy_count = sum(1 for food in healthy_foods if food in detected_foods)
    unhealthy_count = sum(1 for food in unhealthy_foods if food in detected_foods)
    
    if healthy_count > unhealthy_count:
        advice.append("🥗 I love seeing all those nutritious choices! Keep up the excellent eating habits.")
    elif unhealthy_count > 0:
        advice.append("🌱 Consider adding more fruits and vegetables to tomorrow's meals.")
        advice.append("• Swap processed snacks for fresh fruits")
        advice.append("• Try grilled instead of fried foods")
        advice.append("• Add a colorful salad to your main meals")
    
    return "\n".join(advice)

def log_food_intake(user_id, water_intake, meals_text):
    """Log user's food and water intake to database"""
    try:
        # Check if entry already exists for today
        today = datetime.utcnow().date()
        existing_log = FoodLog.query.filter_by(user_id=user_id, date=today).first()
        
        # Analyze the food intake
        analysis = analyze_food_intake(meals_text, water_intake)
        nutritional_advice = get_nutritional_advice(analysis, meals_text)
        
        if existing_log:
            # Update existing entry
            existing_log.water_intake = water_intake
            existing_log.meals = meals_text
            existing_log.total_calories = analysis['total_calories']
            existing_log.nutritional_analysis = nutritional_advice
            existing_log.timestamp = datetime.utcnow()
        else:
            # Create new entry
            food_log = FoodLog(
                user_id=user_id,
                date=today,
                water_intake=water_intake,
                meals=meals_text,
                total_calories=analysis['total_calories'],
                nutritional_analysis=nutritional_advice
            )
            db.session.add(food_log)
        
        db.session.commit()
        return analysis, nutritional_advice
        
    except Exception as e:
        print(f"Error logging food intake: {e}")
        db.session.rollback()
        return None, "Sorry, there was an error processing your food log."

def categorize_mood(mood_input):
    """Categorize mood input into chart-friendly categories"""
    mood_lower = mood_input.lower()
    
    if any(word in mood_lower for word in ['grateful', 'thankful', 'blessed', 'good', 'positive', 'happy', 'great', 'wonderful', 'amazing', 'excited', 'joyful']):
        return 'Positive'
    elif any(word in mood_lower for word in ['stressed', 'overwhelmed', 'pressure', 'busy', 'hectic', 'chaotic', 'rushed']):
        return 'Stressed'
    elif any(word in mood_lower for word in ['anxious', 'worried', 'nervous', 'scared', 'afraid', 'panic', 'fear', 'concerned']):
        return 'Anxious'
    elif any(word in mood_lower for word in ['sad', 'down', 'depressed', 'blue', 'low', 'upset', 'hurt', 'disappointed', 'lonely']):
        return 'Sad'
    elif any(word in mood_lower for word in ['tired', 'exhausted', 'drained', 'low energy', 'fatigue', 'weary', 'sleepy']):
        return 'Tired'
    elif any(word in mood_lower for word in ['frustrated', 'angry', 'mad', 'annoyed', 'irritated', 'furious', 'rage']):
        return 'Frustrated'
    else:
        return 'Neutral'

def get_wellness_suggestion(mood_input):
    """Get contextual wellness suggestion based on mood input"""
    mood_lower = mood_input.lower()
    
    # Positive/Grateful responses
    if any(word in mood_lower for word in ['grateful', 'thankful', 'blessed', 'good', 'positive', 'happy', 'great', 'wonderful', 'amazing', 'excited', 'joyful']):
        positive_suggestions = [
            "🌟 You're radiating such beautiful energy right now! That positive mindset of yours is truly inspiring. Take a moment to savor this wonderful feeling and let it fuel the rest of your day.",
            "💫 I love seeing you so grateful and upbeat! Your appreciation for life is contagious. Why not write down three things you're thankful for to keep this amazing momentum going?",
            "✨ You're absolutely glowing with positivity! This is your superpower shining through. Use this incredible energy to tackle something you've been putting off - you've got this!",
            "🌈 Your joyful spirit is so uplifting! When you feel this good, it's like sunshine for everyone around you. Maybe share this positive energy by doing something kind for yourself or others today.",
            "🎉 Wow, you're on fire today! This kind of gratitude and joy is what makes life beautiful. Ride this wave of happiness - perhaps treat yourself to something special you've been wanting.",
            "💖 Your grateful heart is truly beautiful! The way you appreciate life shows such wisdom and strength. Keep nurturing this wonderful perspective - it's one of your greatest gifts."
        ]
        return random.choice(positive_suggestions)
    
    # Stressed/Overwhelmed responses
    elif any(word in mood_lower for word in ['stressed', 'overwhelmed', 'pressure', 'busy', 'hectic', 'chaotic', 'rushed']):
        stress_suggestions = [
            "💙 I can feel the weight you're carrying right now, and I want you to know you're incredibly strong. You've overcome challenges before, and you have that same resilience within you now. Try the 4-7-8 breathing technique: in for 4, hold for 7, out for 8. You've got this.",
            "🫂 Hey, it's okay to feel overwhelmed sometimes - it just shows how much you care. You're human, and that's beautiful. Break those big tasks into tiny, manageable pieces. Every small step is a victory worth celebrating.",
            "🌿 I see you pushing through so much right now, and that takes incredible courage. Your strength amazes me. Take 5 minutes to step outside or put on some calming music - you've earned this break.",
            "💪 The fact that you're feeling stressed shows you're someone who cares deeply, and that's actually a superpower. Try progressive muscle relaxation: tense and release each muscle group. Your body deserves this care.",
            "🤗 You're juggling so much, and I'm genuinely impressed by your dedication. But remember, even superheroes need rest. Write down your top 3 priorities and tackle them one by one. You're more capable than you know.",
            "🌱 I want to remind you of something important: you don't have to be perfect, and you don't have to do everything at once. Take that walk outside - fresh air and your beautiful spirit will reset everything."
        ]
        return random.choice(stress_suggestions)
    
    # Anxious/Worried responses
    elif any(word in mood_lower for word in ['anxious', 'worried', 'nervous', 'scared', 'afraid', 'panic', 'fear', 'concerned']):
        anxiety_suggestions = [
            "🤲 I see you, and I want you to know that what you're feeling is valid and you're going to be okay. Your heart might be racing, but you're safe right now. Try the 5-4-3-2-1 grounding technique: name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste. You're braver than you believe.",
            "💗 That worried feeling in your chest? It shows just how deeply you care about life and the people around you. That's actually beautiful, even when it's scary. Place your hand on your heart - feel it beating strong and steady. You're alive, you're here, and you're going to be okay.",
            "🌸 I know those anxious thoughts feel so real and urgent right now, but they're just thoughts - not predictions, not facts. You've survived 100% of your difficult days so far, and that's an incredible track record. Let's focus on this very moment together.",
            "🌊 Your anxiety comes from a place of love - you care so much about doing right by yourself and others. That caring heart of yours is truly special. Try the 'worry window' technique: give those concerns 10 minutes later, then let them go for now.",
            "🦋 I know your mind is spinning with 'what-ifs' and worst-case scenarios. Your brain is trying to protect you, but right now, in this very moment, you're safe. Write those worries down - getting them out of your head can reduce their power over you.",
            "🌟 Sweet soul, anxiety might be visiting you right now, but it's temporary - like weather that passes through. Your strength, your resilience, your beautiful heart? Those are permanent. Be as kind to yourself as you would be to your dearest friend."
        ]
        return random.choice(anxiety_suggestions)
    
    # Sad/Down responses
    elif any(word in mood_lower for word in ['sad', 'down', 'depressed', 'blue', 'low', 'upset', 'hurt', 'disappointed', 'lonely']):
        sad_suggestions = [
            "🤗 Oh sweetheart, I can feel the sadness in your heart right now, and I want you to know it's completely okay to feel this way. Your emotions are valid, and you don't have to put on a brave face. Sometimes the most healing thing is to just let yourself feel, wrapped in self-compassion like a warm blanket.",
            "💙 The fact that you can feel sadness this deeply shows what a beautiful, caring soul you have. Your heart is tender because it's capable of profound love and connection. Would it help to do something small and comforting? Maybe make yourself some tea or take a warm shower - you deserve that gentleness.",
            "🌙 I see the weight you're carrying today, and I'm so proud of you for just being here, just breathing, just continuing. Sometimes the bravest thing in the world is simply getting through the day when it feels hard, and look - you're doing exactly that. Consider reaching out to someone who loves you - you don't have to carry this alone.",
            "🌷 Your sadness isn't something to fix or rush through - it's often your heart's way of processing something important. These feelings deserve space and respect. When you're ready, maybe try some gentle movement, like stretching or a slow walk. Your body is holding you so beautifully through this.",
            "🕊️ I know everything feels heavy right now, but I want to remind you: this sadness is a visitor, not a permanent resident. You've felt joy before, and you will again. For now, what's one tiny act of kindness you can offer yourself? You deserve all the tenderness in the world.",
            "💖 Your tender heart is one of your most beautiful qualities, even when it aches like this. The depth of your sadness reflects the depth of your capacity to love. Remember, this feeling will shift and change - nothing lasts forever, including pain."
        ]
        return random.choice(sad_suggestions)
    
    # Tired/Low Energy responses
    elif any(word in mood_lower for word in ['tired', 'exhausted', 'drained', 'low energy', 'fatigue', 'weary', 'sleepy']):
        tired_suggestions = [
            "🌙 Sweet soul, your body is sending you such an important message right now - it's asking for the rest and care you so deserve. There's absolutely no shame in feeling tired; it just means you've been showing up for life with everything you've got. Try a 10-20 minute rest - even lying down with your eyes closed can be like a gift to yourself.",
            "💤 I can feel that deep exhaustion you're carrying, and it tells me you've been giving your absolute all to the world. What a generous heart you have! But now it's time to be just as generous with yourself. Make sure you're drinking water and nourishing your body - you deserve that care.",
            "🤲 Oh honey, you're running on empty, aren't you? I can sense how drained you feel, and I want you to know it's okay to step back and recharge. Your energy is precious - you've been spending it so generously. Try some gentle stretching or just breathe deeply. Your body will thank you.",
            "🌿 Your tiredness isn't weakness - it's proof of your strength and how much you care about everything you do. Your body has been your faithful companion through it all, and now it's asking for some TLC. What would help you recharge - rest, fresh air, or maybe just acknowledging how hard you've been working?",
            "☁️ I see you pushing through even when your energy feels depleted, and that shows incredible resilience. But you know what? It's time to honor what your body needs. Sometimes the most productive thing is to rest and restore - you've more than earned it.",
            "🕊️ You've been carrying so much, haven't you? The world is lucky to have someone who gives as much as you do, but now it's time to prioritize the most important person in your life - you. What energizes your soul versus what drains it? Focus on the good stuff today."
        ]
        return random.choice(tired_suggestions)
    
    # Frustrated/Angry responses
    elif any(word in mood_lower for word in ['frustrated', 'angry', 'mad', 'annoyed', 'irritated', 'furious', 'rage']):
        anger_suggestions = [
            "🔥 I can absolutely feel that frustration burning inside you right now, and every bit of it is completely valid. When things don't go the way we pour our heart into making them go, it's maddening! This fire inside you shows how much you care, and that's actually beautiful. Take some deep breaths and ask yourself what you need right now.",
            "💪 That frustration bubbling up? It's coming from a place of passion and high standards - that's the mark of someone who really gives a damn about doing things right. I admire that about you, even when it feels overwhelming. Try channeling that energy into movement - a quick walk or even some vigorous cleaning can help.",
            "⚡ Oh, I can feel that energy building up in you - that 'why isn't this working?!' feeling that makes you want to scream. And you know what? Sometimes we need to let that energy out! Try the 'STOP' technique: Stop, Take a breath, Observe, then Proceed with that brilliant mind of yours.",
            "🌪️ When it feels like the whole universe is working against you, that frustration is so real and so exhausting. You're definitely not alone in feeling this way. It's absolutely okay to feel angry - punch a pillow, scream in your car, write it all out. Your feelings deserve expression.",
            "🔥 That fire of frustration? It's your inner warrior wanting things to be better, wanting to create positive change. Even when it's uncomfortable, it shows you haven't given up - and that's incredibly powerful. What's one small thing you DO have control over right now? Start there.",
            "💥 I hear the exhaustion behind that frustration - some days it really does feel like everything is an uphill battle, doesn't it? Your feelings are so valid. Once you've honored this anger, let's think about what you need to feel better. You're stronger than whatever is testing you right now."
        ]
        return random.choice(anger_suggestions)
    
    # Default response for unclear or mixed emotions
    else:
        general_suggestions = [
            "🌸 Thank you for trusting me with your feelings - that takes real courage. You're taking such good care of yourself by checking in like this. Take a moment to breathe deeply and just be present with yourself. You're doing beautifully.",
            "💫 Whatever you're experiencing right now is completely valid and worthy of attention. Your emotions matter because YOU matter. Consider doing something small and loving for yourself today - you deserve that kindness.",
            "🎨 Emotions can be so beautifully complex, just like you are. I love that you're paying attention to your inner world - that's actually a superpower. Try checking in with yourself throughout the day and notice how your feelings shift and change like art.",
            "🤲 Sometimes the most profound thing we can do is simply witness our feelings without rushing to fix or change them. You're being so wise by just acknowledging what's here. That kind of self-awareness is truly special.",
            "✨ Your emotional intelligence is absolutely glowing right now! The fact that you're tuning into your feelings shows such strength and wisdom. What do you think your heart is trying to tell you that you need right now?",
            "🌿 I'm so impressed by how you're navigating your emotional landscape with such care and attention. Remember to be incredibly patient with yourself - you're learning and growing every single day. What would feel most supportive for your beautiful soul right now?"
        ]
        return random.choice(general_suggestions)

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
    mood_counts, mood_timeline = get_mood_chart_data(current_user.id)
    
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
            <a href="{{ url_for('food_tracker') }}" class="btn">🍎 Track Food & Nutrition</a>
        </div>
        
        <div class="card">
            <h2>📊 Your Mood Insights</h2>
            {% if mood_counts %}
            <div style="width: 100%; height: 320px; margin: 25px 0; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                <canvas id="moodChart"></canvas>
            </div>
            <div style="width: 100%; height: 320px; margin: 25px 0; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                <canvas id="moodTrendChart"></canvas>
            </div>
            {% else %}
            <p style="text-align: center; color: rgba(255,255,255,0.8); margin: 40px 0;">
                📈 Your mood chart will appear here after you complete a few check-ins!
            </p>
            {% endif %}
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Mood distribution chart (Doughnut)
        {% if mood_counts %}
        const moodCtx = document.getElementById('moodChart').getContext('2d');
        new Chart(moodCtx, {
            type: 'doughnut',
            data: {
                labels: {{ mood_counts.keys() | list | tojson }},
                datasets: [{
                    data: {{ mood_counts.values() | list | tojson }},
                    backgroundColor: [
                        '#A8E6CF', // Positive - Soft Mint Green
                        '#FFB3BA', // Stressed - Soft Pink  
                        '#FFD1A9', // Anxious - Soft Peach
                        '#B8C6E8', // Sad - Soft Lavender Blue
                        '#E4C1F9', // Tired - Soft Purple
                        '#FFC9A9', // Frustrated - Soft Orange
                        '#D4C4E0'  // Neutral - Soft Gray Purple
                    ],
                    borderWidth: 3,
                    borderColor: 'rgba(255,255,255,0.4)',
                    hoverBorderWidth: 4,
                    hoverBorderColor: 'rgba(255,255,255,0.8)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Your Mood Distribution',
                        color: 'white',
                        font: { size: 16 }
                    },
                    legend: {
                        labels: { 
                            color: 'white',
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 20,
                            font: { size: 13 }
                        },
                        position: 'bottom'
                    }
                }
            }
        });
        
        // Mood timeline chart (Line)
        const trendCtx = document.getElementById('moodTrendChart').getContext('2d');
        const moodColors = {
            'Positive': '#A8E6CF',
            'Stressed': '#FFB3BA', 
            'Anxious': '#FFD1A9',
            'Sad': '#B8C6E8',
            'Tired': '#E4C1F9',
            'Frustrated': '#FFC9A9',
            'Neutral': '#D4C4E0'
        };
        
        const timelineData = {{ mood_timeline | tojson }};
        const dates = timelineData.map(item => item.date);
        const moods = timelineData.map(item => item.mood);
        
        // Convert mood categories to numeric values for line chart
        const moodValues = moods.map(mood => {
            const moodScale = {'Positive': 5, 'Neutral': 3, 'Tired': 2, 'Anxious': 2, 'Stressed': 1, 'Frustrated': 1, 'Sad': 1};
            return moodScale[mood] || 3;
        });
        
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Mood Trend',
                    data: moodValues,
                    borderColor: '#A8E6CF',
                    backgroundColor: 'rgba(168, 230, 207, 0.2)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: moods.map(mood => moodColors[mood]),
                    pointBorderColor: 'white',
                    pointBorderWidth: 3,
                    pointRadius: 7,
                    pointHoverRadius: 10,
                    pointHoverBorderWidth: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Your Mood Timeline',
                        color: 'white',
                        font: { size: 16 }
                    },
                    legend: {
                        labels: { 
                            color: 'white',
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 15,
                            font: { size: 12 }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 5,
                        ticks: {
                            color: 'white',
                            callback: function(value) {
                                const labels = {1: 'Low', 2: 'Tired', 3: 'Neutral', 4: 'Good', 5: 'Great'};
                                return labels[value] || '';
                            }
                        },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    x: {
                        ticks: { color: 'white' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    }
                }
            }
        });
        {% endif %}
    </script>
</body>
</html>''', total_checkins=total_checkins, interactions=interactions, mood_counts=mood_counts, mood_timeline=mood_timeline)

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
        <a href="{{ url_for('dashboard') }}" class="back-link">← Back to Dashboard</a>
        
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
        <a href="{{ url_for('dashboard') }}" class="back-link">← Back to Dashboard</a>
        
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

@app.route('/food-tracker', methods=['GET', 'POST'])
@login_required
def food_tracker():
    """Food and nutrition tracker"""
    if request.method == 'POST':
        water_intake = int(request.form.get('water_intake', 0))
        meals_text = request.form.get('meals', '').strip()
        
        if meals_text:
            analysis, advice = log_food_intake(current_user.id, water_intake, meals_text)
            if analysis:
                flash('Your food intake has been logged and analyzed!', 'success')
                return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nutrition Analysis - Health Whisperer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: white;
        }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px 0; }
        .card {
            background: rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 30px;
            margin-bottom: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .nutrition-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 15px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.2); }
        .stat-number { font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }
        .btn {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; padding: 12px 25px;
            border: none; border-radius: 25px; text-decoration: none; display: inline-block;
            margin: 10px; font-weight: 600; text-align: center; transition: all 0.3s ease;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .advice-section { background: rgba(255, 255, 255, 0.1); padding: 25px; border-radius: 15px; margin-top: 20px; white-space: pre-line; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍎 Your Nutrition Analysis</h1>
            <p>Here's what I found about your food intake today</p>
        </div>
        <div class="nutrition-stats">
            <div class="stat-card"><div class="stat-number">{{ analysis.total_calories }}</div><div>Total Calories</div></div>
            <div class="stat-card"><div class="stat-number">{{ water_intake }}</div><div>Glasses of Water</div></div>
            <div class="stat-card"><div class="stat-number">{{ analysis.detected_foods|length }}</div><div>Foods Detected</div></div>
        </div>
        <div class="card">
            <h2>🥗 Detected Foods</h2>
            <p>{{ ', '.join(analysis.detected_foods) if analysis.detected_foods else 'No specific foods detected' }}</p>
        </div>
        <div class="card">
            <h2>💡 Personalized Nutrition Advice</h2>
            <div class="advice-section">{{ advice }}</div>
        </div>
        <div style="text-align: center; margin-top: 30px;">
            <a href="{{ url_for('dashboard') }}" class="btn">🏠 Back to Dashboard</a>
            <a href="{{ url_for('food_tracker') }}" class="btn">📝 Log More Food</a>
        </div>
    </div>
</body>
</html>''', analysis=analysis, advice=advice, water_intake=water_intake)
            else:
                flash('Sorry, there was an error processing your food log.', 'error')
        else:
            flash('Please enter your meals for the day.', 'error')
    
    # Get today's existing log if any
    today = datetime.utcnow().date()
    existing_log = FoodLog.query.filter_by(user_id=current_user.id, date=today).first()
    
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Food & Nutrition Tracker - Health Whisperer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: white;
        }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px 0; }
        .card {
            background: rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 30px;
            margin-bottom: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .form-group { margin-bottom: 25px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 600; font-size: 1.1em; }
        .form-group input, .form-group textarea {
            width: 100%; padding: 15px; border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px; background: rgba(255, 255, 255, 0.1); color: white;
            font-size: 16px; backdrop-filter: blur(5px);
        }
        .form-group input::placeholder, .form-group textarea::placeholder { color: rgba(255, 255, 255, 0.7); }
        .form-group textarea { min-height: 120px; resize: vertical; }
        .btn {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; padding: 15px 30px;
            border: none; border-radius: 25px; font-size: 16px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; width: 100%; margin-top: 10px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .examples { background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 10px; margin-top: 10px; font-size: 0.9em; }
        .flash-messages { margin-bottom: 20px; }
        .flash-message { padding: 15px; border-radius: 10px; margin-bottom: 10px; }
        .flash-success { background: rgba(76, 175, 80, 0.3); border: 1px solid rgba(76, 175, 80, 0.5); }
        .flash-error { background: rgba(244, 67, 54, 0.3); border: 1px solid rgba(244, 67, 54, 0.5); }
        .existing-log { background: rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 15px; margin-bottom: 20px; }
        .back-link { display: inline-block; margin-bottom: 20px; color: rgba(255, 255, 255, 0.8); text-decoration: none; }
        .back-link:hover { color: white; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('dashboard') }}" class="back-link">← Back to Dashboard</a>
        <div class="header">
            <h1>🍎 Food & Nutrition Tracker</h1>
            <p>Track your daily food intake and get personalized nutrition advice</p>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        {% if existing_log %}
        <div class="existing-log">
            <h3>📊 Today's Current Log</h3>
            <p><strong>Water:</strong> {{ existing_log.water_intake }} glasses</p>
            <p><strong>Calories:</strong> {{ existing_log.total_calories }}</p>
            <p><strong>Last updated:</strong> {{ existing_log.timestamp.strftime('%I:%M %p') }}</p>
        </div>
        {% endif %}
        <div class="card">
            <form method="POST">
                <div class="form-group">
                    <label for="water_intake">💧 How many glasses of water have you had today?</label>
                    <input type="number" id="water_intake" name="water_intake" 
                           value="{{ existing_log.water_intake if existing_log else 0 }}" 
                           min="0" max="20" required>
                    <div class="examples">
                        <strong>Tip:</strong> Aim for 8 glasses (64 oz) per day for optimal hydration
                    </div>
                </div>
                <div class="form-group">
                    <label for="meals">🍽️ What did you eat today? (Include all meals and snacks)</label>
                    <textarea id="meals" name="meals" 
                              placeholder="Example: Breakfast - 2 eggs, toast, banana. Lunch - chicken salad, apple. Dinner - grilled fish, vegetables, rice. Snacks - nuts, yogurt" 
                              required>{{ existing_log.meals if existing_log else '' }}</textarea>
                    <div class="examples">
                        <strong>Include:</strong> Breakfast, lunch, dinner, snacks, drinks, portion sizes (small/medium/large), cooking methods (fried, grilled, baked)
                    </div>
                </div>
                <button type="submit" class="btn">🔍 Analyze My Nutrition</button>
            </form>
        </div>
        <div class="card">
            <h3>🎯 What You'll Get</h3>
            <ul style="margin-left: 20px; line-height: 1.8;">
                <li>✅ Total calorie count for the day</li>
                <li>💡 Personalized nutrition advice</li>
                <li>🏃‍♂️ Exercise suggestions if calories are high</li>
                <li>🥗 Food quality assessment</li>
                <li>💧 Hydration feedback</li>
                <li>📋 Recommendations for better eating</li>
            </ul>
        </div>
    </div>
</body>
</html>''', existing_log=existing_log)

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