# Overview

Health Whisperer is an AI-powered wellness coaching web application that provides personalized mental health suggestions based on user mood input. The application uses Google's Gemini AI model to generate compassionate, actionable wellness recommendations tailored to how users are feeling in real-time. Users can describe their emotions through text input or dropdown selections, receive AI-generated suggestions, and track their wellness journey over time through a history feature built with Streamlit.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit for rapid web app development with built-in UI components
- **UI Design**: Clean, wellness-focused design with custom CSS styling and calming color palette (sea green primary, slate gray secondary)
- **User Interface**: Interactive sidebar navigation, responsive layout with multi-column designs
- **Pages**: Home landing page, mood input form, suggestion display, and history tracking
- **Client-side**: Streamlit's built-in interactivity with session state management

## Backend Architecture
- **Web Framework**: Streamlit application with single-file architecture
- **Application Structure**: Modular functions for different pages and AI integration within streamlit_app.py
- **Session Management**: Streamlit session state with unique session IDs for anonymous users
- **Error Handling**: Graceful fallbacks for AI service failures with default wellness suggestions

## Data Storage Solutions
- **Primary Storage**: CSV file-based logging system using pandas for data persistence
- **Data Structure**: CSV with columns for Timestamp, Session_ID, Mood_Input, and AI_Suggestion
- **Data Processing**: Pandas for CSV data manipulation, filtering, and display formatting
- **Session Tracking**: Unique session IDs generated with datetime stamps for user separation

## Authentication and Authorization
- **Current State**: Anonymous session-based tracking using Streamlit session state
- **Session Management**: Auto-generated session IDs for tracking user interactions across page visits
- **Privacy**: No user authentication required, maintaining user privacy and ease of access

## External Dependencies

### AI Service Integration
- **Google Gemini API**: Gemini-2.5-flash model integration for generating wellness suggestions
- **API Client**: Google GenAI Python client library for API communication
- **Response Format**: Direct text responses from Gemini for natural wellness suggestions
- **Fallback System**: Default suggestions when AI service is unavailable

### Third-party Libraries
- **Streamlit**: Web application framework with built-in UI components and state management
- **Data Processing**: Pandas for CSV data manipulation and datetime formatting
- **AI Integration**: google-genai library for Gemini API communication
- **Data Types**: Pydantic for structured data validation (BaseModel import)

### Environment Configuration
- **Gemini API Key**: Required GEMINI_API_KEY environment variable for AI service access
- **Port Configuration**: Streamlit configured to run on port 5000 with 0.0.0.0 binding for Replit compatibility