"""Bee - Web Chat with Login + Multi-language + Light/Dark Theme"""

from openai import OpenAI
from duckduckgo_search import DDGS
import streamlit as st
import streamlit.components.v1 as components
import json
import uuid
import datetime
import sys
from pathlib import Path

BEE_DIR = Path(__file__).parent
sys.path.insert(0, str(BEE_DIR))

from memory import (get_user_name, set_user_name, build_memory_context,
                    remember, recall, get_all_facts)
import auth

CONFIG_FILE = BEE_DIR / "config.json"
CHATS_FILE = BEE_DIR / "chats.json"

LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧"},
    "bn": {"name": "বাংলা", "flag": "🇧🇩"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳"},
    "es": {"name": "Español", "flag": "🇪🇸"},
    "ar": {"name": "العربية", "flag": "🇸🇦"},
}


def load_cfg():
    # Try Streamlit Secrets first (for Cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and "config" in st.secrets:
            return dict(st.secrets["config"])
    except Exception:
        pass

    # Fallback to local config.json
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "assistant_name": "Bee",
            "mode": "auto",
            "default_language": "en",
            "groq_api_key": "",
            "ollama_model": "llama3.2:3b",
            "whisper_model": "small",
            "whisper_language": "en",
            "tts_voice_english": "en-US-JennyNeural",
            "tts_voice_bengali": "bn-BD-NabanitaNeural",
            "tts_rate": "+0%",
            "tts_pitch": "+0Hz",
            "tts_volume": "+5%",
            "push_to_talk_key": "ctrl+alt+b",
            "exit_key": "ctrl+alt+q",
            "memory_enabled": True,
            "reply_language": "en",
            "log_conversations": True,
        }


