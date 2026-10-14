import os
import subprocess
from pathlib import Path

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "spotify": "spotify.exe",
    "vscode": "code",
    "vs code": "code",
}


def _find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None


def _find_edge():
    for p in EDGE_PATHS:
        if os.path.exists(p):
            return p
    return None


def open_app(app_name: str) -> str:
    name = app_name.lower().strip()

    if name in ("chrome", "ক্রোম", "গুগল ক্রোম", "google chrome"):
        path = _find_chrome()
        if path:
            try:
                subprocess.Popen([path])
                return "✅ Chrome খোলা হয়েছে।"
            except Exception as e:
                return f"❌ Chrome খুলতে পারলাম না: {e}"
        return "❌ Chrome ইনস্টল নেই।"

    if name in ("edge", "এজ", "microsoft edge", "browser", "ব্রাউজার"):
        path = _find_edge()
        if path:
            try:
                subprocess.Popen([path])
                return "✅ Edge খোলা হয়েছে।"
            except Exception as e:
                return f"❌ Edge খুলতে পারলাম না: {e}"
        return "❌ Edge ইনস্টল নেই।"

    if name in APPS:
        try:
            subprocess.Popen(APPS[name], shell=True)
            return f"✅ {app_name} খোলা হয়েছে।"
        except Exception as e:
            return f"❌ {app_name} খুলতে পারলাম না: {e}"

    for key, exe in APPS.items():
        if key in name or name in key:
            try:
                subprocess.Popen(exe, shell=True)
                return f"✅ {key} খোলা হয়েছে।"
            except Exception as e:
                return f"❌ {key} খুলতে পারলাম না: {e}"

    try:
        os.system(f'start "" "{app_name}"')
        return f"✅ {app_name} খোলার চেষ্টা করলাম।"
    except Exception as e:
        return f"❌ {app_name} পাইনি।"