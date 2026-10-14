import webbrowser
import urllib.parse

try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False


def open_youtube():
    webbrowser.open("https://www.youtube.com")
    return "✅ YouTube খোলা হয়েছে।"


def open_google():
    webbrowser.open("https://www.google.com")
    return "✅ Google খোলা হয়েছে।"


def web_search(query: str) -> str:
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"✅ Google-এ '{query}' সার্চ করলাম।"


def youtube_search(query: str) -> str:
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"✅ YouTube-এ '{query}' খুঁজলাম।"


def play_youtube(query: str) -> str:
    if HAS_YTDLP:
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "default_search": "ytsearch1",
                "noplaylist": True,
                "extract_flat": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if info and "entries" in info and info["entries"]:
                    vid = info["entries"][0]
                    vid_id = vid.get("id")
                    title = vid.get("title", query)
                    if vid_id:
                        webbrowser.open(f"https://www.youtube.com/watch?v={vid_id}")
                        return f"▶️ '{title}' চালাচ্ছি।"
        except Exception as e:
            print(f"[yt-dlp failed: {e}]")

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f"▶️ '{query}' YouTube-এ সার্চ করলাম।"


def open_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"✅ {url} খোলা হয়েছে।"