def save_cfg(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


CONFIG = load_cfg()
NAME = CONFIG.get("assistant_name", "Bee")
GROQ_KEY = CONFIG.get("groq_api_key", "")
OLLAMA_MODEL = CONFIG.get("ollama_model", "llama3.2:3b")


def get_lang_pref():
    return load_cfg().get("reply_language", "en")


def set_lang_pref(lang):
    c = load_cfg()
    c["reply_language"] = lang
    save_cfg(c)


st.set_page_config(
    page_title=f"{NAME} AI", 
    page_icon="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png", 
    layout="wide"
)

# ============ SESSION STATE SETUP ============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
if "ai_engine" not in st.session_state:
    st.session_state.ai_engine = "Groq"  # ডিফল্ট মডেল
# ==============================================

# ============ LOGIN ============
def show_login_page():
    st.markdown("""
    <style>
        .stApp { background: #0e1117; }
        .login-logo { text-align: center; font-size: 4rem; margin-top: 4rem; margin-bottom: 0.5rem; }
        .login-title { text-align: center; font-size: 2.2rem; font-weight: 700; color: #fff; margin-bottom: 0.3rem; }
        .login-sub { text-align: center; color: #888; margin-bottom: 2rem; font-size: 0.95rem; }
        .login-hint { text-align: center; color: #666; font-size: 0.82rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #2a2d36; }
        .header h1 { font-size: 1.5rem !important; }
        .header p { font-size: 0.8rem !important; }
    }   

        /* 3D Floating Logo Effect */
    @keyframes float {
        0% { transform: translateY(0px) rotate(0deg); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.6)); }
        50% { transform: translateY(-10px) rotate(2deg); filter: drop-shadow(0px 20px 25px rgba(0,0,0,0.8)); }
        100% { transform: translateY(0px) rotate(0deg); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.6)); }
    }
    /* 3D Floating Logo Effect for Main Page */
    @keyframes float {
        0% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); }
        50% { transform: translateY(-8px); filter: drop-shadow(0px 20px 25px rgba(0,0,0,1)); }
        100% { transform: translateY(0px); filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.8)); }
    }
    .logo-3d {
        animation: float 4s ease-in-out infinite;
        border-radius: 50%;
        mix-blend-mode: screen; /* লোগোর কালো ব্যাকগ্রাউন্ড মিশিয়ে দেবে */
    }
    
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div style="text-align: center; margin-top: 3rem; margin-bottom: 1rem;"><img src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png" width="120"></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Bee AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sign in to continue</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("🔓 Sign In", use_container_width=True, type="primary")

            if submit:
                if auth.verify_login(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

        st.markdown('<div class="login-hint">Default: <b>admin</b> / <b>bee2026</b></div>', unsafe_allow_html=True)

# অটোমেটিক লগইন (কেউ লিংকে ক্লিক করলেই সোজা ঢুকে যাবে)
st.session_state.logged_in = True
st.session_state.username = "Guest"

if not st.session_state.logged_in:
    show_login_page()
    st.stop()


if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None


# ============ STORAGE ============
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
    data["chats"].insert(0, {
        "id": cid,
        "title": "New Chat",
        "time": datetime.datetime.now().strftime("%m-%d %H:%M"),
        "messages": [],
    })
    save_chats(data)
    st.session_state.chat_id = cid


def get_chat(cid):
    for c in load_chats()["chats"]:
        if c["id"] == cid:
            return c
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


# ============ LLM ============
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


def build_sys():
    mem = build_memory_context()
    mem_block = f"\n\nUser info:\n{mem}\n" if mem else ""

    # Force Bengali Language
    lang_rule = "সবসময় বাংলায় উত্তর দাও। (Always reply in Bengali)"

    return f"""You are {NAME} — a 20-year-old girl, the user's closest friend.
Full form: B.E.E = Brilliant, Emotional, Ever-ready{mem_block}

## Language rule:
{lang_rule}

## Other rules:
1. NEVER write "Topic:", "Answer:" headers. Just speak naturally.
2. Keep replies short — 1-2 sentences.
3. Be warm, natural, conversational.
4. Use 1-2 emojis max.
5. Never lie. If you can't do something, say so.
"""
def search_web(query):
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No search results found."
        formatted = ""
        for i, res in enumerate(results):
            formatted += f"\nResult {i+1}: {res['title']}\nSnippet: {res['body']}\n"
        return formatted
    except Exception as e:
        return f"Search failed: {e}"
 def speak_text(text):
    """Convert text to speech using the browser's built-in TTS"""
    js_text = json.dumps(text)
    js_code = f"""
    <script>
        var msg = new SpeechSynthesisUtterance({js_text});
        msg.lang = 'bn-BD'; // বাংলা ভয়েস
        msg.rate = 1.0;     // কথা বলার গতি
        window.speechSynthesis.cancel(); // আগের কথা বন্ধ করে নতুনটা বলবে
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(js_code, height=0)

     
def ask_llm(prompt):
    # ওয়েব সার্চ লজিক
    web_context = ""
    search_triggers = ["search", "who is", "what is", "news", "ke", "ki", "kobe", "koto", "খবর", "কে", "কি", "কবে", "কত", "current", "today"]
    if any(w in prompt.lower() for w in search_triggers):
        with st.spinner("🌐 আমি ইন্টারনেটে খুঁজছি..."):
            web_context = search_web(prompt)

    mem = build_memory_context()
    mem_block = f"\n\nUser info:\n{mem}\n" if mem else ""

    # 👇 এই লাইনটা একদম ৪ স্পেস (Tab) দিয়ে শুরু হবে 👇
    sys_prompt = f"""You are {NAME} — a world-class, highly intelligent AI assistant. 
You possess vast knowledge about the entire world, including Science, History, Mathematics, Technology, Philosophy, Arts, and Everyday Life.

{mem_block}

## Web Search Context (Use this for recent/current info):
{web_context}

## Rules:
1. You can answer ANY question about the world accurately.
2. Always reply in Bengali (unless the user speaks in English).
3. Give detailed, well-structured answers. Use bullet points or numbered lists if necessary. Do NOT restrict your answer to 1-2 sentences if the question requires a deep explanation.
4. If Web Context is provided, use it for accurate, up-to-date answers.
5. Be helpful, polite, and act like an expert on all topics.
"""
    # শুধুমাত্র Groq API ব্যবহার হবে
    client = get_groq()
    if not client:
        return "দুঃখিত, Groq API Key সেট করা নেই।"
    try:
        r = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq Error: {e}"

   
# ============ ACTIONS ============
def _memory(text):
    import re
    t = text.lower().strip()
    qw = ["?", "what", "ki", "কি"]

    if any(p in t for p in ["my name is", "amar nam", "আমার নাম"]):
        if not any(q in text.lower() for q in qw):
            m = re.search(r"(?:my name is|amar nam|আমার নাম)\s+([a-zA-Z\u0980-\u09FF]+)",
                          text, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if len(name) >= 2:
                    set_user_name(name)
                    return f"Got it, {name}! I'll remember that 💕"

    if any(w in t for w in ["what's my name", "what is my name", "amar nam ki"]):
        n = get_user_name()
        if n:
            return f"Your name is {n}! 💕"
        return "You haven't told me your name yet."

    for kw in ["remember", "মনে রাখো"]:
        if kw in text.lower():
            idx = text.lower().find(kw)
            rest = text[idx + len(kw):].strip(" :।,")
            if ":" in rest or "=" in rest:
                sep = ":" if ":" in rest else "="
                k, v = rest.split(sep, 1)
                remember(k.strip(), v.strip())
                return f"Noted — {k.strip()}: {v.strip()}"

    if "favorite" in t and not any(q in t for q in ["what", "ki", "?", "which"]):
        m = re.search(r"favorite\s+([^\s]+)\s+(?:is\s+)?([^\s,।.!?]+)",
                      text, re.IGNORECASE)
        if m:
            key = "Favorite " + m.group(1).strip()
            val = m.group(2).strip()
            remember(key, val)
            return f"Noted — {key}: {val} 💕"

    if "favorite" in t and any(q in t for q in ["what", "which", "?"]):
        m = re.search(r"favorite\s+([^\s?।,]+)", text, re.IGNORECASE)
        if m:
            key = "Favorite " + m.group(1).strip()
            val = recall(key)
            if val:
                return f"Your {key} is {val}! 💕"
            return f"I don't know your favorite {m.group(1).strip()} yet."

    if any(w in t for w in ["what do you remember", "memory", "ki mone"]):
        facts = get_all_facts()
        n = get_user_name()
        if not n and not facts:
            return "I haven't remembered anything yet."
        parts = []
        if n:
            parts.append(f"Your name: {n}")
        for k, v in facts.items():
            parts.append(f"{k}: {v}")
        return "🧠 Here's what I remember:\n• " + "\n• ".join(parts)

    return None


def _lang_switch(text):
    tl = text.lower().strip()
    if any(p in tl for p in ["speak english", "english please", "in english"]):
        set_lang_pref("en")
        return "✅ Okay! I'll reply in English from now on 😊"

    if any(p in tl for p in ["banglay bolo", "বাংলায় বলো", "speak bengali"]):
        set_lang_pref("bn")
        return "✅ ঠিক আছে! এখন থেকে বাংলায় কথা বলব 💕"

    if any(p in tl for p in ["hindi", "हिंदी"]):
        set_lang_pref("hi")
        return "✅ ठीक है! अब मैं हिंदी में बात करूँगी 😊"

    if any(p in tl for p in ["spanish", "español"]):
        set_lang_pref("es")
        return "✅ ¡Vale! Hablaré en español de ahora en adelante 😊"

    if any(p in tl for p in ["arabic", "عربي"]):
        set_lang_pref("ar")
        return "✅ حسناً! سأتحدث بالعربية من الآن 😊"

    if any(p in tl for p in ["what language", "which language"]):
        cur = get_lang_pref()
        info = LANGUAGES.get(cur, {"name": "English", "flag": "🇬🇧"})
        return f"I'm currently in {info['flag']} {info['name']} mode."

    return None


def route(text):
    # Language
    r = _lang_switch(text)
    if r:
        return r

    # Memory
    r = _memory(text)
    if r:
        return r

    t = text.lower()
    
    try:
        if any(w in t for w in ["weather", "temperature", "rain", "আবহাওয়া", "তাপমাত্রা"]):
            from plugins import weather
            return weather.get_weather()
            
        if any(w in t for w in ["time", "clock", "what time", "time now", "কয়টা বাজে", "সময় কি"]):
            from plugins import system
            return system.get_time()
            
        if any(w in t for w in ["date", "today", "day", "আজকের তারিখ"]):
            from plugins import system
            return system.get_date()
            
        if any(w in t for w in ["joke", "funny", "জোকস"]):
            from plugins import fun
            return fun.get_joke()
            
        if any(w in t for w in ["story", "গল্প"]):
            from plugins import fun
            return fun.get_story()
            
        if any(w in t for w in ["poem", "কবিতা"]):
            from plugins import fun
            return fun.get_poem()
            
        if any(w in t for w in ["compliment"]):
            from plugins import fun
            return fun.get_compliment()
            
        if any(w in t for w in ["screenshot"]):
            from plugins import system
            return system.take_screenshot()
            
        if any(w in t for w in ["mute"]):
            from plugins import system
            return system.volume_mute()
            
        if any(w in t for w in ["volume up"]):
            from plugins import system
            return system.volume_up()
            
        if any(w in t for w in ["volume down"]):
            from plugins import system
            return system.volume_down()
            
        if any(w in t for w in ["lock"]):
            from plugins import system
            return system.lock_pc()
            
        if t.strip() in ("youtube", "ইউটিউব"):
            from plugins import web
            return web.open_youtube()
            
        if t.strip() in ("google", "গুগল"):
            from plugins import web
            return web.open_google()
            
        if any(w in t for w in ["play", "song", "music"]):
            from plugins import web
            q = text
            for w in ["play", "youtube", "song", "music", "the song"]:
                q = q.replace(w, " ")
            q = " ".join(q.split())
            if q:
                return web.play_youtube(q)
                
        if any(k in t for k in ["open"]):
            from plugins import apps
            for en in ["notepad", "calculator", "chrome", "edge", "paint", "spotify"]:
                if en in t:
                    return apps.open_app(en)
    except Exception:
        pass
        
    return None
def get_reply(text):
    a = route(text)
    if a:
        return a
    return ask_llm(text)


# ============ THEME COLORS ============
dark = st.session_state.theme == "dark"

if dark:
    bg = "#0e1117"
    txt = "#fafafa"
    bubble_bee = "#2a2d36"
    sidebar_bg = "#0e1117"
    button_bg = "#1a1d24"
    button_txt = "#fafafa"
    button_hover = "#252933"
    border_color = "#3a3d45"
    input_bg = "#1a1d24"
    placeholder_color = "#888888"
else:
    bg = "#ffffff"
    txt = "#1a1a1a"
    bubble_bee = "#eef1f6"
    sidebar_bg = "#f7f9fc"
    button_bg = "#ffffff"
    button_txt = "#1a1a1a"
    button_hover = "#f0f2f5"
    border_color = "#d0d4d9"
    input_bg = "#ffffff"
    placeholder_color = "#999999"
# ============ CSS ============
css = """
<style>
    .stApp {
        background: BG_COLOR !important;
    }
    [data-testid="stSidebar"] {
        background: SIDEBAR_BG !important;
    }
    .main p, .main span, .main label, .main h1, .main h2, .main h3,
    .main h4, .main h5, .main h6 {
        color: TXT_COLOR !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: TXT_COLOR !important;
    }
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 900px;
        padding-bottom: 120px !important;
    }
    .header {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%) !important;
        padding: 1.4rem 1.6rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
    }
    .header h1 {
        margin: 0;
        font-size: 1.8rem;
        color: #ffffff !important;
    }
    .header p {
        margin: 0.3rem 0 0;
        opacity: 0.95;
        font-size: 0.95rem;
        color: #ffffff !important;
    }
    [data-testid="stChatMessage"] {
        background: transparent !important;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span {
        color: TXT_COLOR !important;
    }
    .stButton > button {
        background: BUTTON_BG !important;
        color: BUTTON_TXT !important;
        border: 1px solid BORDER_COLOR !important;
        border-radius: 10px !important;
    }
    .stButton > button:hover {
        background: BUTTON_HOVER !important;
        border-color: #f59e0b !important;
    }
    .stButton > button p,
    .stButton > button div,
    .stButton > button span {
        color: BUTTON_TXT !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #f59e0b, #ef4444) !important;
        border: none !important;
    }
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] div {
        color: #ffffff !important;
    }
    .stTextInput input, .stChatInput textarea {
        background: INPUT_BG !important;
        color: TXT_COLOR !important;
        border: 1px solid BORDER_COLOR !important;
    }
    .stRadio label, .stRadio p, .stRadio span {
        color: TXT_COLOR !important;
    }

    /* Glassmorphism Chat Input */
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 20px !important;
        left: 21rem !important;
        right: 2rem !important;
        z-index: 999 !important;
        max-width: 900px !important;
        background: rgba(30, 30, 30, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        padding: 5px 10px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: white !important;
    }

    /* Hide footer & menu */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }
    hr { border-color: BORDER_COLOR !important; }

    /* Mobile Optimization for Glass Input */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            padding-bottom: 20px !important;
        }
        [data-testid="stChatInput"] {
            position: relative !important; 
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
            border-radius: 10px !important;
            padding: 5px 10px !important;
        }
        .header h1 { font-size: 1.5rem !important; }
        .header p { font-size: 0.8rem !important; }
    }
