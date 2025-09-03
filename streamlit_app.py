import streamlit as st
import json
import os
import logging
from datetime import datetime
import pandas as pd
import csv
from google import genai
from google.genai import types
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Configure page
st.set_page_config(
    page_title="Health Whisperer - Your AI Wellness Coach",
    page_icon="💚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Gemini client
@st.cache_resource
def get_gemini_client():
    """Initialize Gemini client with API key"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY environment variable is required. Please set it in the Secrets tab.")
        st.stop()
    return genai.Client(api_key=api_key)

# Wellness suggestion functions
def get_wellness_suggestion(mood_input, client):
    """Generate AI-powered wellness suggestions using Gemini"""
    try:
        prompt = f"""You are a compassionate AI wellness coach. Based on the user's mood or feelings, 
        provide a short, actionable wellness suggestion (1-3 sentences). Focus on practical, immediate actions 
        they can take to feel better. Keep suggestions simple, positive, and achievable within 5-10 minutes.
        
        Examples of good suggestions:
        - "Take five deep breaths and stretch for two minutes"
        - "Step outside for a short walk and notice three beautiful things around you"
        - "Try the 4-7-8 breathing technique: breathe in for 4, hold for 7, exhale for 8"
        
        User feeling: {mood_input}
        
        Provide only the wellness suggestion, no additional formatting."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text or "Take a moment to breathe deeply and be kind to yourself."
        
    except Exception as e:
        st.error(f"Error generating AI suggestion: {e}")
        return "Take three deep breaths and remember that this feeling is temporary. You are stronger than you know."

# Data logging functions
CSV_FILE = 'wellness_interactions.csv'

def log_interaction(mood_input, ai_suggestion, session_id=None):
    """Log user interaction to CSV file"""
    try:
        file_exists = os.path.isfile(CSV_FILE)
        
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            if not file_exists:
                writer.writerow(['Timestamp', 'Session_ID', 'Mood_Input', 'AI_Suggestion'])
            
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                session_id or st.session_state.get('session_id', 'anonymous'),
                mood_input,
                ai_suggestion
            ])
                
    except Exception as e:
        st.error(f"Error logging interaction: {e}")

def get_user_history(session_id=None):
    """Retrieve user history from CSV file"""
    try:
        if not os.path.isfile(CSV_FILE):
            return pd.DataFrame()
        
        df = pd.read_csv(CSV_FILE)
        
        if session_id:
            df = df[df['Session_ID'] == session_id]
        
        return df
        
    except Exception as e:
        st.error(f"Error retrieving history: {e}")
        return pd.DataFrame()

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if 'suggestion_given' not in st.session_state:
        st.session_state.suggestion_given = False
    
    if 'current_mood' not in st.session_state:
        st.session_state.current_mood = ""
    
    if 'current_suggestion' not in st.session_state:
        st.session_state.current_suggestion = ""

