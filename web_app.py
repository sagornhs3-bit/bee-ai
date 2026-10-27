"""Bee - Ultimate AI Assistant (ChatGPT Style, Auto Theme, Image Gen)"""

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

# আপনার লোকাল মডিউল (যদি থাকে)
try:
    from memory import (get_user_name, set_user_name, build_memory_context,
                        remember, recall, get_all_facts)
except ImportError:
    # মেমোরি মডিউল না থাকলে বেসিক ফাংশন
    def get_user_name(): return "Guest"
    def set_user_name(name): pass

CONFIG_FILE = BEE_DIR / "config.json"
CHATS_FILE = BEE_DIR / "chats.json"

# পেজ কনফিগারেশন
st.set_page_config(
    page_title="Bee AI", 
    page_icon="https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png", 
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
if "theme" not in st.session_state: st.session_state.theme = "System"

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

# ============ ইমেজ জেনারেশন (নতুন ফিচার) ============
def generate_image(prompt):
    with st.spinner("🎨 ছবি তৈরি করা হচ্ছে, একটু অপেক্ষা করুন..."):
        try:
            # Pollinations.ai ব্যবহার করে ফ্রি ইমেজ জেনারেশন (কোনো API key লাগে না)
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                return response.content
            else:
                return None
        except Exception as e:
            st.error(f"ইমেজ তৈরি করতে সমস্যা: {e}")
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
    for msg in chat_history[-10:]: # শেষ ১০টি মেসেজ মনে রাখবে
        if isinstance(msg, dict) and msg.get("content", "").strip():
            role = "assistant" if msg.get("role") in ["bee", "assistant"] else "user"
            messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(model="llama3-70b-8192", messages=messages, temperature=0.4)
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# ============ অটোমেটিক থিম CSS ============
# Streamlit নেটিভভাবে থিম হ্যান্ডেল করে, আমরা শুধু চ্যাটবক্স সুন্দর করবো
st.markdown("""
<style>
    /* চ্যাট ইনপুটকে ChatGPT এর মতো ফ্লোটিং লুক দেওয়া */
    [data-testid="stChatInput"] {
        border-radius: 20px !important;
    }
    /* হেডার লোগো অ্যানিমেশন */
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
        100% { transform: translateY(0px); }
    }
    .logo-3d {
        animation: float 3s ease-in-out infinite;
        border-radius: 50%;
        max-height: 60px;
    }
    /* সাইডবারের বাটন স্টাইল */
    .stButton > button {
        border-radius: 10px !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ============ সাইডবার ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")
    uname = get_user_name()
    st.caption(f"👤 **{uname if uname else 'Guest'}**")
    st.divider()
    
    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat(); st.rerun()
    
    # ভয়েস মোড
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
    
    # হিস্ট্রি
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
    
    # ইউজার নেম
    new_name = st.text_input("Your Name", value=uname or "", placeholder="Enter your name")
    if st.button("💾 Save Name", use_container_width=True):
        if new_name and new_name.strip() != uname: 
            set_user_name(new_name.strip()); st.rerun()

# ============ মেইন চ্যাট এরিয়া ============
st.markdown(f"""
<div style="display: flex; align-items: center; margin-bottom: 2rem;">
    <img class="logo-3d" src="https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png" width="60" style="margin-right: 15px;">
    <div>
        <h1 style="margin: 0; font-size: 1.8rem;">{NAME} AI</h1>
        <p style="margin: 0; opacity: 0.7; font-size: 0.9rem;">Your Personal Assistant & Image Generator</p>
    </div>
</div>
""", unsafe_allow_html=True)

# নতুন চ্যাট শুরু
if st.session_state.chat_id is None:
    new_chat()
    st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None: 
    new_chat()
    st.rerun()

# মেসেজ ডিসপ্লে
if not cur["messages"]:
    uname = get_user_name() or "friend"
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{uname}**! I'm {NAME}. আপনি চাইলে আমার সাথে কথা বলতে পারেন, ফাইল আপলোড করতে পারেন, অথবা **'Draw a cat'** লিখে ছবি তৈরি করতে বলতে পারেন! 😊")
else:
    for m in cur["messages"]:
        avatar = "👤" if m["role"] == "user" else "https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png"
        with st.chat_message(m["role"], avatar=avatar): 
            # ইমেজ হলে ডিসপ্লে করা
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

    # চেক করা হচ্ছে ইউজার ছবি বানাতে চাচ্ছে কিনা
    is_image_request = any(kw in user_message.lower() for kw in ["image", "draw", "picture", "ছবি", "আঁকো", "generate"])
    
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/saghnhs3-bit/bee-ai/main/bumblebee.png"):
        if is_image_request:
            # ইমেজ জেনারেট করা
            img_data = generate_image(user_message)
            if img_data:
                st.image(img_data, caption=user_message, use_column_width=True)
                # চ্যাট হিস্ট্রিতে ইমেজ হিসেবে সেভ করা
                # (নোট: Streamlit এ সরাসরি ইমেজ সেভ করা কঠিন, তাই আমরা আপাতত স্ক্রিনে দেখাচ্ছি, চাইলে base64 এ সেভ করা যেতে পারে)
                add_msg(st.session_state.chat_id, "bee", f"Here is the image for: {user_message} (Generated)")
            else:
                st.error("দুঃখিত, ছবি তৈরি করা যায়নি। আবার চেষ্টা করুন।")
                add_msg(st.session_state.chat_id, "bee", "Image generation failed.")
        else:
            # টেক্সট রেসপন্স
            with st.spinner("Bee is thinking..."):
                current_chat = get_chat(st.session_state.chat_id)
                history = current_chat["messages"][:-1]
                reply = ask_llm(user_message, history, file_context)
            st.markdown(reply)
            speak_text(reply)
            add_msg(st.session_state.chat_id, "bee", reply)
    
    st.rerun()