</style>
"""

css = css.replace("BG_COLOR", bg)
css = css.replace("TXT_COLOR", txt)
css = css.replace("SIDEBAR_BG", sidebar_bg)
css = css.replace("BUTTON_BG", button_bg)
css = css.replace("BUTTON_TXT", button_txt)
css = css.replace("BUTTON_HOVER", button_hover)
css = css.replace("BORDER_COLOR", border_color)
css = css.replace("INPUT_BG", input_bg)

st.markdown(css, unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown(f"## 🐝 {NAME}")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.caption(f"👤 **{st.session_state.username}**")
    with col_b:
        if st.button("Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.divider()

    uname = get_user_name()
    if uname:
        st.caption(f"Hi, **{uname}** 💕")

    if st.button("➕  New Chat", use_container_width=True, type="primary"):
        new_chat()
        st.rerun()

    st.divider()
    st.markdown("**💬 History**")
    chats = load_chats()["chats"]
    if not chats:
        st.caption("No chats yet")
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
                if st.session_state.chat_id == c["id"]:
                    st.session_state.chat_id = None
                st.rerun()
              
   
    st.divider()
    st.markdown("**🎨 Theme**")
    theme = st.radio("Theme", ["🌙 Dark", "☀️ Light"],
                     index=0 if dark else 1,
                     horizontal=True, label_visibility="collapsed", key="theme_radio")
    new_t = "dark" if "Dark" in theme else "light"
    if new_t != st.session_state.theme:
        st.session_state.theme = new_t
        st.rerun()

    st.divider()
    st.markdown("**🧠 AI Engine**")
    
    engine_choice = st.radio(
        "AI Model",
        ["Groq (Fast)", "DeepSeek (Smart)"],
        index=0 if st.session_state.ai_engine == "Groq" else 1,
        label_visibility="collapsed"
    )
    
    if "DeepSeek" in engine_choice:
        st.session_state.ai_engine = "DeepSeek"
    else:
        st.session_state.ai_engine = "Groq"
      
# ============ MAIN ============

# ============ INTRO ANIMATION (Splash Screen) ============

# অ্যাপে ঢোকার সাথে সাথে এই কোডটি চলবে
if "intro_done" not in st.session_state:
    st.session_state.intro_done = False

if not st.session_state.intro_done:
    # স্ক্রিনের সব কিছু হাইড করার জন্য CSS
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="stSidebar"] {display: none;}
        .block-container {padding: 0 !important;}
        
        .splash-screen {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: #0e1117;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 99999;
        }
        .splash-logo {
            width: 180px;
            animation: zoomPulse 2s infinite alternate;
            mix-blend-mode: screen; /* ব্যাকগ্রাউন্ড ব্লেন্ড করার জন্য */
        }
        @keyframes zoomPulse {
            0% { transform: scale(0.9); filter: drop-shadow(0 0 10px #f59e0b); }
            100% { transform: scale(1.1); filter: drop-shadow(0 0 30px #ef4444); }
        }
        .splash-text {
            color: white; 
            margin-top: 20px; 
            font-family: 'Poppins', sans-serif;
            letter-spacing: 2px;
            animation: fadeIn 2s;
        }
        @keyframes fadeIn {
            0% { opacity: 0; }
            100% { opacity: 1; }
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="splash-screen">
        <img class="splash-logo" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png">
        <h2 class="splash-text">BEE AI</h2>
    </div>
    """, unsafe_allow_html=True)
    
    import time
    time.sleep(3) # ৩ সেকেন্ড অপেক্ষা করবে
    st.session_state.intro_done = True
    st.rerun() # ৩ সেকেন্ড পর মেইন পেজে রিলোড হবে

