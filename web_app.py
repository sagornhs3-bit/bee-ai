"""Bee - Ultimate AI Assistant (ChatGPT Voice Mode + Light Theme + Fixed Model)"""

import streamlit as st
import json
import uuid
import datetime
import sys
import time
import hashlib
import requests
import urllib.parse
from pathlib import Path
import streamlit.components.v1 as components
import PyPDF2
from supabase import create_client, Client
import extra_streamlit_components as stx

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
# ☁️ SUPABASE & COOKIE CONFIGURATION
# ============================================================
SUPABASE_URL = "https://cbhqkxrldihvohplusyw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNiaHFreHJsZGlodm9ocGx1c3l3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMxMDM3OTUsImV4cCI6MjEwODY3OTc5NX0.Z_F2stGOybDL0liwsiYQAzldWist1sPTy7RTZSz38iE"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
cookie_manager = stx.CookieManager()

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
if "voice_ui" not in st.session_state: st.session_state.voice_ui = False # Voice UI State

if not st.session_state.logged_in:
    saved_user = cookie_manager.get(cookie="bee_user")
    if saved_user:
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
                    cookie_manager.delete("bee_user")
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
                        
                        expires = datetime.datetime.now() + datetime.timedelta(days=36500)
                        cookie_manager.set("bee_user", user["username"], expires_at=expires)
                        
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
sys_theme = "dark"
try:
    if hasattr(st, 'context') and hasattr(st.context, 'theme'): sys_theme = st.context.theme.type
except Exception: pass

if "theme_choice" not in st.session_state: st.session_state.theme_choice = "⚙️ System"
if st.session_state.theme_choice == "⚙️ System": dark = (sys_theme == "dark")
elif st.session_state.theme_choice == "🌙 Dark": dark = True
else: dark = False

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
        st.error(f"❌ ভয়েস বুঝতে সমস্যা: {e}"); return None

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

