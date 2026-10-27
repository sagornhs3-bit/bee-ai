"""Bee - Ultimate AI Assistant (Voice, Search, File Upload, Multi-lang)"""

import streamlit as st
import json
import uuid
import datetime
import sys
import os
import time
from pathlib import Path
import streamlit.components.v1 as components
import PyPDF2

BEE_DIR = Path(__file__).parent
sys.path.insert(0, str(BEE_DIR))

from memory import (get_user_name, set_user_name, build_memory_context,
                    remember, recall, get_all_facts)

CONFIG_FILE = BEE_DIR / "config.json"
CHATS_FILE = BEE_DIR / "chats.json"

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="Bee AI",
    page_icon="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png",
    layout="wide"
)

# ============ CONFIG LOADER ============
def load_cfg():
    try:
        if hasattr(st, 'secrets') and "config" in st.secrets:
            return dict(st.secrets["config"])
    except Exception:
        pass
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"groq_api_key": ""}

CONFIG = load_cfg()
NAME = CONFIG.get("assistant_name", "Bee")
GROQ_KEY = CONFIG.get("groq_api_key", "")

# ============ SESSION STATE ============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
if "username" not in st.session_state:
    st.session_state.username = "Guest"
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

# ============ INTRO ANIMATION ============
if "intro_done" not in st.session_state:
    st.session_state.intro_done = False

