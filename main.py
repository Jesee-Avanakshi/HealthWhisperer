#!/usr/bin/env python3
import os
import subprocess
from flask import Flask

# Create Flask app for gunicorn
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

@app.route('/')
def home():
    """Main page - redirect to Streamlit"""
    return '''<!DOCTYPE html>
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
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        h1 { font-size: 2.5rem; margin-bottom: 1rem; }
        p { font-size: 1.2rem; margin: 0.5rem 0; }
        .link { 
            color: #fff; 
            text-decoration: underline; 
            cursor: pointer;
            font-weight: bold;
        }
        .loading {
            margin: 2rem 0;
            font-style: italic;
        }
    </style>
</head>
<body>
    <h1>🌿 Health Whisperer</h1>
    <p>Your AI-Powered Wellness Coach</p>
    <div class="loading">Starting your wellness journey...</div>
    <p>
        <span class="link" onclick="openStreamlit()">Click here to access your wellness coach</span>
    </p>
    
    <script>
        function openStreamlit() {
            // Try different URLs to access Streamlit
            const urls = [
                window.location.origin.replace(':5000', ':8501'),
                window.location.protocol + '//' + window.location.hostname + ':8501',
                'https://workspace-replit-dev.replit-deploy.repl.co:8501/'
            ];
            
            // Open in current window
            window.location.href = urls[1];
        }
        
        // Auto redirect after 3 seconds
        setTimeout(openStreamlit, 3000);
    </script>
</body>
</html>'''

# Start Streamlit on port 8501 when app starts
def start_streamlit():
    """Start Streamlit server"""
    subprocess.Popen([
        "streamlit", "run", "streamlit_app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--server.enableXsrfProtection=false"
    ])

# Start Streamlit in background
start_streamlit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)