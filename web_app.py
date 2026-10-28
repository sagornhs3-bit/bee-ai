"""Bee - Ultimate AI Assistant (Fixed Model + Streaming + Image Gen)"""

import streamlit as st
import json
import uuid
import datetime
from zoneinfo import ZoneInfo
import sys
import time
import hashlib
import requests
import urllib.parse
import random
import re
import io
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
if "persona" not in st.session_state: st.session_state.persona = "Default Bee"
if "last_prompt" not in st.session_state: st.session_state.last_prompt = ""

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

DAILY_LIMIT = 100 
BKASH_NUMBER = "01840506838"
CODE_LIFETIME = "BEE-PRO"
CODE_MONTHLY = "BEE-MONTH" 

# ============ SYSTEM AUTO THEME ============
sys_theme = "dark"
try:
    if hasattr(st, 'context') and hasattr(st.context, 'theme'): sys_theme = st.context.theme.type
except Exception: pass

if "theme_choice" not in st.session_state: st.session_state.theme_choice = "⚙️ System"
if st.session_state.theme_choice == "⚙️ System": dark = (sys_theme == "dark")
elif st.session_state.theme_choice == "🌙 Dark": dark = True
else: dark = False

# ============ PERSONAS ============
PERSONAS = {
    "Default Bee": "You are Bee, a helpful and friendly AI assistant.",
    "Coder Bee": "You are an expert software engineer. Provide clean, optimized code with clear explanations.",
    "Storyteller": "You are a creative writer. Write engaging and imaginative stories.",
    "Teacher": "You are a patient teacher. Explain concepts simply with real-life examples.",
    "Motivator": "You are an energetic life coach. Motivate the user and give practical advice."
}

# ============ STORAGE (Supabase) ============
def load_chats():
    res = supabase.table("chats").select("*").eq("username", st.session_state.username).order("created_at", desc=True).execute()
    if res.data: return {"chats": res.data}
    return {"chats": []}

def new_chat():
    data = load_chats()
    if data["chats"] and data["chats"][0]["title"] == "New Chat" and len(data["chats"][0]["messages"]) == 0:
        st.session_state.chat_id = data["chats"][0]["id"]
        return
    cid = str(uuid.uuid4())
    supabase.table("chats").insert({"id": cid, "username": st.session_state.username, "title": "New Chat", "messages": []}).execute()
    st.session_state.chat_id = cid

def get_chat(cid):
    res = supabase.table("chats").select("*").eq("id", cid).execute()
    if res.data: return res.data[0]
    return None

def add_msg(cid, role, content):
    chat = get_chat(cid)
    if chat:
        messages = chat["messages"]
        messages.append({"role": role, "content": content})
        title = chat["title"]
        if role == "user" and title == "New Chat":
            title = content[:28] + ("..." if len(content) > 28 else "")
        supabase.table("chats").update({"messages": messages, "title": title}).eq("id", cid).execute()

def del_chat(cid):
    supabase.table("chats").delete().eq("id", cid).execute()

_groq = None
def get_groq():
    global _groq
    if _groq is None and GROQ_KEY.startswith("gsk_"):
        try:
            import groq
            _groq = groq.Groq(api_key=GROQ_KEY)
        except Exception: _groq = None
    return _groq

