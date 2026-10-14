"""System plugins - English time, date, screenshot, volume, notes, lock"""

import os
import time
import datetime
from pathlib import Path

NOTES_FILE = Path(__file__).parent.parent / "notes.txt"
SCREENSHOTS_DIR = Path.home() / "Pictures" / "Bee_Screenshots"

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False


def _get_volume_interface():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def get_time() -> str:
    now = datetime.datetime.now()
    h, m = now.hour, now.minute
    if 4 <= h < 12:
        period = "morning"
    elif 12 <= h < 17:
        period = "afternoon"
    elif 17 <= h < 21:
        period = "evening"
    else:
        period = "night"
    return f"It's {h}:{m:02d} - good {period}!"


def get_date() -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS_DIR / f"bee_{int(time.time())}.png"
        ImageGrab.grab().save(str(path))
        return "Screenshot taken and saved!"
    except Exception as e:
        return f"Couldn't take screenshot: {e}"


def volume_up() -> str:
    if not HAS_PYCAW:
        return "pycaw not installed."
    try:
        vol = _get_volume_interface()
        cur = vol.GetMasterVolumeLevelScalar()
        new = min(1.0, cur + 0.1)
        vol.SetMasterVolumeLevelScalar(new, None)
        return f"Volume up to {int(new*100)} percent."
    except Exception as e:
        return f"Error: {e}"


def volume_down() -> str:
    if not HAS_PYCAW:
        return "pycaw not installed."
    try:
        vol = _get_volume_interface()
        cur = vol.GetMasterVolumeLevelScalar()
        new = max(0.0, cur - 0.1)
        vol.SetMasterVolumeLevelScalar(new, None)
        return f"Volume down to {int(new*100)} percent."
    except Exception as e:
        return f"Error: {e}"


def volume_mute() -> str:
    if not HAS_PYCAW:
        return "pycaw not installed."
    try:
        vol = _get_volume_interface()
        muted = vol.GetMute()
        vol.SetMute(not muted, None)
        return "Muted." if not muted else "Unmuted."
    except Exception as e:
        return f"Error: {e}"


def take_note(note_text: str) -> str:
    if not note_text or len(note_text.strip()) < 2:
        return "What should I note down?"
    try:
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {note_text}\n")
        return "Note saved!"
    except Exception as e:
        return f"Error: {e}"


def lock_pc() -> str:
    try:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Locking your PC. See you soon!"
    except Exception as e:
        return f"Error: {e}"