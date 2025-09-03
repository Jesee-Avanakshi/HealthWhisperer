# Overview

Health Whisperer is an AI-powered wellness coaching web application that provides personalized mental health suggestions based on user mood input. The application now features complete user authentication, allowing individual users to track their wellness journey separately. Users can sign up for accounts, log in securely, describe their emotions, receive personalized wellness suggestions, and maintain their own private wellness history over time.

# Recent Changes

**September 3, 2025**: Migrated from Streamlit to Flask with full user authentication system
- Implemented user signup and login functionality with secure password hashing
- Added PostgreSQL database integration for user management and wellness tracking
- Created individual user dashboards and personalized wellness histories
- Fixed database connection pooling for stable operation

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Flask with server-side rendered templates for reliable web application delivery
- **UI Design**: Clean, wellness-focused design with custom CSS styling and beautiful gradient backgrounds
- **User Interface**: Responsive design with landing page, authentication forms, dashboard, and wellness tracking
- **Pages**: Landing page with signup/login, user dashboard, mood check-in form, suggestion display, and personal history
- **Authentication Flow**: Secure user registration and login with session management

## Backend Architecture
- **Web Framework**: Flask application with user authentication and session management
- **Application Structure**: Single-file Flask app (main.py) with modular route handling
- **Authentication System**: Flask-Login with secure password hashing using Werkzeug
- **Session Management**: Flask sessions with login state tracking for authenticated users
- **Error Handling**: Graceful fallbacks for AI service failures and database connection issues

## Data Storage Solutions
- **Primary Storage**: PostgreSQL database with SQLAlchemy ORM for reliable data persistence
- **User Management**: User model with username, email, hashed passwords, and creation timestamps
- **Wellness Tracking**: WellnessInteraction model linking users to their mood inputs and AI suggestions
- **Database Configuration**: Connection pooling with pre-ping and connection recycling for stability
- **Data Relationships**: One-to-many relationship between users and their wellness interactions

## Authentication and Authorization
- **User Authentication**: Complete signup and login system with secure password hashing
- **Session Management**: Flask-Login integration for user session tracking across requests
- **Privacy**: Individual user accounts with private wellness histories
- **Security**: Protected routes requiring login, password validation, and duplicate account prevention

## External Dependencies

### Database Integration
- **PostgreSQL**: Replit's built-in PostgreSQL database for user and interaction storage
- **SQLAlchemy**: ORM for database operations with Flask-SQLAlchemy integration
- **Connection Management**: Pool recycling and pre-ping for stable database connections

### Authentication Libraries
- **Flask-Login**: User session management and authentication state tracking
- **Werkzeug Security**: Password hashing and verification for secure user authentication

### AI Service Integration (Future Enhancement)
- **Google Gemini API**: Available for integration with GEMINI_API_KEY environment variable
- **Fallback System**: Built-in wellness suggestions when AI service is unavailable
- **Response Format**: Random selection from curated wellness suggestions library

### Environment Configuration
- **Database URL**: PostgreSQL connection via DATABASE_URL environment variable
- **Session Secret**: Flask session secret key via SESSION_SECRET environment variable
- **Port Configuration**: Flask configured to run on port 5000 with 0.0.0.0 binding for Replit compatibility