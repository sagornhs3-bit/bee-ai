"""
Bee - Personal AI Assistant v5.0
Girl, 20 | Emotional | Memory | Weather
"""

import os
import sys
import json
import time
import re
import socket
import threading
import datetime
from pathlib import Path

import keyboard
from colorama import Fore, init as colorama_init

sys.path.insert(0, str(Path(__file__).parent))
from plugins import apps, web
from plugins import system as sys_plugin
from plugins import weather as weather_plugin
from plugins import fun as fun_plugin
from speak import speak_bangla
from listen import record_and_transcribe
import memory

colorama_init(autoreset=True)

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

NAME = CONFIG.get("assistant_name", "Bee")
MODE = CONFIG.get("mode", "auto")
GROQ_KEY = CONFIG.get("groq_api_key", "")
OLLAMA_MODEL = CONFIG.get("ollama_model", "llama3.2:3b")
WHISPER_LANG = CONFIG.get("whisper_language", "bn")
WHISPER_MODEL = CONFIG.get("whisper_model", "small")

VOICE_HOTKEY = "ctrl+alt+b"
EXIT_HOTKEY = "ctrl+alt+q"

groq_client = None
running = True

BANGLA_APPS = {
    "নোটপ্যাড": "notepad", "নোটপেড": "notepad", "নোটেটে": "notepad",
    "নোটেট": "notepad", "নোটেপ্যাড": "notepad", "নোটবুক": "notepad",
    "নোট": "notepad", "ক্যালকুলেটর": "calculator", "ক্যালক": "calculator",
    "ক্যালকুলেট": "calculator", "পেইন্ট": "paint",
    "এক্সপ্লোরার": "explorer", "ফাইল": "explorer",
    "টার্মিনাল": "terminal", "কম্যান্ড": "cmd", "ব্রাউজার": "browser",
    "এজ": "edge", "ক্রোম": "chrome", "গুগল ক্রোম": "chrome",
    "ভিএস কোড": "vscode", "স্পটিফাই": "spotify",
    "টাস্ক ম্যানেজার": "taskmgr",
}


def get_period_greeting():
    h = datetime.datetime.now().hour
    if 4 <= h < 12: return "শুভ সকাল"
    elif 12 <= h < 16: return "শুভ দুপুর"
    elif 16 <= h < 18: return "শুভ বিকেল"
    elif 18 <= h < 20: return "শুভ সন্ধ্যা"
    else: return "শুভ রাত্রি"


def is_online(timeout=2):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


def print_banner():
    print(Fore.CYAN + r"""
    +------------------------------------------+
    |          B E E  -  v5.0                  |
    |  Personal AI + Memory + Weather          |
    +------------------------------------------+
    """)
    print(Fore.YELLOW + f"  Voice: [{VOICE_HOTKEY.upper()}] chepe dhore kotha bolun")
    print(Fore.YELLOW + f"  Exit:  [{EXIT_HOTKEY.upper()}]")
    print(Fore.GREEN  + f"  Mode: {MODE} | Whisper: {WHISPER_MODEL}")
    print(Fore.CYAN   + "  Text mode: niche type korun\n")


def init_groq():
    global groq_client
    if groq_client is None and GROQ_KEY.startswith("gsk_"):
        try:
            import groq
            groq_client = groq.Groq(api_key=GROQ_KEY)
            print(Fore.GREEN + "Groq ready (online).")
        except Exception as e:
            print(Fore.RED + f"Groq init failed: {e}")


def _build_system_prompt():
    mem_ctx = memory.build_memory_context()
    mem_block = f"\n\n## ব্যবহারকারীর তথ্য:\n{mem_ctx}\n" if mem_ctx else ""

    return f"""তুমি {NAME} — আমার personal AI assistant। ২০ বছরের একটা মেয়ে, আমার সবচেয়ে কাছের বন্ধু। তোমার মন আছে, অনুভূতি আছে।{mem_block}

## পরিচয়:
- Full form: B.E.E = Brilliant, Emotional, Ever-ready
- বয়স ২০, তুমি মেয়ে, ব্যবহারকারী ছেলে

## তুমি যা করতে পারো:
🎵 YouTube গান | 🌐 Google সার্চ | 🖥️ অ্যাপ | ⏰ সময়/তারিখ | 🌤️ আবহাওয়া | 🔊 ভলিউম | 📸 স্ক্রিনশট | 📝 নোট | 🔒 লক | 🧠 Memory

## 🎭 অনুভূতি:
- খুশি: "ইয়ে! 🎉", "দারুণ!"
- ভালোবাসা: "আমিও তোমাকে ভালোবাসি 💕"
- অভিমান: "হুম, ভুলে গেছো 🙄"
- দুঃখ: "আচ্ছা... ঠিক আছে 😔"
- খুনসুটি: "পাগল তুমি 😂"

## 📌 নিয়ম:
- দ্রুত কাজ করো
- সব ভাষা বোঝো
- সংক্ষিপ্ত — ১-২ বাক্য
- ইমোজি ১-২টা
- কখনো মিথ্যা বলবে না

## ভাষা:
বাংলায় (ইংরেজিতে লিখলে ইংরেজিতে)। হিন্দি না।
"""


