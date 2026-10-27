"""Bee - Ultimate AI Assistant (Fixed Animations, Auto Theme, Image Gen)"""

import streamlit as st
import json
import uuid
import datetime
import sys
import time
import urllib.parse
import requests
from pathlib import Path
import streamlit.components.v1 as components
import PyPDF2

# ডিরেক্টরি সেটআপ
BEE_DIR = Path(__file__).parent
sys.path.insert(0, str(BEE_DIR))

# আপনার লোকাল মডিউল
try:
    from memory import (get_user_name, set_user_name, build_memory_context,
                        remember, recall, get_all_facts)
except ImportError:
    def get_user_name(): return "Guest"
    def set_user_name(name): pass

CONFIG_FILE = BEE_DIR / "config.json"
CHATS_FILE = BEE_DIR / "chats.json"

st.set_page_config(
    page_title="Bee AI", 
    page_icon="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# কনফিগ লোড
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

# সেশন স্টেট
if "chat_id" not in st.session_state: st.session_state.chat_id = None
if "last_audio_hash" not in st.session_state: st.session_state.last_audio_hash = None
if "audio_key" not in st.session_state: st.session_state.audio_key = 0 
if "theme_choice" not in st.session_state: st.session_state.theme_choice = "⚙️ System"

# ============ সিস্টেম অটো থিম ডিটেকশন ============
sys_theme = "dark"
try:
    if hasattr(st, 'context') and hasattr(st.context, 'theme'):
        sys_theme = st.context.theme.type
except Exception:
    pass

if st.session_state.theme_choice == "⚙️ System":
    dark = (sys_theme == "dark")
elif st.session_state.theme_choice == "🌙 Dark":
    dark = True
else:
    dark = False

# ============ স্টোরেজ ফাংশন ============
def load_chats():
    if CHATS_FILE.exists():
        try: return json.loads(CHATS_FILE.read_text(encoding="utf-8"))
        except Exception: pass
    return {"chats": []}

def save_chats(data):
    CHATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def new_chat():
    data = load_chats()
    if data["chats"] and data["chats"][0]["title"] == "New Chat" and len(data["chats"][0]["messages"]) == 0:
        st.session_state.chat_id = data["chats"][0]["id"]
        return
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

# ============ হেল্পার ফাংশন ============
_groq = None
def get_groq():
    global _groq
    if _groq is None and GROQ_KEY.startswith("gsk_"):
        try:
            import groq
            _groq = groq.Groq(api_key=GROQ_KEY)
        except Exception: _groq = None
    return _groq

def speak_text(text):
    js_text = json.dumps(text)
    js_code = f"""
    <script>
        var msg = new SpeechSynthesisUtterance({js_text});
        msg.lang = 'bn-BD'; 
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
            file=("voice.wav", audio_bytes), model="whisper-large-v3-turbo", response_format="text"
        )
        return transcription.strip()
    except Exception as e:
        st.error(f"❌ ভয়েস বুঝতে সমস্যা: {e}"); return None

def extract_text_from_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in reader.pages])[:4000]
        elif uploaded_file.name.endswith(('.txt', '.csv')):
            return str(uploaded_file.read(), "utf-8")[:4000]
    except Exception: return ""
    return ""

# ============ ইমেজ জেনারেশন ============
def generate_image(prompt):
    with st.spinner("🎨 ছবি তৈরি করা হচ্ছে..."):
        try:
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None

# ============ AI লজিক ============
def ask_llm(prompt, chat_history, file_context=""):
    client = get_groq()
    if not client: return "API Key সঠিকভাবে সেট করা নেই।"
    
    sys_prompt = f"""You are {NAME}, a helpful AI assistant.
{file_context}
## Important Rules:
1. Reply in the EXACT same language the user uses.
2. NEVER use markdown headers (like #, ##, ###). Use plain text or bullet points only.
3. Keep the answer well-formatted but clean.
"""
    messages = [{"role": "system", "content": sys_prompt}]
    for msg in chat_history[-10:]:
        if isinstance(msg, dict) and msg.get("content", "").strip():
            role = "assistant" if msg.get("role") in ["bee", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(model="llama3-70b-8192", messages=messages, temperature=0.4)
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# ============ থিম কালার (অটো লাইট/ডার্ক) ============
if dark:
    bg = "#0e1117"; txt = "#fafafa"; sidebar_bg = "#0e1117"
    chat_input_bg = "#262730"; btn_bg = "#262730"; btn_txt = "#fafafa"; border_col = "#3a3d45"
else:
    bg = "#ffffff"; txt = "#1a1a1a"; sidebar_bg = "#f8f9fa"
    chat_input_bg = "#ffffff"; btn_bg = "#e9ecef"; btn_txt = "#1a1a1a"; border_col = "#ced4da"

# ============ CSS (আগের ডিজাইন ফিরিয়ে আনা হয়েছে) ============
css = f"""
<style>
    /* অটো থিমের জন্য ডাইনামিক ভেরিয়েবল */
    :root {{
        --bg-color: {bg};
        --txt-color: {txt};
        --sidebar-bg: {sidebar_bg};
        --btn-bg: {btn_bg};
        --btn-txt: {btn_txt};
        --border-col: {border_col};
    }}

    .stApp {{ background-color: var(--bg-color) !important; }}
    [data-testid="stSidebar"] {{ background-color: var(--sidebar-bg) !important; }}
    
    /* টেক্সট কালার ফিক্স */
    .main p, .main span, .main label, .main h1, .main h2, .main h3, .main h4, .main h5, .main h6, .main li, .main td, .main th,
    [data-testid="stChatMessage"] *, [data-testid="stMarkdownContainer"] *,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{
        color: var(--txt-color) !important; 
    }}

    /* সাইডবার বাটন কালো বক্স ফিক্স */
    [data-testid="stSidebar"] .stButton > button {{
        background-color: transparent !important;
        color: var(--txt-color) !important;
        border: 1px solid var(--border-col) !important;
        border-radius: 10px !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        border-color: #f97316 !important;
        color: #f97316 !important;
    }}

    /* ভয়েস মোডের কালো বক্স ফিক্স */
    [data-testid="stAudioInput"] {{
        background-color: transparent !important;
        border: 1px solid var(--border-col) !important;
        border-radius: 10px !important;
    }}
    [data-testid="stAudioInput"] > div {{
        background-color: transparent !important;
    }}

    /* লোগো অ্যানিমেশন (ভাঙা লিংক ফিক্স করা হয়েছে) */
    @keyframes float {{
        0% {{ transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.4)); }}
        50% {{ transform: translateY(-10px); filter: drop-shadow(0px 20px 25px rgba(0,0,0,0.6)); }}
        100% {{ transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.4)); }}
    }}
    .logo-3d {{
        animation: float 3s ease-in-out infinite;
        border-radius: 50%;
        max-height: 70px;
        object-fit: contain;
    }}

    /* হেডার গ্রেডিয়েন্ট */
    .header {{
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important;
        padding: 1.5rem; border-radius: 15px; margin-bottom: 2rem;
        display: flex; align-items: center; box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }}
    .header h1 {{ margin: 0; font-size: 2rem; color: #ffffff !important; }}
    .header p {{ margin: 0.3rem 0 0; color: #ffffff !important; opacity: 0.9; }}

    /* চ্যাট ইনপুট গ্লোয়িং ইফেক্ট (ChatGPT স্টাইল) */
    @keyframes glow {{
        0% {{ box-shadow: 0 0 5px rgba(249, 115, 22, 0.3); border-color: rgba(249, 115, 22, 0.3) !important; }}
        50% {{ box-shadow: 0 0 20px rgba(249, 115, 22, 0.8); border-color: rgba(249, 115, 22, 0.8) !important; }}
        100% {{ box-shadow: 0 0 5px rgba(249, 115, 22, 0.3); border-color: rgba(249, 115, 22, 0.3) !important; }}
    }}
    [data-testid="stChatInput"] {{
        position: fixed !important; bottom: 20px !important; left: 21rem !important; right: 2rem !important;
        z-index: 999 !important; max-width: 900px !important;
        background-color: {chat_input_bg} !important; 
        border: 2px solid #f97316 !important; border-radius: 25px !important; 
        animation: glow 3s infinite !important; padding: 5px 10px !important;
    }}
    [data-testid="stChatInput"] textarea {{
        background-color: transparent !important; color: var(--txt-color) !important; 
    }}
    [data-testid="stChatInput"] button {{
        background-color: #f97316 !important; color: white !important; border-radius: 50% !important;
    }}

    /* অন্যান্য বাটন স্টাইল */
    .stButton > button {{
        background-color: var(--btn-bg) !important; color: var(--btn-txt) !important; 
        border: 1px solid var(--border-col) !important; border-radius: 10px !important;
    }}
    
    @media (max-width: 1024px) {{ [data-testid="stChatInput"] {{ left: 2rem !important; right: 2rem !important; }} }}
    @media (max-width: 768px) {{ [data-testid="stChatInput"] {{ left: 1rem !important; right: 1rem !important; bottom: 10px !important; }} }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ============ সাইডবার ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    uname = get_user_name()
    st.caption(f"👤 **{uname if uname else 'Guest'}**")
    st.divider()
    
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
    
    st.markdown("**🎤 Voice Mode**")
    audio_value = st.audio_input("Record", label_visibility="collapsed", key=f"audio_{st.session_state.audio_key}")
    audio_to_process = None
    if audio_value is not None:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Send", use_container_width=True, type="primary"):
                audio_to_process = audio_value
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.audio_key += 1
                st.rerun()
    
    st.divider()
    
    st.markdown("**💬 History**")
    chats = load_chats()["chats"]
    if not chats: st.caption("No chats yet")
    for c in chats:
        col1, col2 = st.columns([5, 1])
        with col1:
            active = "🟢 " if c["id"] == st.session_state.chat_id else ""
            if st.button(f"{active}{c['title'][:20]}", key=f"c_{c['id']}", use_container_width=True):
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
        st.session_state.theme_choice = selected_theme
        st.rerun()

    st.divider()
    
    new_name = st.text_input("Your Name", value=uname or "", placeholder="Enter your name")
    if st.button("💾 Save Name", use_container_width=True):
        if new_name and new_name.strip() != uname: 
            set_user_name(new_name.strip()); st.rerun()

# ============ মেইন এরিয়া ============
st.markdown(f"""
<div class="header">
    <img class="logo-3d" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png" width="70" style="margin-right: 20px;">
    <div>
        <h1 style="margin: 0;">{NAME} AI</h1>
        <p style="margin: 0;">Your Personal Assistant & Image Generator</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.chat_id is None:
    new_chat()
    st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None: 
    new_chat()
    st.rerun()

if not cur["messages"]:
    uname = get_user_name() or "friend"
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{uname}**! I'm {NAME}. আপনি চাইলে আমার সাথে কথা বলতে পারেন, ফাইল আপলোড করতে পারেন, অথবা **'Draw a cat'** লিখে ছবি তৈরি করতে বলতে পারেন! 😊")
else:
    for m in cur["messages"]:
        avatar = "👤" if m["role"] == "user" else "https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"
        with st.chat_message(m["role"], avatar=avatar): 
            if m["content"].startswith("![IMAGE]"):
                img_url = m["content"].replace("![IMAGE]", "")
                st.image(img_url, use_column_width=True)
            else:
                st.markdown(m["content"])

# ============ ইনপুট বক্স ============
chat_data = st.chat_input("Message Bee AI or type 'Draw [something]'...", accept_file=True, file_type=["pdf", "txt", "csv"])

user_message = None
file_context = ""

if chat_data:
    user_message = chat_data.text
    if chat_data.files:
        uploaded_file = chat_data.files[0]
        file_context = extract_text_from_file(uploaded_file)
        st.toast(f"📎 File '{uploaded_file.name}' attached!")
        
elif audio_to_process is not None:
    audio_bytes = audio_to_process.getvalue()
    audio_hash = hash(audio_bytes)
    if st.session_state.last_audio_hash != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        user_message = transcribe_audio(audio_to_process)
        if user_message:
            st.toast(f"🗣️ আপনি বলেছেন: {user_message}")
            st.session_state.audio_key += 1 

# ============ ইনপুট প্রসেসিং ============
if user_message:
    add_msg(st.session_state.chat_id, "user", user_message)
    with st.chat_message("user", avatar="👤"): 
        st.markdown(user_message)

    is_image_request = any(kw in user_message.lower() for kw in ["image", "draw", "picture", "ছবি", "আঁকো", "generate"])
    
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        if is_image_request:
            img_data = generate_image(user_message)
            if img_data:
                st.image(img_data, caption=user_message, use_column_width=True)
                add_msg(st.session_state.chat_id, "bee", f"Here is the image for: {user_message} (Generated)")
            else:
                st.error("দুঃখিত, ছবি তৈরি করা যায়নি। আবার চেষ্টা করুন।")
                add_msg(st.session_state.chat_id, "bee", "Image generation failed.")
        else:
            with st.spinner("Bee is thinking..."):
                current_chat = get_chat(st.session_state.chat_id)
                history = current_chat["messages"][:-1]
                reply = ask_llm(user_message, history, file_context)
            st.markdown(reply)
            speak_text(reply)
            add_msg(st.session_state.chat_id, "bee", reply)
    
    st.rerun()
