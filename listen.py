"""Bee - Voice Input (STT) - Google Speech + Groq + local"""

import queue
import time
import json
import tempfile
import socket
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_DIR = Path(__file__).parent / "models"
CONFIG_PATH = Path(__file__).parent / "config.json"
_whisper_model = None

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _CFG = json.load(f)
_GROQ_KEY = _CFG.get("groq_api_key", "")


def _is_online():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


def _load_whisper(model_name="small"):
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        print("[Whisper local loading...]")
        _whisper_model = WhisperModel(
            model_name, device="cpu", compute_type="int8",
            download_root=str(MODEL_DIR),
        )
        print("[Whisper local ready!]")
    return _whisper_model


def record_while(is_pressed_fn, max_seconds=30):
    frames = []
    q = queue.Queue()

    def callback(indata, frame_count, time_info, status):
        q.put(indata.copy())

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype="int16", callback=callback)
    with stream:
        start = time.time()
        while is_pressed_fn() and (time.time() - start) < max_seconds:
            try:
                frames.append(q.get(timeout=0.1))
            except queue.Empty:
                pass
        while not q.empty():
            frames.append(q.get())

    if not frames:
        return None
    audio = np.concatenate(frames, axis=0).flatten()
    if len(audio) < SAMPLE_RATE * 0.3:
        return None

    audio = audio.astype(np.float32) / 32768.0
    peak = float(np.abs(audio).max())
    print(f"[Volume peak: {peak:.4f}]")
    if 0.0001 < peak < 0.3:
        gain = min(0.9 / peak, 200.0)
        audio = audio * gain
        print(f"[Boosted x{gain:.1f}]")
    return audio


def _save_wav(audio, path):
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())


def _transcribe_google(audio, language="bn-BD"):
    try:
        import speech_recognition as sr
        tmp = Path(tempfile.gettempdir()) / "bee_google.wav"
        _save_wav(audio, tmp)
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(tmp)) as source:
            data = recognizer.record(source)
        return recognizer.recognize_google(data, language=language).strip()
    except Exception as e:
        print(f"[Google STT failed: {e}]")
        return None


def _transcribe_groq(audio, language="bn"):
    try:
        from groq import Groq
        client = Groq(api_key=_GROQ_KEY)
        tmp = Path(tempfile.gettempdir()) / "bee_groq.wav"
        sf.write(str(tmp), audio, SAMPLE_RATE)
        prompt_hint = ("নোটপ্যাড, ক্যালকুলেটর, ক্রোম, ইউটিউব, গুগল, সার্চ, "
                       "গান, খোলো, চালাও, বন্ধ করো, খুলে দাও")
        with open(tmp, "rb") as f:
            resp = client.audio.transcriptions.create(
                file=("audio.wav", f.read()),
                model="whisper-large-v3-turbo",
                language=language,
                prompt=prompt_hint,
                response_format="text",
                temperature=0.0,
            )
        return str(resp).strip()
    except Exception as e:
        print(f"[Groq STT failed: {e}]")
        return None


def _transcribe_local(audio, language="bn", model_name="small"):
    model = _load_whisper(model_name)
    segments, info = model.transcribe(audio, language=language,
                                       beam_size=5, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


def transcribe(audio, language="bn", model_name="small"):
    if _is_online():
        print("[STT: Google Speech]")
        text = _transcribe_google(audio, language="bn-BD")
        if text:
            return text
        if _GROQ_KEY.startswith("gsk_"):
            print("[STT: Groq Whisper Turbo]")
            text = _transcribe_groq(audio, language=language)
            if text:
                return text
    print("[STT: local Whisper]")
    return _transcribe_local(audio, language=language, model_name=model_name)


def record_and_transcribe(is_pressed_fn, language="bn", model_name="small"):
    audio = record_while(is_pressed_fn)
    if audio is None:
        return None
    return transcribe(audio, language=language, model_name=model_name)