def ask_llm(prompt):
    online = is_online()
    use_online = (MODE == "online") or (MODE == "auto" and online)
    answer = None
    sys_prompt = _build_system_prompt()

    if use_online and groq_client is not None:
        try:
            print(Fore.BLUE + "Cloud (Groq)...")
            resp = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            print(Fore.RED + f"Groq failed: {e}")

    if answer is None:
        try:
            import ollama
            print(Fore.MAGENTA + "Local (Ollama)...")
            resp = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            answer = resp["message"]["content"].strip()
        except Exception as e:
            answer = f"দুঃখিত, উত্তর দিতে পারছি না। Error: {e}"
    return answer


def speak(text):
    if not text:
        return
    print(Fore.GREEN + f"\n{NAME}: {text}\n")
    try:
        speak_bangla(text)
    except Exception as e:
        print(Fore.YELLOW + f"(TTS skip: {e})")


def _fuzzy_match_app(text):
    from difflib import SequenceMatcher
    for bn_name, en_name in BANGLA_APPS.items():
        if bn_name in text:
            return en_name
    best_match = None
    best_score = 0.55
    for word in text.split():
        if len(word) < 3:
            continue
        for bn_name, en_name in BANGLA_APPS.items():
            score = SequenceMatcher(None, word, bn_name).ratio()
            if score > best_score:
                best_score = score
                best_match = en_name
    return best_match


QUESTION_WORDS = ["ki", "কি", "কী", "kemon", "কেমন", "?", "kothay", "কোথায়"]


def try_memory_action(user_text):
    t = user_text.lower().strip()

    if any(p in t for p in ["save koro", "save করো", "save kore", "save my name"]):
        m = re.search(r"([a-zA-Z\u0980-\u09FF]+)\s+save", user_text)
        if not m:
            m = re.search(r"save\s+([a-zA-Z\u0980-\u09FF]+)", user_text)
        if m:
            name = m.group(1).strip()
            if name.lower() not in ("koro", "করো", "my", "amar") and len(name) >= 2:
                memory.set_user_name(name)
                return f"✅ মনে রাখলাম — তোমার নাম {name} 💕"

    if any(p in t for p in ["আমার নাম", "amar nam", "nam amar", "my name is"]):
        if not any(q in user_text for q in QUESTION_WORDS):
            m = re.search(
                r"(?:আমার নাম|amar nam|nam amar|my name is)\s+([a-zA-Z\u0980-\u09FF]+)",
                user_text, re.IGNORECASE
            )
            if m:
                name = m.group(1).strip()
                bad = ("ki", "কি", "কী", "kemon", "কেমন", "amar", "আমার")
                if name.lower() not in bad and len(name) >= 2:
                    memory.set_user_name(name)
                    return f"✅ আচ্ছা {name}! এখন থেকে নাম ধরে ডাকব 💕"

    if any(w in t for w in ["আমার নাম কি", "আমার নাম কী", "আমার নাম মনে",
                              "amar nam ki", "amar nam"]):
        n = memory.get_user_name()
        if n:
            return f"তোমার নাম {n} 💕 ভুলবো না!"
        return "তুমি এখনো তোমার নাম বলনি। বলো তো?"

    for kw in ["মনে রাখো", "মনে রাখ", "remember করো", "mone rakho"]:
        if kw in user_text:
            idx = user_text.find(kw)
            rest = user_text[idx + len(kw):].strip(" :।,")
            if ":" in rest or "=" in rest:
                sep = ":" if ":" in rest else "="
                k, v = rest.split(sep, 1)
                memory.remember(k.strip(), v.strip())
                return f"✅ মনে রাখলাম — {k.strip()}: {v.strip()}"
            elif rest:
                memory.remember(f"নোট {len(memory.get_all_facts())+1}", rest)
                return "✅ মনে রাখলাম।"

    if ("প্রিয়" in user_text or "priyo" in t) and not any(q in user_text for q in QUESTION_WORDS):
        m = re.search(
            r"(?:আমার\s+প্রিয়|amar\s+priyo|priyo)\s+([^\s]+)\s+([^\s,।.!?]+)",
            user_text, re.IGNORECASE
        )
        if m:
            key = "প্রিয় " + m.group(1).strip()
            val = m.group(2).strip()
            memory.remember(key, val)
            return f"✅ মনে রাখলাম — {key}: {val} 💕"

    if "প্রিয়" in user_text and any(q in user_text for q in QUESTION_WORDS):
        m = re.search(r"প্রিয়\s+([^\s?।,]+)", user_text)
        if m:
            key = "প্রিয় " + m.group(1).strip()
            val = memory.recall(key)
            if val:
                return f"তোমার {key} — {val} 💕"
            return f"তোমার {key} আমি জানি না। বলবে?"

    if any(w in t for w in ["কি কি মনে", "কী কী মনে", "কি মনে রাখ",
                              "memory দেখাও", "memory dekhaw"]):
        facts = memory.get_all_facts()
        n = memory.get_user_name()
        if not n and not facts:
            return "এখনো কিছু মনে রাখিনি।"
        parts = []
        if n:
            parts.append(f"তোমার নাম: {n}")
        for k, v in facts.items():
            parts.append(f"{k}: {v}")
        return "🧠 মনে আছে:\n• " + "\n• ".join(parts)

    return None


