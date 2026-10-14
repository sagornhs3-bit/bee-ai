"""
Bee - Smart Voice (TTS)
Auto-detect Bangla/English + fix English words in Bangla text
"""

import os
import re
import asyncio
import json
import time
import tempfile
from pathlib import Path

import pygame

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _CFG = json.load(f)

VOICE_BN = _CFG.get("tts_voice_online", "bn-BD-NabanitaNeural")
VOICE_EN = _CFG.get("tts_voice_english", "en-US-JennyNeural")

RATE = _CFG.get("tts_rate", "+0%")
PITCH = _CFG.get("tts_pitch", "+0Hz")
VOLUME = _CFG.get("tts_volume", "+0%")

pygame.mixer.init()


EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U00002B00-\U00002BFF"
    "\U0001FA00-\U0001FAFF"
    "\U00002190-\U000021FF"
    "\U00002300-\U000023FF"
    "]+",
    flags=re.UNICODE,
)

BANGLA_CHARS = re.compile(r"[\u0980-\u09FF]")


# ============================================================
#         ENGLISH WORD → BANGLA PHONETIC (for mixed text)
# ============================================================

ENGLISH_IN_BANGLA = {
    "personal AI": "পার্সোনাল এ আই",
    "personal ai": "পার্সোনাল এ আই",
    "Personal AI": "পার্সোনাল এ আই",
    "B.E.E": "বি ই ই",
    "Brilliant": "ব্রিলিয়্যান্ট",
    "Emotional": "ইমোশনাল",
    "Ever-ready": "এভার রেডি",
    "Ever ready": "এভার রেডি",
    "Good morning": "গুড মর্নিং",
    "Good afternoon": "গুড আফটারনুন",
    "Good evening": "গুড ইভনিং",
    "Good night": "গুড নাইট",
    "How are you": "হাউ আর ইউ",
    "Thank you": "থ্যাংক ইউ",
    "Welcome to": "ওয়েলকাম টু",
    "youtube": "ইউটিউব",
    "YouTube": "ইউটিউব",
    "google": "গুগল",
    "Google": "গুগল",
    "chrome": "ক্রোম",
    "Chrome": "ক্রোম",
    "notepad": "নোটপ্যাড",
    "Notepad": "নোটপ্যাড",
    "spotify": "স্পটিফাই",
    "Spotify": "স্পটিফাই",
    "welcome": "ওয়েলকাম",
    "Welcome": "ওয়েলকাম",
    "Hello": "হ্যালো",
    "hello": "হ্যালো",
    "Thanks": "থ্যাংকস",
    "Setup": "সেটআপ",
    "setup": "সেটআপ",
    "Sorry": "সরি",
    "Please": "প্লিজ",
    "Bee": "বি",
    "bee": "বি",
    "AI": "এ আই",
    "ai": "এ আই",
    "OK": "ওকে",
    "ok": "ওকে",
    "PC": "পি সি",
    "pc": "পি সি",
    "CPU": "সি পি ইউ",
    "RAM": "র‍্যাম",
    "USB": "ইউ এস বি",
    "WiFi": "ওয়াই ফাই",
    "Yes": "ইয়েস",
    "No": "নো",
}


def _is_bangla(text: str) -> bool:
    if not text:
        return False
    bn = len(BANGLA_CHARS.findall(text))
    total = len(re.findall(r"[a-zA-Z\u0980-\u09FF]", text))
    if total == 0:
        return False
    return bn / total > 0.4


def _fix_english_in_bangla(text: str) -> str:
    """Replace English words with Bangla phonetic (only if text has Bangla)"""
    if not text:
        return text
    if not BANGLA_CHARS.search(text):
        return text
    # Sort by length desc to avoid partial replacement
    for en in sorted(ENGLISH_IN_BANGLA.keys(), key=len, reverse=True):
        if en in text:
            text = text.replace(en, ENGLISH_IN_BANGLA[en])
    return text


def clean_for_tts(text: str) -> str:
    if not text:
        return ""
    # 1. Remove emoji
    text = EMOJI_PATTERN.sub("", text)
    # 2. Remove weird chars
    text = re.sub(r"[^\u0980-\u09FFa-zA-Z0-9\s,.!?।:'\"\-]", " ", text)
    # 3. Fix English words in Bangla text
    text = _fix_english_in_bangla(text)
    # 4. Collapse spaces
    text = re.sub(r"\s+", " ", text).strip()
    # 5. Strip edge punctuation
    text = text.strip(" -.,!?:;।")
    return text


# ============================================================
#                    TTS ENGINE
# ============================================================

async def _edge_speak(text, voice):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH, volume=VOLUME)
    tmp = Path(tempfile.gettempdir()) / f"bee_voice_{int(time.time()*1000)}.mp3"
    await communicate.save(str(tmp))

    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass

    pygame.mixer.music.load(str(tmp))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.05)

    try:
        pygame.mixer.music.unload()
        os.remove(str(tmp))
    except Exception:
        pass


def _windows_speak(text):
    try:
        safe = text.replace("'", "''")
        cmd = (
            'powershell -c "Add-Type -AssemblyName System.Speech; '
            '$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            f"$s.Speak('{safe}')\""
        )
        os.system(cmd)
        return True
    except Exception as e:
        print(f"[Windows SAPI failed: {e}]")
        return False


def speak_English(text):
    if not text:
        return False

    clean = clean_for_tts(text)
    if not clean:
        return False

    # Check user's language preference
    try:
        from settings import get_reply_language
        pref = get_reply_language()
    except Exception:
        pref = "auto"

    if pref == "bn":
        voice = VOICE_BN
        lang = "BN (forced)"
    elif pref == "en":
        voice = VOICE_EN
        lang = "EN (forced)"
    else:
        if _is_bangla(clean):
            voice = VOICE_BN
            lang = "BN"
        else:
            voice = VOICE_EN
            lang = "EN"

    print(f"[TTS {lang}] {clean}")

    try:
        import edge_tts  # noqa
        asyncio.run(_edge_speak(clean, voice))
        return True
    except Exception as e:
        print(f"[edge-tts failed: {e}]")
        return _windows_speak(clean)

# Test
if __name__ == "__main__":
    print("\n--- Test 1: Mixed text ---")
    print("Input:  ধন্যবাদ নাসির! আমি Bee, তোমার personal AI।")
    print("Output:", clean_for_tts("ধন্যবাদ নাসির! আমি Bee, তোমার personal AI।"))

    print("\n--- Test 2: Setup text ---")
    print("Input:  Hello! Welcome to Bee. এটা প্রথমবার চালু হচ্ছে।")
    print("Output:", clean_for_tts("Hello! Welcome to Bee. এটা প্রথমবার চালু হচ্ছে।"))

    print("\n--- Playing voice ---")
    speak_bangla("ধন্যবাদ নাসির! আমি Bee, তোমার personal AI। এখন থেকে নাম ধরে ডাকব।")