if not st.session_state.intro_done:
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
        [data-testid="stSidebar"] {display: none;} .block-container {padding: 0 !important;}
        .splash-screen {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: #0e1117; display: flex; flex-direction: column;
            justify-content: center; align-items: center; z-index: 99999;
        }
        .splash-logo { width: 150px; animation: zoomPulse 2s infinite alternate; mix-blend-mode: screen; }
        @keyframes zoomPulse {
            0% { transform: scale(0.9); filter: drop-shadow(0 0 10px #f59e0b); }
            100% { transform: scale(1.1); filter: drop-shadow(0 0 30px #ef4444); }
        }
        .splash-text { color: white; margin-top: 20px; font-family: sans-serif; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="splash-screen">
        <img class="splash-logo" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png">
        <h2 class="splash-text">BEE AI</h2>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    st.session_state.intro_done = True
    st.rerun()

# ============ STORAGE & HELPERS ============
def load_chats():
    if CHATS_FILE.exists():
        try:
            return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"chats": []}

def save_chats(data):
    CHATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def new_chat():
    data = load_chats()
    cid = str(uuid.uuid4())[:8]
    data["chats"].insert(0, {"id": cid, "title": "New Chat", "time": datetime.datetime.now().strftime("%m-%d %H:%M"), "messages": []})
    save_chats(data)
    st.session_state.chat_id = cid

def get_chat(cid):
    for c in load_chats()["chats"]:
        if c["id"] == cid: return c
    return None

def add_msg(cid, role, content):
    data = load_chats()
    for c in data["chats"]:
        if c["id"] == cid:
            c["messages"].append({"role": role, "content": content})
            if role == "user" and c["title"] == "New Chat":
                c["title"] = content[:28] + ("..." if len(content) > 28 else "")
            break
    save_chats(data)

def del_chat(cid):
    data = load_chats()
    data["chats"] = [c for c in data["chats"] if c["id"] != cid]
    save_chats(data)

_groq = None
def get_groq():
    global _groq
    if _groq is None and GROQ_KEY.startswith("gsk_"):
        try:
            import groq
            _groq = groq.Groq(api_key=GROQ_KEY)
        except Exception:
            _groq = None
    return _groq

# ============ VOICE & SEARCH HELPERS ============
def speak_text(text):
    js_text = json.dumps(text)
    js_code = f"""
    <script>
        var msg = new SpeechSynthesisUtterance({js_text});
        msg.lang = 'auto'; // ব্রাউজার নিজেই ভাষা বুঝে নেবে
        msg.rate = 1.0;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

def transcribe_audio(audio_file):
    client = get_groq()
    if not client or not audio_file:
        return None
    try:
        transcription = client.audio.transcriptions.create(
            file=("audio.wav", audio_file.read()),
            model="whisper-large-v3-turbo",
            language="bn", # বাংলা ভয়েসের জন্য
            response_format="text"
        )
        return transcription.strip()
    except Exception as e:
        st.error(f"Voice Error: {e}")
        return None

def search_web(query):
    try:
        from duckduckgo_search import DDGS
        # ডিপ সার্চ: টপ ৫টি রেজাল্ট নেওয়া হচ্ছে
        results = DDGS().text(query, max_results=5)
        if not results: return "No search results found."
        formatted = ""
        for i, res in enumerate(results):
            formatted += f"\n[Result {i+1}]: {res['title']}\n{res['body']}\n"
        return formatted
    except Exception as e:
        return f"Search error: {e}"

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text[:4000] # প্রথম ৪০০০ অক্ষর
    elif uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.csv'):
        return str(uploaded_file.read(), "utf-8")[:4000]
    return ""

# ============ AI LOGIC ============
def build_sys(file_context=""):
    mem = build_memory_context()
    mem_block = f"\n\nUser info:\n{mem}\n" if mem else ""
    file_block = f"\n\n## Attached File Context:\n{file_context}\n" if file_context else ""
    
    return f"""You are {NAME} — a highly intelligent, helpful, and empathetic AI assistant.
You have real-time internet search capability and can read attached files.
{mem_block}{file_block}

## Rules:
1. **Language:** You MUST reply in the EXACT same language the user uses. If they write in Bengali, reply in Bengali. If English, reply in English.
2. **Web Search:** You HAVE internet access. If Web Context is provided, use it to answer accurately. NEVER say "I don't have web search".
3. **Files:** If file context is provided, read it carefully to answer the user's question.
4. **Detail:** Give detailed, well-structured answers. Use bullet points if needed.
"""

def ask_llm(prompt, chat_history, file_context=""):
    web_context = ""
    # সার্চ ট্রিগার
    search_triggers = ["search", "who is", "news", "ke", "ki", "kobe", "koto", "খবর", "কে", "কি", "কবে", "কত", "current", "today"]
    if any(w in prompt.lower() for w in search_triggers):
        with st.spinner("🌐 আমি ইন্টারনেটে ডিপ সার্চ করছি..."):
            clean_query = prompt.lower().replace("search", "").strip()
            web_context = search_web(clean_query)

    sys_prompt = build_sys(file_context) + f"\n\n## Web Search Context:\n{web_context}\n"
    client = get_groq()
    
    if not client:
        return "দুঃখিত, Groq API Key সেট করা নেই।"
    
    # চ্যাট হিস্ট্রি তৈরি (Indentation Error Free)
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in chat_history:
        role = "assistant" if msg["role"] == "bee" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.3,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq Error: {e}"

def route(text):
    t = text.lower()
    try:
        if any(w in t for w in ["time", "কয়টা বাজে", "somoy"]):
            from plugins import system
            return system.get_time()
        if any(w in t for w in ["date", "আজকের তারিখ", "tarikh"]):
            from plugins import system
            return system.get_date()
        if any(w in t for w in ["weather", "আবহাওয়া", "abohawa"]):
            from plugins import weather
            return weather.get_weather()
    except Exception:
        pass
    return None

# ============ CSS ============
dark = st.session_state.theme == "dark"
bg = "#0e1117" if dark else "#ffffff"
txt = "#fafafa" if dark else "#1a1a1a"
sidebar_bg = "#0e1117" if dark else "#f7f9fc"

css = """
<style>
    .stApp { background: BG_COLOR !important; }
    [data-testid="stSidebar"] { background: SIDEBAR_BG !important; }
    
    .main p, .main span, .main label, .main h1, .main h2, .main h3 {
        color: TXT_COLOR !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: TXT_COLOR !important;
    }
    
    .main .block-container { padding-top: 1.5rem; max-width: 900px; padding-bottom: 220px !important; }
    
    .header {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important;
        padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem;
        display: flex; align-items: center;
    }
    .header h1 { margin: 0; font-size: 1.8rem; color: #ffffff !important; }
    .header p { margin: 0.3rem 0 0; opacity: 0.95; font-size: 0.95rem; color: #ffffff !important; }
    
    /* 3D Logo */
    @keyframes float {
        0% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); }
        50% { transform: translateY(-8px); filter: drop-shadow(0px 20px 25px rgba(0,0,0,1)); }
        100% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); }
    }
    .logo-3d { animation: float 4s ease-in-out infinite; border-radius: 50%; mix-blend-mode: screen; }

    [data-testid="stChatMessage"] { background: transparent !important; }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span { color: TXT_COLOR !important; }

    /* Glassmorphism Chat Input */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 20px !important;
        left: 21rem !important;
        right: 2rem !important;
        z-index: 999 !important;
        max-width: 900px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5) !important;
        padding: 5px 15px !important;
    }
    
    /* Voice & File Input Styling */
    [data-testid="stAudioInput"] {
        background: rgba(30, 30, 30, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px !important;
        padding: 10px !important;
        margin-bottom: 10px !important;
    }

    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    @media (max-width: 768px) {
        .main .block-container { padding-top: 1rem; padding-bottom: 250px !important; }
        [data-testid="stChatInput"] {
            position: fixed !important; left: 1rem !important; right: 1rem !important; bottom: 10px !important; max-width: 100% !important; width: auto !important;
        }
    }
</style>
"""
css = css.replace("BG_COLOR", bg).replace("TXT_COLOR", txt).replace("SIDEBAR_BG", sidebar_bg)
st.markdown(css, unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    st.caption(f"👤 **Guest**")
    
    st.divider()
    uname = get_user_name()
    if uname: st.caption(f"Hi, **{uname}** 💕")

    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.divider()
    st.markdown("**💬 History**")
    chats = load_chats()["chats"]
    if not chats: st.caption("No chats yet")
    
    for c in chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            active = "🟢 " if c["id"] == st.session_state.chat_id else ""
            if st.button(f"{active}{c['title'][:22]}", key=f"c_{c['id']}", use_container_width=True):
                st.session_state.chat_id = c["id"]
                st.rerun()
        with col2:
            if st.button("✕", key=f"d_{c['id']}"):
                del_chat(c["id"])
                if st.session_state.chat_id == c["id"]: st.session_state.chat_id = None
                st.rerun()

    st.divider()
    st.markdown("**🎨 Theme**")
    theme = st.radio("Theme", ["🌙 Dark", "☀️ Light"], index=0 if dark else 1, horizontal=True, label_visibility="collapsed")
    new_t = "dark" if "Dark" in theme else "light"
    if new_t != st.session_state.theme:
        st.session_state.theme = new_t
        st.rerun()

    st.divider()
    st.markdown("**👤 Your Name**")
    new_name = st.text_input("name_field", value=uname or "", label_visibility="collapsed")
    if st.button("💾 Save", use_container_width=True):
        if new_name and new_name.strip() != uname:
            set_user_name(new_name.strip())
            st.rerun()

# ============ MAIN ============
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
    chats = load_chats()["chats"]
    if chats: st.session_state.chat_id = chats[0]["id"]
    else:
        new_chat()
        st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None:
    new_chat()
    st.rerun()

# Display Messages
if not cur["messages"]:
    uname = get_user_name() or "friend"
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{uname}**! I'm {NAME} — your personal AI. How can I help you today? 😊")
else:
    for m in cur["messages"]:
        avatar = "👤" if m["role"] == "user" else "https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])

# ============ INPUT AREA ============
# ফাইল আপলোড
uploaded_file = st.file_uploader("📎 Attach a file (PDF, TXT, CSV)", type=["pdf", "txt", "csv"], label_visibility="collapsed")
file_context = ""
if uploaded_file is not None:
    with st.spinner("Reading file..."):
        file_context = extract_text_from_file(uploaded_file)
        st.success(f"File '{uploaded_file.name}' attached. Ask me anything about it!")

# ভয়েস ইনপুট
st.markdown("**🎤 Voice Input (মাইকে কথা বলুন)**")
audio_value = st.audio_input("Record your voice", label_visibility="collapsed")

# চ্যাট ইনপুট
user_in = st.chat_input("Type your message here...")

# ============ HANDLE INPUT (Voice or Text) ============
user_message = None

if user_in and user_in.strip():
    user_message = user_in.strip()
elif audio_value is not None:
    with st.spinner("🎤 আপনার কথা শোনা হচ্ছে..."):
        user_message = transcribe_audio(audio_value)

if user_message:
    add_msg(st.session_state.chat_id, "user", user_message)
    
    # UI-তে ইউজারের মেসেজ দেখানো
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_message)

    # AI-এর রেসপন্স
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        with st.spinner("Bee is thinking..."):
            current_chat = get_chat(st.session_state.chat_id)
            history = current_chat["messages"][:-1]
            
            action_result = route(user_message)
            if action_result:
                reply = action_result
            else:
                reply = ask_llm(user_message, history, file_context)
                
        st.markdown(reply)
    
    speak_text(reply)
    add_msg(st.session_state.chat_id, "bee", reply)
    st.rerun()