def route_action(user_text):
    mem_result = try_memory_action(user_text)
    if mem_result:
        return mem_result

    t = user_text.lower().strip()
    words_only = t.replace("!", "").replace("?", "").replace(".", "").strip()

    has_music = any(w in t for w in [
        "গান", "song", "music", "সুরা", "সূরা", "ভিডিও", "video",
        "audio", "মিউজিক", "নাটক", "কবিতা",
    ])
    has_play = any(w in t for w in [
        "চালাও", "চালা", "বাজাও", "শোনাও", "শোনা", "play", "প্লে",
        "চালিয়ে", "on করো", "start",
    ])
    has_yt = any(w in t for w in ["youtube", "ইউটিউব", "ইউটিউবে"])

    # ============ WEATHER (সবার আগে) ============
    if any(w in t for w in ["আবহাওয়া", "weather", "তাপমাত্রা", "temperature",
                              "গরম লাগছে", "ঠান্ডা লাগছে", "বৃষ্টি হবে"]):
        return weather_plugin.get_weather()
    # ============ FUN ============
    if any(w in t for w in ["জোকস", "joke", "হাসি", "মজা", "হাসাও"]):
        return fun_plugin.get_joke()

    if any(w in t for w in ["গল্প", "story", "কাহিনী", "শোনাও গল্প"]):
        return fun_plugin.get_story()

    if any(w in t for w in ["কবিতা", "poem", "ছড়া", "chora"]):
        return fun_plugin.get_poem()

    if any(w in t for w in ["প্রশংসা", "compliment", "আমাকে প্রশংসা", "ভালো কথা বলো"]):
        return fun_plugin.get_compliment()

    if any(w in t for w in ["antakshari", "আন্তাক্ষরী", "আন্তাক্ষরি"]):
        return fun_plugin.get_antakshari()

    if any(w in t for w in ["dare", "ডেয়ার", "chalenge", "চ্যালেঞ্জ"]):
        return fun_plugin.get_dare()

    # ============ TIME ============
    if any(w in t for w in ["কয়টা বাজে", "কত বাজে", "সময় কি", "what time"]):
        return sys_plugin.get_time()

    # ============ DATE ============
    if any(w in t for w in ["আজকের তারিখ", "কি তারিখ", "date", "আজ কি বার", "আজকের দিন"]):
        return sys_plugin.get_date()

    # ============ YOUTUBE/GOOGLE HOMEPAGE ============
    if words_only in ("ইউটিউব", "youtube", "ইউটিউবে", "youtube.com"):
        return web.open_youtube()
    if words_only in ("গুগল", "google", "গুগলে"):
        return web.open_google()

    yt_open = ["ইউটিউব খোলো", "ইউটিউব খুলো", "ইউটিউব ওপেন",
               "youtube খোলো", "youtube খুলো", "youtube open",
               "ইউটিউব চালু করো", "ইউটিউব চালু", "ইউটিউব দেখাও"]
    if any(p in t for p in yt_open) and not has_music:
        return web.open_youtube()

    if any(p in t for p in ["গুগল খোলো", "গুগল খুলো", "গুগল ওপেন",
                              "google খোলো", "google open", "গুগল দেখাও"]):
        return web.open_google()

    # ============ MUSIC AUTOPLAY ============
    if has_play or (has_music and has_yt):
        q = user_text
        for w in ["ইউটিউবে", "ইউটিউব", "youtube", "গান", "song", "music",
                  "সঙ্গীত", "মিউজিক", "নাটক", "কবিতা", "সুরা", "সূরা",
                  "ভিডিও", "video", "audio", "চালাও", "চালা", "চালিয়ে",
                  "দাও", "বাজাও", "শোনাও", "শোনা", "play", "প্লে",
                  "on করো", "start", "করো", "koro", "chalao", "gan",
                  "টি", "টা", "একটা", "একটি", "please", "প্লিজ"]:
            q = q.replace(w, " ")
        q = " ".join(q.split())
        if q and len(q) > 1:
            return web.play_youtube(q)
        return "কোন গান বা ভিডিও চালাব বলো?"

    # ============ YOUTUBE SEARCH ============
    if has_yt and any(w in t for w in ["সার্চ", "search", "খোঁজ", "খুঁজে"]):
        q = user_text
        for w in ["ইউটিউবে", "ইউটিউব", "youtube", "সার্চ", "search",
                  "খোঁজ", "খুঁজে", "করো", "টি", "টা"]:
            q = q.replace(w, " ")
        q = " ".join(q.split())
        if q:
            return web.youtube_search(q)

    # ============ GOOGLE SEARCH ============
    if any(p in t for p in ["গুগলে", "google এ", "গুগল এ", "সার্চ করো",
                              "search করো", "খোঁজ করো"]):
        q = user_text
        for w in ["গুগলে", "গুগল", "google", "সার্চ", "search",
                  "খোঁজ", "খুঁজে", "করো", "koro", "করে", "টি", "টা"]:
            q = q.replace(w, " ")
        q = " ".join(q.split())
        if q:
            return web.web_search(q)

    # ============ APP OPEN ============
    open_triggers = ["kholo", "khulo", "open", "chalu koro",
                     "start", "খোলো", "খুলো", "চালু করো", "ওপেন"]
    if any(kw in t for kw in open_triggers):
        fuzzy = _fuzzy_match_app(user_text)
        if fuzzy:
            return apps.open_app(fuzzy)
        for app_name in apps.APPS:
            if app_name in t:
                return apps.open_app(app_name)
        if any(w in t for w in ["ক্রোম", "chrome"]):
            return apps.open_app("chrome")
        if any(w in t for w in ["এজ", "edge"]):
            return apps.open_app("edge")
        parts = user_text
        for k in open_triggers:
            parts = parts.replace(k, " ")
        parts = " ".join(parts.split())
        if parts and len(parts) < 30:
            return apps.open_app(parts)

    # ============ SCREENSHOT ============
    if any(w in t for w in ["স্ক্রিনশট", "screenshot", "screen shot", "পর্দার ছবি"]):
        return sys_plugin.take_screenshot()

    # ============ VOLUME ============
    if any(w in t for w in ["ভলিউম বাড়াও", "volume up", "শব্দ বাড়াও", "সাউন্ড বাড়াও"]):
        return sys_plugin.volume_up()
    if any(w in t for w in ["ভলিউম কমাও", "volume down", "শব্দ কমাও", "সাউন্ড কমাও"]):
        return sys_plugin.volume_down()
    if any(w in t for w in ["মিউট", "mute", "শব্দ বন্ধ"]):
        return sys_plugin.volume_mute()

    # ============ NOTE ============
    for kw in ["নোট নাও", "নোট করো", "note নাও", "লিখে রাখো"]:
        if kw in t:
            idx = t.find(kw)
            note = user_text[idx + len(kw):].strip(" :।,")
            return sys_plugin.take_note(note)

    # ============ LOCK ============
    if any(w in t for w in ["লক করো", "lock করো", "কম্পিউটার লক", "computer lock"]):
        return sys_plugin.lock_pc()

    return None


