# 🌿 HealthWhisperer

**HealthWhisperer** is an AI-powered wellness coach built with **Flask**.  
It helps users track their emotions, receive personalized suggestions, and log nutrition habits — all under their own accounts.  

---

## ✨ Features
- 🔐 **User Accounts** → Signup, login, logout with secure password hashing.  
- 💭 **Mood Check-ins** → Log how you feel and receive AI-powered wellness suggestions.  
- 📊 **Dashboard** → Personalized charts showing mood trends and history.  
- 🍎 **Food & Nutrition Tracker** → Log meals, hydration, and get calorie/macronutrient analysis.  
- 🗄 **PostgreSQL Database** → Persistent storage of users, moods, and nutrition logs.  
- 🔑 **Session Management** → Powered by Flask-Login.  

---

## ⚙️ Tech Stack
- **Backend**: Flask (Python 3.11)  
- **Database**: PostgreSQL (SQLAlchemy + psycopg2)  
- **Authentication**: Flask-Login + Werkzeug security  
- **AI**: Google Gemini API (`google-genai`)  
- **Deployment**: Gunicorn + AWS (EC2/Elastic Beanstalk)  

---

## 🚀 Getting Started

### 1️⃣ Clone the Repo
```bash
git clone https://github.com/<your-username>/HealthWhisperer.git
cd HealthWhisperer
