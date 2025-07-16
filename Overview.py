import streamlit as st
import streamlit.components.v1 as components
import os


# Optional: only inject once per app run
def inject_google_analytics():
    try:
        with open("public/google_analytics.html", "r") as f:
            components.html(f.read(), height=0)
    except FileNotFoundError:
        st.warning("Google Analytics file not found.")

inject_google_analytics()


# Set page config for better appearance
st.set_page_config(
    page_title="Smart Meal Helper",
    page_icon="🥗",      
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page title
st.markdown('<h1 class="title-text">Smart Meal Analyzer</h1>', unsafe_allow_html=True)

# Introduction paragraph
st.markdown("""
<div class="intro">
No sign in, no subscriptions, no hassle. Welcome to the <strong>Smart Meal Analyzer</strong>, a tool designed to help you make smarter, nutrition-focused choices at a meal-by-meal level.
Leveraging trusted data from the USDA FoodData Central, this app gives you fast, accurate insight into your meal’s calorie, macronutrient, and sugar content.
Whether you're planning meals, managing dietary goals, or just aiming to eat cleaner — this AI tool supports you every step of the way.
</div>
""", unsafe_allow_html=True)

# Bullet list of features
st.markdown("""
<div class="bullets">
<ul>
    <li>Search and browse foods from a comprehensive USDA-based database</li>
    <li>Log and adjust your planned meals</li>
    <li>Modify portion sizes by gram weight</li>
    <li>View real-time calorie, macro, and sugar estimates</li>
    <li>Receive relevant AI advice on helpful adjustments for planned meals</li>
	
</ul>
</div>
""", unsafe_allow_html=True)



st.markdown("""
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        font-size: 13px;
        color: gray;
        padding: 8px;
        background-color: rgba(0,0,0,0);  /* Transparent background */
    }
    </style>
    <div class="footer">
         2025 Smart Meal Helper
    </div>
""", unsafe_allow_html=True)
