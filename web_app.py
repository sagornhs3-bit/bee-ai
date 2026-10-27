"""Bee - Ultimate AI Assistant (Persistent Login via Query Params)"""

import streamlit as st
import json
import uuid
import datetime
import sys
import time
import hashlib
import requests
import urllib.parse
import random
import re
from pathlib import Path
import streamlit.components.v1 as components
import PyPDF2
from supabase import create_client, Client

BEE_DIR = Path(__file__).parent
sys.path.insert(0, str(BEE_DIR))

try:
    from memory import (get_user_name, set_user_name, build_memory_context,
                        remember, recall, get_all_facts)
except ImportError:
    pass

CONFIG_FILE = BEE_DIR / "config.json"

st.set_page_config(page_title="Bee AI", page_icon="https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png", layout="wide")

# ============================================================
# ☁️ SUPABASE CONFIGURATION
# ============================================================
SUPABASE_URL = "https://cbhqkxrldihvohplusyw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiaHFreHJsZGlodm9ocGx1c3l3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxMDM3OTUsImV4cCI6MjEwODY3OTc5NX0.Z_F2stGOybDL0liwsiYQAzldWist1sPTy7RTZSz38iE"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============================================================
# 🎬 INTRO ANIMATION
# ============================================================
if "intro_done" not in st.session_state: 
    st.session_state.intro_done = False

if not st.session_state.intro_done:
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        [data-testid="stSidebar"] {display: none;} .block-container {padding: 0 !important;}
        .splash-screen { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: #0e1117; display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 99999; }
        .splash-logo { width: 150px; animation: zoomPulse 2s infinite alternate; mix-blend-mode: screen; }
        @keyframes zoomPulse { 0% { transform: scale(0.9); filter: drop-shadow(0 0 10px #f59e0b); } 100% { transform: scale(1.1); filter: drop-shadow(0 0 30px #ef4444); } }
        .splash-text { color: white; margin-top: 20px; font-family: sans-serif; letter-spacing: 2px; }
    </style>
    <div class="splash-screen">
        <img class="splash-logo" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png">
        <h2 class="splash-text">BEE AI</h2>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.intro_done = True
    st.rerun()

# ============================================================
# 🔐 AUTO-LOGIN & INITIALIZATION
# ============================================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "msg_count" not in st.session_state: st.session_state.msg_count = 0
if "chat_id" not in st.session_state: st.session_state.chat_id = None
if "emoji_append" not in st.session_state: st.session_state.emoji_append = ""
if "voice_ui" not in st.session_state: st.session_state.voice_ui = False

# 🔥 Query Params থেকে অটো লগইন (রিফ্রেশ দিলেও লগইন থাকবে)
if "user" in st.query_params and not st.session_state.logged_in:
    saved_user = st.query_params["user"]
    with st.spinner("🔄 অটো লগইন হচ্ছে..."):
        try:
            res = supabase.table("users").select("*").eq("username", saved_user).execute()
            if res.data:
                user = res.data[0]
                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.is_premium = user["is_premium"]
                st.session_state.chat_id = None 
                
                today = datetime.date.today().strftime("%Y-%m-%d")
                if user["last_date"] != today:
                    st.session_state.msg_count = 0
                    supabase.table("users").update({"msg_count": 0, "last_date": today}).eq("username", user["username"]).execute()
                else:
                    st.session_state.msg_count = user["msg_count"]
                st.rerun()
            else:
                st.query_params.clear()
        except Exception:
            pass

# ============================================================
# 🔐 LOGIN & SIGN UP
# ============================================================
if not st.session_state.logged_in:
    st.markdown("""
    <style>
        .login-container .block-container { max-width: 450px !important; padding-top: 5vh !important; }
        .login-container .stButton > button { background-color: #f97316 !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: bold !important; }
        .login-container .stTextInput > div > div > input { border-radius: 8px !important; }
        @media (max-width: 768px) { .login-container .block-container { padding-top: 2vh !important; padding-left: 15px !important; padding-right: 15px !important; } }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🐝 Welcome to Bee AI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 14px; color: gray;'>Your Personal AI Assistant</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        st.subheader("Login to your account")
        login_user = st.text_input("Username or Email", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True, type="primary"):
            if login_user and login_pass:
                hashed_pw = hash_password(login_pass)
                res = supabase.table("users").select("*").or_(f"username.eq.{login_user},email.eq.{login_user}").execute()
                if res.data:
                    user = res.data[0]
                    if user["password"] == hashed_pw:
                        st.session_state.logged_in = True
                        st.session_state.username = user["username"]
                        st.session_state.is_premium = user["is_premium"]
                        st.session_state.chat_id = None 
                        
                        # 🔥 লগইন সেভ করা হচ্ছে URL-এ
                        st.query_params["user"] = user["username"]
                        
                        today = datetime.date.today().strftime("%Y-%m-%d")
                        if user["last_date"] != today:
                            st.session_state.msg_count = 0
                            supabase.table("users").update({"msg_count": 0, "last_date": today}).eq("username", user["username"]).execute()
                        else:
                            st.session_state.msg_count = user["msg_count"]
                        st.rerun()
                    else:
                        st.error("❌ Incorrect password.")
                else:
                    st.error("❌ User not found.")
            else:
                st.warning("Please fill all fields.")

    with tab2:
        st.subheader("Create a new account")
        new_name = st.text_input("Full Name", key="reg_name")
        new_email = st.text_input("Email", key="reg_email")
        new_user = st.text_input("Username", key="reg_user")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        
        if st.button("Sign Up", use_container_width=True, type="primary"):
            if new_name and new_email and new_user and new_pass:
                check = supabase.table("users").select("username").or_(f"username.eq.{new_user},email.eq.{new_email}").execute()
                if check.data:
                    st.error("❌ Username or Email already exists.")
                else:
                    hashed_pw = hash_password(new_pass)
                    today = datetime.date.today().strftime("%Y-%m-%d")
                    data = {"username": new_user, "email": new_email, "password": hashed_pw, "is_premium": False, "msg_count": 0, "last_date": today}
                    try:
                        supabase.table("users").insert(data).execute()
                        st.success("✅ Account created successfully! Please login.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please fill all fields.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# 🔓 MAIN APP CONFIGURATIONS
# ============================================================
def load_cfg():
    try:
        if hasattr(st, 'secrets') and "config" in st.secrets: return dict(st.secrets["config"])
    except Exception: pass
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return {"groq_api_key": ""}

CONFIG = load_cfg()
NAME = CONFIG.get("assistant_name", "Bee")
GROQ_KEY = CONFIG.get("groq_api_key", "")

DAILY_LIMIT = 20 
BKASH_NUMBER = "01840506838"
CODE_LIFETIME = "BEE-PRO" 

# ============ SYSTEM AUTO THEME ============
sys_theme = "