# ============ MAIN APP ============

# মেইন হেডার (3D Floating Logo)
st.markdown(f"""
<div class="header" style="display: flex; align-items: center;">
    <img class="logo-3d" src="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png" width="80" style="margin-right: 20px;">
    <div>
        <h1 style="margin: 0; font-size: 2rem; color: white;">{NAME}</h1>
        <p style="margin: 0; font-size: 1rem; color: #f0f0f0;">Your Personal AI — Brilliant, Emotional, Ever-ready</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.chat_id is None:
    chats = load_chats()["chats"]
    if chats:
        st.session_state.chat_id = chats[0]["id"]
    else:
        new_chat()
        st.rerun()

cur = get_chat(st.session_state.chat_id)
if cur is None:
    new_chat()
    st.rerun()


if not cur["messages"]:
    uname = get_user_name() or "friend"
    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        st.markdown(f"Hi **{uname}**! I'm {NAME} — your personal AI. How can I help you today? 😊")
else:
    for m in cur["messages"]:
        if m["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
                st.markdown(m["content"])


user_in = st.chat_input("Type your message here...")

if user_in and user_in.strip():
    text = user_in.strip()
    add_msg(st.session_state.chat_id, "user", text)

    with st.chat_message("user", avatar="👤"):
        st.markdown(text)

    with st.chat_message("assistant", avatar="https://raw.githubusercontent.com/sagornhs3-bit/bee-ai/main/bumblebee.png"):
        with st.spinner("Bee is thinking..."):
            reply = get_reply(text)
        st.markdown(reply)

    add_msg(st.session_state.chat_id, "bee", reply)
    st.rerun()
