"""Bee - Ultimate AI Assistant (ChatGPT Style UI, Transformer Voice, File)"""

import streamlit as st
import json
import uuid
import datetime
import sys
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

st.set_page_config(page_title="Bee AI", page_icon="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png", layout="wide")

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

if "logged_in" not in st.session_state: st.session_state.logged_in = True
if "username" not in st.session_state: st.session_state.username = "Guest"
if "theme" not in st.session_state: st.session_state.theme = "dark"
if "chat_id" not in st.session_state: st.session_state.chat_id = None

# ============ INTRO ANIMATION ============
if "intro_done" not in st.session_state: st.session_state.intro_done = False
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

# ============ STORAGE ============
def load_chats():
    if CHATS_FILE.exists():
        try: return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
        except Exception: pass
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
        except Exception: _groq = None
    return _groq

# ============ HELPERS (TRANSFORMER VOICE) ============
def speak_text(text):
    st.toast("🤖 Transformer Bee কথা বলছে...")
    js_text = json.dumps(text)
    js_code = f"""
    <script>
        var msg = new SpeechSynthesisUtterance({js_text});
        msg.lang = 'bn-BD'; 
        msg.pitch = 0.1;    
        msg.rate = 0.85;    
        msg.volume = 1.0;
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
            file=("voice.wav", audio_bytes), 
            model="whisper-large-v3-turbo", 
            response_format="text"
        )
        return transcription.strip()
    except Exception as e:
        st.error(f"❌ ভয়েস বুঝতে সমস্যা: {e}"); return None

def search_web(query):
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, max_results=4)
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
    web_context = ""
    if any(w in prompt.lower() for w in ["search", "who is", "news", "খবর", "কে", "কি", "current", "today"]):
        with st.spinner("🌐 ইন্টারনেটে খুঁজছি..."):
            web_context = search_web(prompt.lower().replace("search", "").strip())

    sys_prompt = f"""You are {NAME}, a helpful AI. {file_context} \n Web: {web_context}