# ============ AI LOGIC ============
def ask_llm(prompt, chat_history, file_context=""):
    client = get_groq()
    if not client: return "API Key নেই।"

    image_keywords = ["ছবি তৈরি", "ছবি বানাও", "draw", "generate image", "picture of", "paint"]
    if any(kw in prompt.lower() for kw in image_keywords):
        with st.spinner("🎨 ছবি তৈরি করা হচ্ছে..."):
            clean_prompt = prompt
            for kw in image_keywords:
                clean_prompt = clean_prompt.replace(kw, "")
            clean_prompt = clean_prompt.strip()
            if not clean_prompt: clean_prompt = "beautiful scenery"
            
            encoded_prompt = urllib.parse.quote(clean_prompt)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            
            return f"আপনার অনুরোধ অনুযায়ী ছবিটি তৈরি করেছি:\n\n![Generated Image]({img_url})\n\n_ছবিটি ডাউনলোড করতে ছবির ওপর রাইট ক্লিক করুন।_"

    web_context = ""
    if any(w in prompt.lower() for w in ["search", "who is", "news", "খবর", "current", "today", "weather", "time"]):
        with st.spinner("🌐 ইন্টারনেটে খুঁজছি..."):
            web_context = search_web(prompt)

    sys_prompt = f"""You are {NAME}, a helpful AI assistant.
{file_context}

## Web Context:
{web_context}

## Rules:
1. Reply in the EXACT same language the user uses.
2. NEVER use markdown headers. Use bullet points.
3. Be highly intelligent and helpful.
"""
    
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in chat_history:
        if isinstance(msg, dict) and msg.get("content", "").strip():
            role = "assistant" if msg.get("role") in ["bee", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        # 🔥 Groq এর নতুন সক্রিয় মডেল (llama-3.3 বন্ধ হয়ে যাওয়ায় এটি ব্যবহার করা হলো)
        r = client.chat.completions.create(model="llama-3.1-70b-versatile", messages=messages, temperature=0.5)
        return r.choices[0].message.content.strip()
    except Exception as e:
        # যদি উপরের মডেল কাজ না করে, তবে এটি ফলব্যাক হিসেবে কাজ করবে
        try:
            r = client.chat.completions.create(model="llama3-70b-8192", messages=messages, temperature=0.5)
            return r.choices[0].message.content.strip()
        except Exception as e2:
            return f"Error: {e2}"

# ============================================================
# 🎨 PREMIUM CSS (ChatGPT Voice UI + Fixed Light Theme)
# ============================================================
if dark:
    bg_base = "#0e1117"
    bg_gradient = "radial-gradient(circle at 50% 0%, #1f1e2e 0%, #0e1117 80%)"
    txt = "#fafafa"
    sidebar_bg = "#0e1117"
    chat_input_bg = "rgba(38, 39, 48, 0.8)" 
    btn_bg = "#262730"
    btn_txt = "#fafafa"
    border_col = "rgba(255,255,255,0.1)"
    glass_bg = "rgba(255, 255, 255, 0.05)"
    watermark_opacity = "0.08"
    radio_bg = "#262730"
    radio_border = "#ffffff"
else:
    # ☀️ Dreamy Pastel Light Theme
    bg_base = "#ffffff"
    bg_gradient = "linear-gradient(135deg, #FFFDFB 0%, #FFF0F5 50%, #F0F8FF 100%)"
    txt = "#1a1a1a" 
    sidebar_bg = "rgba(255, 255, 255, 0.6)"
    chat_input_bg = "rgba(255, 255, 255, 0.95)" 
    btn_bg = "rgba(255, 255, 255, 0.9)" 
    btn_txt = "#1a1a1a" 
    border_col = "rgba(0,0,0,0.1)" 
    glass_bg = "rgba(255, 255, 255, 0.7)" 
    watermark_opacity = "0.08"
    radio_bg = "#ffffff"
    radio_border = "#f97316"

css = f"""
<style>
    /* 🌟 Premium Colorful Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div {{
        background: {bg_gradient} !important;
    }}

    /* 🌟 Watermark */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: 600px; height: 600px;
        background-image: url('https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png');
        background-size: contain;
        background-repeat: no-repeat;
        opacity: {watermark_opacity};
        z-index: 0;
        pointer-events: none;
    }}

    .main .block-container {{ 
        padding-top: 1.5rem; 
        max-width: 900px; 
        padding-bottom: 150px !important; 
        z-index: 1;
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{ 
        background: {sidebar_bg} !important; 
        backdrop-filter: blur(15px) !important;
        border-right: 1px solid {border_col} !important;
    }}
    
    /* Text Colors */
    .main p, .main span, .main label, .main h1, .main h2, .main h3, .main h4, .main h5, .main h6, .main li, .main td, .main th,
    [data-testid="stChatMessage"] *, [data-testid="stMarkdownContainer"] *,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{ color: {txt} !important; }}

    /* 💎 Glassmorphism Chat Bubbles */
    [data-testid="stChatMessage"] {{
        background: {glass_bg} !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid {border_col} !important;
        border-radius: 15px !important;
        padding: 15px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03) !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: flex-start !important;
    }}

    /* 🔥 User Message Right Align */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
        flex-direction: row-reverse !important;
        background: rgba(249, 115, 22, 0.1) !important; 
        border-color: rgba(249, 115, 22, 0.3) !important;
    }}
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {{
        text-align: right !important;
    }}
    
    /* Header */
    .header {{ background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important; padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem; display: flex; align-items: center; overflow: hidden; box-shadow: 0 8px 20px rgba(239, 68, 68, 0.2); }}
    .header h1 {{ margin: 0; font-size: 1.8rem; color: #ffffff !important; }}
    .header p {{ margin: 0.3rem 0 0; opacity: 0.95; font-size: 0.95rem; color: #ffffff !important; }}
    
    /* 🐝 Animated Logo */
    @keyframes talk {{
        0% {{ transform: translateY(0px) scale(1); filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.3)); }}
        50% {{ transform: translateY(-8px) scale(1.05); filter: drop-shadow(0 0 25px rgba(249, 115, 22, 0.8)); }}
        100% {{ transform: translateY(0px) scale(1); filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.3)); }}
    }}
    .logo-3d {{ animation: talk 3s ease-in-out infinite; border-radius: 50%; mix-blend-mode: multiply; max-height: 80px; object-fit: contain; }}
    
    /* Buttons */
    .stButton > button {{
        background-color: {btn_bg} !important;
        color: {btn_txt} !important;
        border: 1px solid {border_col} !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        transition: all 0.2s !important;
    }}
    .stButton > button:hover {{
        border-color: #f97316 !important;
        color: #f97316 !important;
    }}
    .stButton > button p, .stButton > div {{
        color: {btn_txt} !important;
    }}

    /* 🔥 Streamlit Radio Button Fix (White & Orange) */
    [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {{
        background-color: {radio_bg} !important;
        border: 2px solid {radio_border} !important;
    }}
    [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child > div {{
        background-color: #f97316 !important;
        transform: scale(1.2) !important;
    }}

    /* 🔥 Voice Input Fix (Remove Black Box) */
    [data-testid="stAudioInput"] {{
        background-color: #ffffff !important;
        border-radius: 12px !important;
        border: 2px solid #f97316 !important;
        box-shadow: 0 4px 15px rgba(249, 115, 22, 0.15) !important;
        padding: 10px !important;
    }}
    [data-testid="stAudioInput"] * {{
        color: #1a1a1a !important;
        fill: #f97316 !important;
    }}
    [data-testid="stAudioInput"] button {{
        background-color: #f97316 !important;
        color: white !important;
        border: none !important;
    }}
    [data-testid="stAudioInput"] button svg {{
        fill: white !important;
        color: white !important;
    }}

    /* Input Box */
    [data-testid="stChatInput"] {{
        position: fixed !important; bottom: 20px !important; left: 21rem !important; right: 2rem !important;
        z-index: 999 !important; max-width: 900px !important;
        background: {chat_input_bg} !important; backdrop-filter: blur(15px) !important;
        border: 2px solid #f97316 !important; border-radius: 25px !important; padding: 5px 10px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08) !important;
    }}
    [data-testid="stChatInput"] > div {{ background-color: transparent !important; }}
    [data-testid="stChatInput"] textarea {{ background-color: transparent !important; color: {txt} !important; padding-right: 80px !important; }}
    [data-testid="stChatInput"] button {{ background-color: #f97316 !important; color: white !important; border-radius: 50% !important; }}

    /* Hide default Streamlit UI */
    [data-testid="stBottom"] > div {{ background: transparent !important; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    [data-testid="stHeader"] {{ background: transparent !important; z-index: 999; }}
    .stDeployButton {{display: none !important;}}
    
    /* Sidebar Toggle Arrow */
    [data-testid="collapsedControl"] {{
        display: flex !important; visibility: visible !important; opacity: 1 !important;
        position: fixed !important; top: 15px !important; left: 15px !important; z-index: 99999 !important;
        background-color: #f97316 !important; color: white !important;
        border-radius: 50% !important; padding: 8px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    }}
    [data-testid="collapsedControl"] svg {{ fill: white !important; color: white !important; }}
    
    /* Emoji Popover */
    [data-testid="stPopover"] > button {{
        background-color: {btn_bg} !important; color: {btn_txt} !important;
        border: 1px solid {border_col} !important; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
    }}
    [data-testid="stPopoverBody"] {{
        background-color: #ffffff !important; border: 1px solid {border_col} !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1) !important;
    }}

    /* 🎤 ChatGPT-Style Voice UI Card */
    .voice-card {{
        background: {glass_bg};
        backdrop-filter: blur(25px);
        border-radius: 30px;
        padding: 50px 20px;
        text-align: center;
        box-shadow: 0 15px 50px rgba(0,0,0,0.1);
        border: 2px solid rgba(249, 115, 22, 0.3);
        margin-top: 5vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ============================================================
# 🎤 VOICE UI (Full Screen Interface)
# ============================================================
if st.session_state.voice_ui:
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
                            if st.session_state.chat_id is None:
                                new_chat()
                                
                            # Save User Message
                            add_msg(st.session_state.chat_id, "user", user_msg)
                            
                            # Get AI Reply
                            current_chat = get_chat(st.session_state.chat_id)
                            history = current_chat["messages"][:-1]
                            reply = ask_llm(user_msg, history)
                            
                            # Save AI Reply
                            add_msg(st.session_state.chat_id, "bee", reply)
                            
                            # Speak the reply
                            speak_text(reply)
                            
                            # Close Voice UI and go back to chat
                            st.session_state.voice_ui = False
                            st.rerun()
                else:
                    st.warning("Please record something first.")
        with btn_col2:
            if st.button("❌ Close", use_container_width=True):
                st.session_state.voice_ui = False
                st.rerun()
                
    st.stop() # Stop rendering normal chat while in voice UI

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    st.caption(f"👤 **{st.session_state.username}**")
    
    if st.button("🚪 Logout", use_container_width=True):
        cookie_manager.delete("bee_user")
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
        
    st.divider()
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
    st.divider()
    
    if st.session_state.is_premium:
        st.success("🌟 PRO User (Unlimited Lifetime)")
    else:
        st.info(f"💬 আজকের ফ্রি মেসেজ বাকি: {DAILY_LIMIT - st.session_state.msg_count}/{DAILY_LIMIT}")
        
    st.divider()
    
    # 🎤 New Voice Mode Button
    if st.button("🎤 Start Voice Chat", use_container_width=True):
        st.session_state.voice_ui = True
        st.rerun()
                
    # 😊 Emoji Picker
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

if not cur["messages"]:
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{st.session_state.username}**! I'm {NAME} — your personal AI. How can I help you today? 😊")
else:
    for m in cur["messages"]:
        with st.chat_message(m["role"]): 
            st.markdown(m["content"])

# ============ INPUT AREA ============
user_message = None
file_context = ""

# Premium Paywall
if (not st.session_state.is_premium) and (st.session_state.msg_count >= DAILY_LIMIT):
    st.warning("⚠️ আপনার আজকের ফ্রি মেসেজ লিমিট শেষ!")
    with st.container(border=True):
        st.markdown("### 💎 Lifetime Pro — Unlimited Access")
        st.markdown(f"**পেমেন্ট:** মাত্র **৫০০ টাকা (≈ $4.99)** | 📱 **bKash:** `{BKASH_NUMBER}`")
        
        col1, col2 = st.columns(2)
        with col1: user_trx = st.text_input("TrxID (যেমন: 9F5A2B1C)")
        with col2: unlock_input = st.text_input("Unlock Code", type="password")
            
        if st.button("🔓 Unlock Lifetime Pro", use_container_width=True, type="primary"):
            if unlock_input == CODE_LIFETIME:
                supabase.table("users").update({"is_premium": True}).eq("username", st.session_state.username).execute()
                st.session_state.is_premium = True
                st.success("🎉 অভিনন্দন! আপনি এখন Lifetime Pro ইউজার।")
                time.sleep(1); st.rerun()
            elif unlock_input != "":
                st.error("❌ ভুল আনলক কোড!")
else:
    # Text Input Only
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

# ============ HANDLE TEXT INPUT ============
if user_message:
    if not st.session_state.is_premium:
        st.session_state.msg_count += 1
        supabase.table("users").update({"msg_count": st.session_state.msg_count}).eq("username", st.session_state.username).execute()
        
    add_msg(st.session_state.chat_id, "user", user_message)
    with st.chat_message("user"): 
        st.markdown(user_message)

    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        with st.spinner("Bee is thinking..."):
            current_chat = get_chat(st.session_state.chat_id)
            history = current_chat["messages"][:-1]
            reply = ask_llm(user_message, history, file_context)
        st.markdown(reply)
        
    add_msg(st.session_state.chat_id, "bee", reply)
    st.rerun()