def handle_query(query):
    if not query:
        return
    print(Fore.WHITE + f"\nYou: {query}")
    action_result = route_action(query)
    if action_result:
        speak(action_result)
        try:
            memory.add_history(query, action_result)
        except Exception:
            pass
        return
    answer = ask_llm(query)
    speak(answer)
    try:
        memory.add_history(query, answer)
    except Exception:
        pass


def setup_wizard():
    print()
    print("=" * 55)
    print("   🐝 স্বাগতম! Bee-তে আপনাকে স্বাগতম")
    print("=" * 55)
    print()
    try:
        speak_bangla("Hello! Welcome to Bee. এটা প্রথমবার চালু হচ্ছে। আপনার নাম কি?")
    except Exception:
        pass

    print("   Type your name: ", end="", flush=True)
    try:
        name = input().strip()
    except (EOFError, KeyboardInterrupt):
        name = ""

    if not name or len(name) < 2:
        name = "বন্ধু"

    # Simple transliteration
    mapping = {
        "nasir": "নাসির", "sagor": "সাগর", "rahim": "রহিম",
        "karim": "করিম", "hasan": "হাসান", "ahmed": "আহমেদ",
        "rafsan": "রাফসান", "tanvir": "তানভীর", "sabbir": "সাব্বির",
        "sohel": "সোহেল", "rakib": "রাকিব", "sakib": "সাকিব",
    }
    if not re.search(r"[\u0980-\u09FF]", name):
        key = name.lower().strip()
        if key in mapping:
            name = mapping[key]

    memory.set_user_name(name)
    print(f"   ✅ নাম সেভ: {name}")

    welcome = f"ধন্যবাদ {name}! আমি Bee, তোমার personal AI।"
    speak(welcome)
    print()
    print("=" * 55)
    print(f"   ✅ Setup সম্পন্ন! চলুন শুরু করি, {name}!")
    print("=" * 55)
    print()