# ============ HELPERS ============
def speak_text(text):
    js_text = json.dumps(text)
    js_code = f"""
    <script>
        var msg = new SpeechSynthesisUtterance({js_text});
        var isBengali = /[\u0980-\u09FF]/.test({js_text});
        msg.lang = isBengali ? 'bn-BD' : 'en-US'; 
        msg.pitch = 0.1; msg.rate = 0.85; msg.volume = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

def transcribe_audio(audio_file):
    client = get_groq()
    if not client or not audio_file: return None
    try:
        audio_bytes = audio_file.read()
        transcription = client.audio.transcriptions.create(
            file=("voice.wav", audio_bytes), model="whisper-large-v3-turbo", response_format="text")
        return transcription.strip()
    except Exception as e:
        st.error(f"❌ ভয়েস বুঝতে সমস্যা: {e}"); return None

def search_web(query):
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=3)
        if not results: return "No search results."
        return "\n".join([f"{res['title']}: {res['body']}" for res in results])
    except Exception as e: return f"Search error: {e}"

def extract_text_from_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in reader.pages])[:4000]
        elif uploaded_file.name.endswith(('.txt', '.csv')):
            return str(uploaded_file.read(), "utf-8")[:4000]
    except Exception: return ""
    return ""

# ============ AI LOGIC (STREAMING + IMAGE GEN FIXED) ============
def ask_llm_stream(prompt, chat_history, file_context=""):
    client = get_groq()
    if not client: 
        yield "API Key নেই।"
        return

    image_keywords = ["ছবি তৈরি", "ছবি বানাও", "draw", "generate image", "picture of", "paint", "pic", "image", "photo", "আঁকো", "আঁক", "banao", "bana", "chobi", "ছবি"]
    
    if any(kw in prompt.lower() for kw in image_keywords):
        yield "🎨 **Bee is drawing your image...**\n\n"
        
        # 🔥 ইমেজ প্রম্পট এনহ্যান্সমেন্ট (ChatGPT-এর মতো ডিটেইল তৈরি করা)
        enhance_sys = """You are an expert AI image prompt engineer. Take the user's idea and create a highly detailed, descriptive English prompt suitable for the Flux image generation model. 
        Always explicitly specify the art style (e.g., cartoon, 3D render, anime, photorealistic), lighting, colors, and character details. 
        Output ONLY the final English prompt. Do not add quotes or extra text."""
        
        enhance_msg = [
            {"role": "system", "content": enhance_sys},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # ✅ নতুন মডেল আপডেট করা হয়েছে
            enhanced_res = client.chat.completions.create(model="openai/gpt-oss-120b", messages=enhance_msg, temperature=0.7)
            clean_prompt = enhanced_res.choices[0].message.content.strip()
        except Exception:
            clean_prompt = prompt
        
        seed = random.randint(1, 999999)
        encoded_prompt = urllib.parse.quote(clean_prompt)
        # 🔥 URL-এ enhance=true যুক্ত করা হয়েছে
        img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model=flux&enhance=true"
        
        yield f"![Generated Image]({img_url})\n\n"
        yield f"_[📥 Download Image]({img_url})_"
        return

    web_context = ""
    if any(w in prompt.lower() for w in ["search", "who is", "news", "খবর", "current", "today", "weather", "time"]):
        with st.spinner("🌐 ইন্টারনেটে খুঁজছি..."):
            web_context = search_web(prompt)

    dhaka_time = datetime.datetime.now(ZoneInfo("Asia/Dhaka"))
    current_time_str = dhaka_time.strftime("%I:%M %p, %d %B %Y")
    
    persona_instruction = PERSONAS.get(st.session_state.persona, PERSONAS["Default Bee"])

    sys_prompt = f"""{persona_instruction}
{file_context}

## Context Information:
- Current Date & Time in Bangladesh: {current_time_str}
- Web Context: {web_context}