# Custom CSS
def load_custom_css():
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #2E8B57;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .subtitle {
        text-align: center;
        color: #708090;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    .mood-card {
        background: #F0F8F8;
        padding: 2rem;
        border-radius: 15px;
        border-left: 4px solid #2E8B57;
        margin: 1rem 0;
    }
    
    .suggestion-card {
        background: #E6F3FF;
        padding: 2rem;
        border-radius: 15px;
        border-left: 4px solid #4682B4;
        margin: 1rem 0;
    }
    
    .tips-card {
        background: #FFE4B5;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #FFD700;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .stButton > button {
        background-color: #2E8B57;
        color: white;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border: none;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #236B47;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

# Main app
def main():
    load_custom_css()
    init_session_state()
    
    # Initialize Gemini client
    client = get_gemini_client()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 💚 Health Whisperer")
        st.markdown("Your AI Wellness Coach")
        
        # Navigation
        page = st.selectbox(
            "Navigate to:",
            ["🏠 Home", "💭 Check In", "📊 History", "🔄 New Session"]
        )
        
        st.markdown("---")
        
        # Quick stats
        history_df = get_user_history(st.session_state.session_id)
        if not history_df.empty:
            st.markdown("### 📈 Your Progress")
            st.metric("Check-ins", len(history_df))
            st.metric("Last Check-in", history_df.iloc[0]['Timestamp'].split()[0] if not history_df.empty else "None")
        
        st.markdown("---")
        st.markdown("*Taking care of your mental wellness, one interaction at a time.*")
    
    # Main content based on navigation
    if page == "🏠 Home":
        show_home_page()
    elif page == "💭 Check In":
        show_mood_input_page(client)
    elif page == "📊 History":
        show_history_page()
    elif page == "🔄 New Session":
        start_new_session()

def show_home_page():
    """Display the home/landing page"""
    st.markdown('<h1 class="main-header">🧠 Your AI Wellness Coach</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Get personalized, real-time wellness suggestions based on how you\'re feeling right now.</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.page = "💭 Check In"
            st.rerun()
    
    st.markdown("---")
    
    # How it works section
    st.markdown("## 🌟 How It Works")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="mood-card">
            <h4>💬 1. Share Your Feelings</h4>
            <p>Tell us how you're feeling right now. Whether you're stressed, anxious, 
            tired, or just need guidance - we're here to listen.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="suggestion-card">
            <h4>✨ 2. Get AI Suggestions</h4>
            <p>Our AI analyzes your input and provides personalized, actionable wellness 
            suggestions you can implement immediately.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="tips-card">
            <h4>📈 3. Track Your Progress</h4>
            <p>View your wellness history to see patterns and track your emotional 
            journey over time.</p>
        </div>
        """, unsafe_allow_html=True)

def show_mood_input_page(client):
    """Display the mood input page"""
    st.markdown('<h1 class="main-header">💭 How are you feeling right now?</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Share your current mood or stress level with us, and we\'ll provide personalized wellness guidance.</p>', unsafe_allow_html=True)
    
    # Input form
    with st.form("mood_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Text input
            mood_text = st.text_area(
                "✍️ Describe your feelings",
                placeholder="For example: 'I feel anxious and tired' or 'I'm stressed about work'",
                height=120,
                help="Express yourself freely - the more specific you are, the better our suggestions."
            )
        
        with col2:
            # Dropdown alternative
            mood_options = [
                "",
                "I feel stressed and overwhelmed",
                "I feel anxious and worried", 
                "I feel sad and down",
                "I feel tired and drained",
                "I feel angry and frustrated",
                "I feel lonely and isolated",
                "I feel confused and uncertain",
                "I feel restless and can't focus",
                "I feel good but want to improve",
                "I feel neutral and seeking guidance"
            ]
            
            mood_dropdown = st.selectbox(
                "🔽 Or select from common feelings",
                mood_options,
                help="If you prefer, choose from these common feelings instead of typing."
            )
        
        # Submit button
        submitted = st.form_submit_button("🎯 Get My Wellness Suggestion", use_container_width=True)
        
        if submitted:
            # Use dropdown if text is empty, otherwise use text input
            final_mood = mood_text.strip() if mood_text.strip() else mood_dropdown
            
            if not final_mood:
                st.error("Please describe how you are feeling or select from the dropdown.")
            else:
                # Generate suggestion
                with st.spinner("Getting your personalized wellness suggestion..."):
                    suggestion = get_wellness_suggestion(final_mood, client)
                
                # Store in session state
                st.session_state.current_mood = final_mood
                st.session_state.current_suggestion = suggestion
                st.session_state.suggestion_given = True
                
                # Log the interaction
                log_interaction(final_mood, suggestion, st.session_state.session_id)
                
                st.success("✅ Your wellness suggestion is ready!")
                st.rerun()
    
    # Display suggestion if available
    if st.session_state.suggestion_given and st.session_state.current_suggestion:
        st.markdown("---")
        st.markdown("## 🎯 Your Personalized Wellness Suggestion")
        
        # User's mood
        st.markdown(f"""
        <div class="mood-card">
            <h4>💭 You shared:</h4>
            <p><em>"{st.session_state.current_mood}"</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        # AI suggestion
        st.markdown(f"""
        <div class="suggestion-card">
            <h4>✨ Here's what I suggest:</h4>
            <p><strong>{st.session_state.current_suggestion}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Check-In", use_container_width=True):
                st.session_state.suggestion_given = False
                st.session_state.current_mood = ""
                st.session_state.current_suggestion = ""
                st.rerun()
        
        with col2:
            if st.button("📊 View History", use_container_width=True):
                st.session_state.page = "📊 History"
                st.rerun()
    
    # Wellness tips
    st.markdown("---")
    st.markdown("## 💡 Wellness Fundamentals")
    
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.markdown("""
        **🫁 Breathe Mindfully**  
        Deep, conscious breathing can instantly calm your nervous system.
        
        **🚶 Move Your Body**  
        Even a short walk can boost your mood and energy levels.
        """)
    
    with tips_col2:
        st.markdown("""
        **💧 Stay Hydrated**  
        Proper hydration supports both physical and mental clarity.
        
        **🌙 Rest Well**  
        Quality sleep is the foundation of emotional resilience.
        """)

def show_history_page():
    """Display the user's wellness history"""
    st.markdown('<h1 class="main-header">📊 Your Wellness Journey</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Track your emotional patterns and see how our suggestions have helped you along the way.</p>', unsafe_allow_html=True)
    
    # Get user history
    history_df = get_user_history(st.session_state.session_id)
    
    if history_df.empty:
        st.markdown("""
        <div class="mood-card" style="text-align: center;">
            <h3>💔 No Wellness History Yet</h3>
            <p>You haven't started your wellness journey with us yet. 
            Take your first step by sharing how you're feeling right now.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💚 Start Your First Check-in", use_container_width=True):
            st.session_state.page = "💭 Check In"
            st.rerun()
    else:
        # Statistics summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>📅</h3>
                <h2>{}</h2>
                <p>Total Check-ins</p>
            </div>
            """.format(len(history_df)), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h3>⏰</h3>
                <h2>{}</h2>
                <p>Last Check-in</p>
            </div>
            """.format(history_df.iloc[0]['Timestamp'].split()[0]), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3>💚</h3>
                <h2>Growing</h2>
                <p>Wellness Progress</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # History table
        st.markdown("## 📋 Your Check-in History")
        
        # Prepare data for display
        display_df = history_df.copy()
        # Convert timestamp to datetime and format
        display_df['Date'] = pd.to_datetime(display_df['Timestamp']).dt.strftime('%b %d, %Y')
        display_df['Time'] = pd.to_datetime(display_df['Timestamp']).dt.strftime('%I:%M %p')
        
        # Display as expandable entries
        for idx, row in display_df.iterrows():
            with st.expander(f"🗓️ {row['Date']} at {row['Time']}"):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown(f"""
                    **💭 How you felt:**  
                    *"{row['Mood_Input']}"*
                    """)
                
                with col2:
                    st.markdown(f"""
                    **✨ AI Suggestion:**  
                    {row['AI_Suggestion']}
                    """)
        
        # Action buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Start New Session", use_container_width=True):
                start_new_session()
        
        with col2:
            if st.button("➡️ Continue Journey", use_container_width=True):
                st.session_state.page = "💭 Check In"
                st.rerun()

def start_new_session():
    """Start a new wellness session"""
    st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.suggestion_given = False
    st.session_state.current_mood = ""
    st.session_state.current_suggestion = ""
    st.success("🎉 New session started! Ready for a fresh wellness journey.")
    st.balloons()

if __name__ == "__main__":
    main()