Rules: Reply in the same language as the user. Be detailed. Use Web Context if provided. Never say you can't search."""

    client = get_groq()
    if not client: return "API Key নেই।"
    
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in chat_history:
        if isinstance(msg, dict) and msg.get("content", "").strip():
            role = "assistant" if msg.get("role") in ["bee", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(model="openai/gpt-oss-120b", messages=messages, temperature=0.3)
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# ============ THEME SETUP ============
dark = st.session_state.theme == "dark"
if dark:
    bg = "#0e1117"
    txt = "#fafafa"
    sidebar_bg = "#0e1117"
    chat_input_bg = "rgba(30, 30, 30, 0.8)"
    chat_input_border = "rgba(249, 115, 22, 0.5)"
    header_bg = "#0e1117"
    btn_bg = "#262730"
    btn_txt = "#fafafa"
    border_col = "#3a3d45"
    mic_col = "#a3a3a3"
else:
    bg = "#ffffff"
    txt = "#1a1a1a"
    sidebar_bg = "#f8f9fa"
    chat_input_bg = "rgba(255, 255, 255, 0.95)"
    chat_input_border = "rgba(249, 115, 22, 0.8)"
    header_bg = "#ffffff"
    btn_bg = "#e9ecef"
    btn_txt = "#1a1a1a"
    border_col = "#ced4da"
    mic_col = "#6c757d"

css = """
<style>
    /* Force ALL backgrounds */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: BG_COLOR !important; }
    [data-testid="stSidebar"] { background: SIDEBAR_BG !important; }
    
    /* Force text colors */
    .main p, .main span, .main label, .main h1, .main h2, .main h3, .main div, 
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: TXT_COLOR !important; 
    }
    
    /* Top native header icons */
    [data-testid="stHeader"] svg { fill: TXT_COLOR !important; stroke: TXT_COLOR !important; }

    .main .block-container { padding-top: 1.5rem; max-width: 900px; padding-bottom: 150px !important; }
    
    /* Header Gradient */
    .header { background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important; padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem; display: flex; align-items: center; overflow: hidden; }
    .header h1 { margin: 0; font-size: 1.8rem; color: #ffffff !important; }
    .header p { margin: 0.3rem 0 0; opacity: 0.95; font-size: 0.95rem; color: #ffffff !important; }
    
    @keyframes float { 0% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); } 50% { transform: translateY(-8px); filter: drop-shadow(0px 20px 25px rgba(0,0,0,1)); } 100% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); } }
    .logo-3d { animation: float 4s ease-in-out infinite; border-radius: 50%; mix-blend-mode: screen; max-height: 80px; object-fit: contain; }

    /* Chat Messages */
    [data-testid="stChatMessage"] { background: transparent !important; }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span { color: TXT_COLOR !important; }

    /* Sidebar Buttons */
    .stButton > button {
        background: BTN_BG !important;
        color: BTN_TXT !important;
        border: 1px solid BORDER_COL !important;
    }
    .stButton > button p, .stButton > button div { color: BTN_TXT !important; }

    /* Glowing Orange Chat Input */
    @keyframes glow {
        0% { box-shadow: 0 0 5px rgba(249, 115, 22, 0.3); border-color: rgba(249, 115, 22, 0.3) !important; }
        50% { box-shadow: 0 0 15px rgba(249, 115, 22, 0.8); border-color: rgba(249, 115, 22, 0.8) !important; }
        100% { box-shadow: 0 0 5px rgba(249, 115, 22, 0.3); border-color: rgba(249, 115, 22, 0.3) !important; }
    }
    
    [data-testid="stChatInput"] {
        position: fixed !important; bottom: 20px !important; left: 21rem !important; right: 2rem !important;
        z-index: 999 !important; max-width: 900px !important;
        background: CHAT_INPUT_BG !important; 
        backdrop-filter: blur(15px) !important;
        border: 1px solid CHAT_INPUT_BORDER !important; 
        border-radius: 25px !important;
        animation: glow 3s infinite !important;
        padding: 5px 10px !important;
    }
    
    [data-testid="stChatInput"] textarea { 
        background: transparent !important; 
        color: TXT_COLOR !important;
        padding-right: 90px !important; 
    }

    /* Orange Send Button */
    [data-testid="stChatInput"] button {
        background-color: #f97316 !important; 
        color: white !important;
        border-radius: 50% !important;
        border: none !important;
    }

    /* 🔥 MIC BUTTON (Floating Inside Chat Bar) */
    [data-testid="stAudioInput"] {
        position: fixed !important;
        bottom: 26px !important; 
        right: 5.5rem !important; 
        z-index: 1000 !important;
        width: 40px !important;
        height: 40px !important;
        background: transparent !important;
        border: none !important;
    }
    
    /* Hide the complex elements of stAudioInput, keep only the button */
    [data-testid="stAudioInput"] > div { padding: 0 !important; background: transparent !important; }
    [data-testid="stAudioInput"] > div > div:not(:first-child) { display: none !important; }
    [data-testid="stAudioInput"] p { display: none !important; }

    /* Style the Mic Icon */
    [data-testid="stAudioInput"] button {
        background: transparent !important;
        color: MIC_COL !important;
        padding: 0 !important;
        border: none !important;
        box-shadow: none !important;
    }
    [data-testid="stAudioInput"] button svg {
        fill: MIC_COL !important;
        color: MIC_COL !important;
        width: 24px !important;
        height: 24px !important;
    }
    [data-testid="stAudioInput"] button:hover svg { fill: #f97316 !important; color: #f97316 !important; }

    footer { visibility: hidden; } #MainMenu { visibility: hidden; }

    @media (max-width: 768px) {
        .main .block-container { padding-bottom: 120px !important; }
        [data-testid="stChatInput"] { left: 1rem !important; right: 1rem !important; bottom: 10px !important; }
        [data-testid="stAudioInput"] { bottom: 16px !important; right: 4.5rem !important; }
    }
</style>
"""
css = css.replace("BG_COLOR", bg).replace("TXT_COLOR", txt).replace("SIDEBAR_BG", sidebar_bg).replace("CHAT_INPUT_BG", chat_input_bg).replace("CHAT_INPUT_BORDER", chat_input_border).replace("BTN_BG", btn_bg).replace("BTN_TXT", btn_txt).replace("BORDER_COL", border_col).replace("MIC_COL", mic_col)
st.markdown(css, unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    st.caption(f"👤 **Guest**")
    st.divider()
    uname = get_user_name()
    if uname: st.caption(f"Hi, **{uname}** 💕")
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
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
    theme = st.radio("Theme", ["🌙 Dark", "☀️ Light"], index=0 if dark else 1, horizontal=True, label_visibility="collapsed")
    new_t = "dark" if "Dark" in theme else "light"
    if new_t != st.session_state.theme: st.session_state.theme = new_t; st.rerun()
    st.divider()
    st.markdown("**👤 Your Name**")
    new_name = st.text_input("name_field", value=uname or "", label_visibility="collapsed")
    if st.button("💾 Save", use_container_width=True):
        if new_name and new_name.strip() != uname: set_user_name(new_name.strip()); st.rerun()

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
    else: new_chat(); st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None: new_chat(); st.rerun()

if not cur["messages"]:
    uname = get_user_name() or "friend"
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{uname}**! I'm {NAME} — your personal AI. How can I help you today? 😊")
else:
    for m in cur["messages"]:
        avatar = "👤" if m["role"] == "user" else "https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"
        with st.chat_message(m["role"], avatar=avatar): st.markdown(m["content"])

# ============ INPUT AREA ============
audio_value = st.audio_input("Voice Input", label_visibility="collapsed")
chat_data = st.chat_input("Type your message here...", accept_file=True, file_type=["pdf", "txt", "csv"])

user_message = None
file_context = ""

if chat_data:
    user_message = chat_data.text
    if chat_data.files:
        uploaded_file = chat_data.files[0]
        file_context = extract_text_from_file(uploaded_file)
        st.toast(f"📎 File '{uploaded_file.name}' attached!")
elif audio_value is not None:
    with st.spinner("🎤 আপনার কথা শোনা হচ্ছে..."):
        user_message = transcribe_audio(audio_value)
    if user_message:
        st.toast(f"🗣️ আপনি বলেছেন: {user_message}")

# ============ HANDLE INPUT ============
if user_message:
    add_msg(st.session_state.chat_id, "user", user_message)
    with st.chat_message("user", avatar="👤"): st.markdown(user_message)

    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        with st.spinner("Bee is thinking..."):
            current_chat = get_chat(st.session_state.chat_id)
            history = current_chat["messages"][:-1]
            reply = ask_llm(user_message, history, file_context)
        st.markdown(reply)
    
    speak_text(reply)
    add_msg(st.session_state.chat_id, "bee", reply)
    st.rerun()