## Rules:
1. Reply in the EXACT same language the user uses.
2. NEVER use markdown headers. Use bullet points.
3. Keep responses helpful and engaging.
"""
    
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in chat_history:
        if isinstance(msg, dict) and msg.get("content", "").strip():
            role = "assistant" if msg.get("role") in ["bee", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        # ✅ নতুন মডেল আপডেট করা হয়েছে
        stream = client.chat.completions.create(
            model="openai/gpt-oss-120b", 
            messages=messages, 
            temperature=0.5,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Error: {e}"

# ============================================================
# 🎨 PREMIUM CSS
# ============================================================
if dark:
    bg_base = "#0e1117"
    txt = "#fafafa"
    sidebar_bg = "rgba(14, 17, 23, 0.7)"
    chat_input_bg = "rgba(30, 30, 40, 0.7)" 
    btn_bg = "#262730"
    btn_txt = "#fafafa"
    border_col = "rgba(255,255,255,0.1)"
    glass_bg = "rgba(30, 30, 40, 0.4)"
    watermark_opacity = "0.08"
    radio_bg = "#262730"
    radio_border = "#ffffff"
else:
    bg_base = "#ffffff"
    txt = "#1a1a1a" 
    sidebar_bg = "rgba(255, 255, 255, 0.7)"
    chat_input_bg = "rgba(255, 255, 255, 0.8)" 
    btn_bg = "rgba(255, 255, 255, 0.9)" 
    btn_txt = "#1a1a1a" 
    border_col = "rgba(0,0,0,0.1)" 
    glass_bg = "rgba(255, 255, 255, 0.5)" 
    watermark_opacity = "0.08"
    radio_bg = "#ffffff"
    radio_border = "#f97316"

css = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, {bg_base} 0%, #1a1124 50%, #241211 100%) !important;
        background-size: 200% 200% !important;
        animation: gradientBG 15s ease infinite !important;
        background-attachment: fixed !important;
    }}
    @keyframes gradientBG {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stVerticalBlock"], .main, .block-container {{
        background: transparent !important;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: ""; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        width: 600px; height: 600px;
        background-image: url('https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png');
        background-size: contain; background-repeat: no-repeat;
        opacity: {watermark_opacity}; z-index: 0; pointer-events: none;
    }}
    .main .block-container {{ padding-top: 1.5rem; max-width: 900px; padding-bottom: 120px !important; z-index: 1; }}
    [data-testid="stSidebar"] {{ background: {sidebar_bg} !important; backdrop-filter: blur(15px) !important; border-right: 1px solid {border_col} !important; }}
    .main p, .main span, .main label, .main h1, .main h2, .main h3, .main h4, .main h5, .main h6, .main li, .main td, .main th,
    [data-testid="stChatMessage"] *, [data-testid="stMarkdownContainer"] *,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{ color: {txt} !important; }}
    [data-testid="stChatMessage"] {{
        background: {glass_bg} !important; backdrop-filter: blur(20px) !important; -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid {border_col} !important; border-radius: 20px !important; padding: 20px !important; 
        margin-bottom: 20px !important; display: flex !important; flex-direction: row !important; align-items: flex-start !important;
        z-index: 1; box-shadow: 0 4px 20px rgba(0,0,0,0.1) !important;
    }}
    [data-testid="stChatMessage"]:not(:has([data-testid="chatAvatarIcon-user"])) {{ animation: aiGlow 3s infinite alternate !important; }}
    @keyframes aiGlow {{
        0% {{ box-shadow: 0 0 5px rgba(249, 115, 22, 0.1) !important; border-color: rgba(255,255,255,0.1) !important; }}
        100% {{ box-shadow: 0 0 20px rgba(249, 115, 22, 0.4) !important; border-color: rgba(249, 115, 22, 0.5) !important; }}
    }}
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
        flex-direction: row-reverse !important; background: rgba(249, 115, 22, 0.15) !important; 
        border: 1px solid rgba(249, 115, 22, 0.3) !important; animation: userGlow 3s infinite alternate !important;
    }}
    @keyframes userGlow {{
        0% {{ box-shadow: 0 0 5px rgba(249, 115, 22, 0.2) !important; }}
        100% {{ box-shadow: 0 0 20px rgba(249, 115, 22, 0.6) !important; }}
    }}
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {{ text-align: right !important; }}
    .header {{ background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important; padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem; display: flex; align-items: center; overflow: hidden; box-shadow: 0 8px 20px rgba(239, 68, 68, 0.2); }}
    .header h1 {{ margin: 0; font-size: 1.8rem; color: #ffffff !important; }}
    .header p {{ margin: 0.3rem 0 0; opacity: 0.95; font-size: 0.95rem; color: #ffffff !important; }}
    @keyframes talk {{
        0% {{ transform: translateY(0px) scale(1); filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.3)); }}
        50% {{ transform: translateY(-8px) scale(1.05); filter: drop-shadow(0 0 25px rgba(249, 115, 22, 0.8)); }}
        100% {{ transform: translateY(0px) scale(1); filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.3)); }}
    }}
    .logo-3d {{ animation: talk 3s ease-in-out infinite; border-radius: 50%; mix-blend-mode: multiply; max-height: 80px; object-fit: contain; }}
    .stButton > button {{ background-color: {btn_bg} !important; color: {btn_txt} !important; border: 1px solid {border_col} !important; border-radius: 10px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important; transition: all 0.2s !important; }}
    .stButton > button:hover {{ border-color: #f97316 !important; color: #f97316 !important; }}
    .stButton > button p, .stButton > div {{ color: {btn_txt} !important; }}
    [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {{ background-color: {radio_bg} !important; border: 2px solid {radio_border} !important; }}
    [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child > div {{ background-color: #f97316 !important; transform: scale(1.2) !important; }}
    [data-testid="stAudioInput"] {{ background-color: #ffffff !important; border-radius: 12px !important; border: 2px solid #f97316 !important; box-shadow: 0 4px 15px rgba(249, 115, 22, 0.15) !important; padding: 10px !important; }}
    [data-testid="stAudioInput"] * {{ color: #1a1a1a !important; fill: #f97316 !important; }}
    [data-testid="stAudioInput"] button {{ background-color: #f97316 !important; color: white !important; border: none !important; }}
    [data-testid="stAudioInput"] button svg {{ fill: white !important; color: white !important; }}
    [data-testid="stBottom"] {{ background: transparent !important; padding-bottom: 15px !important; }}
    [data-testid="stChatInput"] {{ 
        background: {chat_input_bg} !important; backdrop-filter: blur(20px) !important; -webkit-backdrop-filter: blur(20px) !important;
        border: 2px solid #f97316 !important; border-radius: 30px !important; padding: 2px 10px !important; 
        box-shadow: 0 0 15px rgba(249, 115, 22, 0.4) !important; animation: inputGlow 3s infinite alternate !important;
    }}
    @keyframes inputGlow {{
        0% {{ box-shadow: 0 0 10px rgba(249, 115, 22, 0.2) !important; border-color: rgba(249, 115, 22, 0.5) !important; }}
        100% {{ box-shadow: 0 0 25px rgba(249, 115, 22, 0.7) !important; border-color: rgba(249, 115, 22, 1) !important; }}
    }}
    [data-testid="stChatInput"] > div, [data-testid="stChatInput"] div[data-testid="stVerticalBlock"], [data-testid="stChatInput"] div[data-testid="stHorizontalBlock"] {{ background-color: transparent !important; border: none !important; box-shadow: none !important; }}
    [data-testid="stChatInput"] textarea {{ background-color: transparent !important; color: {txt} !important; padding-right: 80px !important; border: none !important; box-shadow: none !important; }}
    [data-testid="stChatInput"] button {{ background-color: #f97316 !important; color: white !important; border-radius: 50% !important; transition: all 0.3s !important; border: none !important; }}
    [data-testid="stChatInput"] button:hover {{ transform: scale(1.1) !important; box-shadow: 0 0 15px rgba(249, 115, 22, 0.8) !important; }}
    @media (max-width: 768px) {{
        .main .block-container {{ padding-left: 10px !important; padding-right: 10px !important; padding-bottom: 120px !important; }}
        .header h1 {{ font-size: 1.4rem !important; }}
        .header p {{ font-size: 0.8rem !important; }}
        [data-testid="stChatInput"] {{ border-radius: 25px !important; margin-bottom: 10px !important; }}
    }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    [data-testid="stHeader"] {{ background: transparent !important; z-index: 999; }}
    .stDeployButton {{display: none !important;}}
    [data-testid="collapsedControl"] {{ display: flex !important; visibility: visible !important; opacity: 1 !important; position: fixed !important; top: 15px !important; left: 15px !important; z-index: 99999 !important; background-color: #f97316 !important; color: white !important; border-radius: 50% !important; padding: 8px !important; box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important; }}
    [data-testid="collapsedControl"] svg {{ fill: white !important; color: white !important; }}
    [data-testid="stPopover"] > button {{ background-color: {btn_bg} !important; color: {btn_txt} !important; border: 1px solid {border_col} !important; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important; }}
    [data-testid="stPopoverBody"] {{ background-color: #ffffff !important; border: 1px solid {border_col} !important; box-shadow: 0 10px 30px rgba(0,0,0,0.1) !important; }}
    .voice-card {{ background: {glass_bg}; backdrop-filter: blur(25px); border-radius: 30px; padding: 50px 20px; text-align: center; box-shadow: 0 15px 50px rgba(0,0,0,0.1); border: 2px solid rgba(249, 115, 22, 0.3); margin-top: 5vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ============================================================
# 🎤 VOICE UI (Premium Locked)
# ============================================================
if st.session_state.voice_ui:
    if not st.session_state.is_premium:
        st.error("🔒 ভয়েস ফিচারটি শুধুমাত্র প্রিমিয়াম ইউজারদের জন্য।")
        if st.button("🔙 Back to Chat", use_container_width=True):
            st.session_state.voice_ui = False
            st.rerun()
        st.stop()

    st.markdown(f"""
    <div class="voice-card">
        <img class="logo-3d" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png" width="150">
        <h2 style="margin-top: 20px; color: {txt};">Listening...</h2>
        <p style="color: gray; margin-bottom: 30px;">Tap the mic below and speak your mind.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        audio_val = st.audio_input("Record", label_visibility="collapsed", key="voice_recorder")
        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🚀 Send to Bee", use_container_width=True, type="primary"):
                if audio_val:
                    with st.spinner("🎤 Processing voice..."):
                        user_msg = transcribe_audio(audio_val)
                        if user_msg:
                            if st.session_state.chat_id is None: new_chat()
                            add_msg(st.session_state.chat_id, "user", user_msg)
                            st.session_state.last_prompt = user_msg
                            st.session_state.voice_ui = False
                            st.rerun()
                else:
                    st.warning("Please record something first.")
        with btn_col2:
            if st.button("❌ Close", use_container_width=True):
                st.session_state.voice_ui = False
                st.rerun()
    st.stop()