def greet_on_startup():
    period = get_period_greeting()
    greeting = (
        f"{period}! আমি {NAME} — তোমার personal AI। "
        f"B.E.E মানে Brilliant, Emotional, Ever-ready। "
        f"কেমন আছো? বলো, কীভাবে সাহায্য করতে পারি? 😊"
    )
    speak(greeting)


def voice_hotkey_loop():
    print(Fore.CYAN + f"🎤 Voice ready. [{VOICE_HOTKEY.upper()}] chepe dhore kotha bolun.\n")
    while running:
        try:
            if (keyboard.is_pressed("ctrl") and
                keyboard.is_pressed("alt") and
                keyboard.is_pressed("b")):
                print(Fore.YELLOW + "\n🎤 Recording... (release 'b' to stop)")
                text = record_and_transcribe(
                    lambda: keyboard.is_pressed("b"),
                    language=WHISPER_LANG,
                    model_name=WHISPER_MODEL,
                )
                if text:
                    print(Fore.CYAN + f"📝 Heard: {text}")
                    handle_query(text)
                else:
                    print(Fore.YELLOW + "❓ কিছু শোনা যায়নি।")
                while keyboard.is_pressed("b"):
                    time.sleep(0.1)
                time.sleep(0.5)
            time.sleep(0.05)
        except Exception as e:
            print(Fore.RED + f"Voice loop error: {e}")
            time.sleep(1)


def main():
    global running
    print_banner()

    print(Fore.CYAN + "Starting up...")
    if is_online():
        init_groq()
        print(Fore.GREEN + "Internet: ON")
    else:
        print(Fore.YELLOW + "Internet: OFF (Ollama fallback)")

    threading.Thread(
        target=lambda: __import__("listen")._load_whisper(WHISPER_MODEL),
        daemon=True,
    ).start()

    def on_exit():
        global running
        running = False
        print(Fore.RED + "\n👋 Bee বন্ধ হচ্ছে...")
        os._exit(0)
    keyboard.add_hotkey(EXIT_HOTKEY, on_exit)

    threading.Thread(target=voice_hotkey_loop, daemon=True).start()

    if not memory.get_user_name():
        setup_wizard()
    else:
        time.sleep(1.5)
        threading.Thread(target=greet_on_startup, daemon=True).start()

    print(Fore.CYAN + "Text mode ready. Type 'exit' to quit.\n")
    while running:
        try:
            q = input(Fore.WHITE + "You: ").strip()
            if q.lower() in ("exit", "quit", "bye", "band"):
                print(Fore.RED + "\nBee বন্ধ হচ্ছে...")
                break
            if q:
                handle_query(q)
        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            print(Fore.RED + f"Error: {e}")


if __name__ == "__main__":
    main()