# ============================================================
# 🖼️ IMAGE RENDERING HELPER
# ============================================================
def render_message_with_image(content):
    img_match = re.search(r'!\[.*?\]\((https://image\.pollinations\.ai/.*?)\)', content)
    if img_match:
        text_before = content.split(img_match.group(0))[0]
        st.markdown(text_before)
        img_url = img_match.group(1)
        try:
            st.image(img_url, use_column_width=True)
        except Exception:
            st.error("⚠️ ছবিটি লোড হতে সমস্যা হচ্ছে।")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<a href="{img_url}" target="_blank" download style="text-decoration: none;"><div style="width:100%; border-radius:8px; padding:6px; background:#f97316; color:white; text-align:center; font-size:13px;">📥 Download</div></a>', unsafe_allow_html=True)
        with col2:
            if st.button("🔗 Share", key=f"share_{hash(img_url)}", use_container_width=True):
                st.toast("✅ লিংক কপি হয়েছে!")
        with col3:
            if st.button("👍 Like", key=f"like_{hash(img_url)}", use_container_width=True):
                st.toast("❤️ ধন্যবাদ!")
        with col4:
            if st.button("🚩 Report", key=f"report_{hash(img_url)}", use_container_width=True):
                st.toast("🚨 রিপোর্ট করা হয়েছে।")
        text_after = content.split(img_match.group(0))[1] if len(content.split(img_match.group(0))) > 1 else ""
        st.markdown(text_after)
    else:
        st.markdown(content)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    st.caption(f"👤 **{st.session_state.username}**")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.query_params.clear()
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
    st.divider()
    
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
    st.divider()

    st.markdown("**🎭 AI Persona**")
    selected_persona = st.selectbox("Choose AI behavior", list(PERSONAS.keys()), label_visibility="collapsed")
    if selected_persona != st.session_state.persona:
        st.session_state.persona = selected_persona
        st.rerun()
    st.divider()
    
    if st.session_state.is_premium:
        st.success("🌟 PRO User (Unlimited Chat & Voice)")
    else:
        st.info(f"💬 আজকের ফ্রি মেসেজ বাকি: {DAILY_LIMIT - st.session_state.msg_count}/{DAILY_LIMIT}")
    st.divider()
    
    if st.session_state.is_premium:
        if st.button("🎤 Start Voice Chat", use_container_width=True):
            st.session_state.voice_ui = True
            st.rerun()
    else:
        st.button("🔒 Voice Chat (Premium)", disabled=True, use_container_width=True, help="Upgrade to premium to unlock voice features.")
                
    with st.popover("😊 Emoji", use_container_width=True):
        st.markdown("### Select an Emoji")
        emoji_list = ["😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗", "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄", "😯", "😦", "😧", "😮", "😲", "🥱", "😴", "🤤", "😪", "😵", "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈", "👿", "👹", "👺", "🤡", "💩", "👻", "💀", "☠️", "👽", "👾", "🤖", "🎃", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "👍", "👎", "👊", "✊", "🤛", "🤜", "🤞", "✌️", "🤟", "🤘", "👌", "👈", "👉", "👆", "👇", "☝️", "✋", "🤚", "🖐", "🖖", "👋", "🤙", "💪", "🦾", "🙏", "✍️", "🤝", "💅", "🤳", "💍", "💄", "💋", "👄", "👅", "👂", "🦻", "👃", "👣", "👁", "👀", "🫀", "🧠", "🫁", "🦷", "🦴", "👤", "👥", "🗣", "👶", "🧒", "👦", "👧", "🧑", "👱", "👨", "🧔", "👩", "🧓", "👴", "👵"]
        cols = st.columns(5)
        for i, em in enumerate(emoji_list):
            with cols[i % 5]:
                if st.button(em, key=f"em_{em}"):
                    st.session_state.emoji_append += em
                    st.rerun()
                    
    if st.session_state.emoji_append:
        st.caption(f"Selected: {st.session_state.emoji_append}")

    st.divider()
    st.markdown("**💬 History**")
    chats = load_chats()["chats"]
    if not chats: st.caption("No chats yet")
    for c in chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            active = "🟢 " if c["id"] == st.session_state.chat_id else ""
            if st.button(f"{active}{c['title'][:22]}", key=f"c_{c['id']}", use_container_width=True):
                st.session_state.chat_id = c["id"]; st.rerun()
        with col2:
            if st.button("✕", key=f"d_{c['id']}"):
                del_chat(c["id"])
                if st.session_state.chat_id == c["id"]: st.session_state.chat_id = None
                st.rerun()
    st.divider()
    
    if st.session_state.chat_id:
        cur_chat = get_chat(st.session_state.chat_id)
        if cur_chat and cur_chat["messages"]:
            chat_text = "\n".join([f"{'You' if m['role']=='user' else 'Bee'}: {m['content']}" for m in cur_chat["messages"]])
            st.download_button(
                label="📥 Export Chat (.txt)",
                data=chat_text,
                file_name=f"Bee_Chat_{st.session_state.chat_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    st.markdown("**🎨 Theme**")
    theme_options = ["⚙️ System", "🌙 Dark", "☀️ Light"]
    current_idx = theme_options.index(st.session_state.theme_choice) if st.session_state.theme_choice in theme_options else 0
    selected_theme = st.radio("Theme", theme_options, index=current_idx, horizontal=True, label_visibility="collapsed")
    if selected_theme != st.session_state.theme_choice:
        st.session_state.theme_choice = selected_theme; st.rerun()

# ============ MAIN CHAT AREA ============
st.markdown(f"""
<div class="header">
    <img class="logo-3d" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png" width="80" style="margin-right: 20px;">
    <div>
        <h1 style="margin: 0; font-size: 2rem; color: white;">{NAME}</h1>
        <p style="margin: 0; font-size: 1rem; color: #f0f0f0;">Your Personal AI — Brilliant, Emotional, Ever-ready</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.chat_id is None:
    new_chat(); st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None: 
    new_chat(); st.rerun()

# Display Chat History
if not cur["messages"]:
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{st.session_state.username}**! I'm {NAME}. How can I help you today? 😊")
else:
    for i, m in enumerate(cur["messages"]):
        avatar_icon = "👤" if m["role"] == "user" else "https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"
        with st.chat_message(m["role"], avatar=avatar_icon): 
            render_message_with_image(m["content"])
            
            if m["role"] in ["bee", "assistant"] and i == len(cur["messages"]) - 1:
                if st.button("🔄 Regenerate Response", key="regen_btn", help="Get a different answer"):
                    msgs = cur["messages"]
                    msgs.pop() 
                    supabase.table("chats").update({"messages": msgs}).eq("id", st.session_state.chat_id).execute()
                    st.rerun()

# ============ INPUT AREA & PAYWALL ============
user_message = None
file_context = ""

if (not st.session_state.is_premium) and (st.session_state.msg_count >= DAILY_LIMIT):
    st.warning("⚠️ আপনার আজকের ১০০টি ফ্রি মেসেজের লিমিট শেষ! আগামীকাল আবার রিসেট হবে অথবা প্রিমিয়ামে আপগ্রেড করুন।")
    with st.container(border=True):
        st.markdown("### 💎 Bee AI Premium Plans")
        st.markdown(f"**🌟 Monthly Plan (Unlimited Chat + Voice):** মাত্র **$4**")
        st.markdown(f"**♾️ Lifetime Plan (Unlimited Chat + Voice):** মাত্র **1200 TK / $10**")
        st.markdown(f"📱 **bKash (Lifetime):** `{BKASH_NUMBER}`")
        
        col1, col2 = st.columns(2)
        with col1: 
            unlock_input = st.text_input("Unlock Code", type="password")
        with col2:
            st.write("") 
            st.write("") 
            if st.button("🔓 Unlock Premium", use_container_width=True, type="primary"):
                if unlock_input == CODE_LIFETIME or unlock_input == CODE_MONTHLY:
                    supabase.table("users").update({"is_premium": True}).eq("username", st.session_state.username).execute()
                    st.session_state.is_premium = True
                    st.success("🎉 অভিনন্দন! আপনি এখন Premium ইউজার।")
                    time.sleep(1); st.rerun()
                elif unlock_input != "":
                    st.error("❌ ভুল আনলক কোড!")
else:
    chat_data = st.chat_input("Type your message here...", accept_file=True, file_type=["pdf", "txt", "csv"])
    if chat_data:
        user_message = chat_data.text
        if st.session_state.emoji_append:
            user_message = st.session_state.emoji_append + " " + (user_message or "")
            st.session_state.emoji_append = "" 
        if chat_data.files:
            uploaded_file = chat_data.files[0]
            file_context = extract_text_from_file(uploaded_file)
            st.toast(f"📎 File '{uploaded_file.name}' attached!")

# ============ HANDLE TEXT INPUT (STREAMING) ============
if user_message:
    if not st.session_state.is_premium:
        st.session_state.msg_count += 1
        supabase.table("users").update({"msg_count": st.session_state.msg_count}).eq("username", st.session_state.username).execute()
        
    add_msg(st.session_state.chat_id, "user", user_message)
    st.session_state.last_prompt = user_message
    
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_message)

    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        current_chat = get_chat(st.session_state.chat_id)
        history = current_chat["messages"][:-1]
        full_response = st.write_stream(ask_llm_stream(user_message, history, file_context))
        
    add_msg(st.session_state.chat_id, "bee", full_response)
    st.rerun()
