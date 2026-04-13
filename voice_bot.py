import os
import io
import time
import base64
import threading
import numpy as np
import soundfile as sf
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import sherpa_onnx
import ollama

# ---------------------------------------------------------------------------
# Windows MeCab bootstrap: fugashi.Tagger() needs a mecabrc pointing to a
# UniDic-format dictionary. unidic-lite ships the full UniDic schema (named
# feature attributes like .pron / .kana) that misaki/cutlet.py requires.
# ipadic uses a different schema and gives "tuple has no attribute 'pron'".
# ---------------------------------------------------------------------------
if os.name == 'nt':
    try:
        import unidic_lite
        _mecabrc = r'c:\mecab\mecabrc'
        os.makedirs(r'c:\mecab', exist_ok=True)
        with open(_mecabrc, 'w') as _f:
            _f.write(f'dicdir = {unidic_lite.DICDIR}\n')
        print("[System] MeCab config written (unidic-lite). Japanese TTS ready.")
    except ImportError:
        print("[Warning] unidic-lite not installed — Japanese TTS unavailable. Fix: pip install unidic-lite")

from kokoro import KPipeline

# ---------------------------------------------------------------------------
# Setup & Config
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "voice-bot-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=10 * 1024 * 1024)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "STT", "models"))
# If the script is run from root, STT/models should be accessible there.
if not os.path.exists(MODELS_DIR):
    MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

SAMPLE_RATE_STT = 16000
SAMPLE_RATE_TTS = 24000

EN_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-streaming-zipformer-en-2023-06-26")
SV_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17")
DOLPHIN_DIR = os.path.join(MODELS_DIR, "sherpa-onnx-dolphin-base-ctc-multi-lang-int8-2025-04-02")
VAD_MODEL = os.path.join(MODELS_DIR, "silero_vad.onnx")

LANGUAGE_MAP = {
    "en": {"name": "English", "stt": "en", "tts": "a", "voice": "af_heart"},
    "ja": {"name": "Japanese", "stt": "ja", "tts": "j", "voice": "jf_alpha"},
    "hi": {"name": "Hindi", "stt": "hi", "tts": "h", "voice": "hf_alpha"}
}

# ---------------------------------------------------------------------------
# Load STT Models
# ---------------------------------------------------------------------------
print("[System] Loading STT (SenseVoice) for all languages...")
sense_voice = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=os.path.join(SV_DIR, "model.int8.onnx"), tokens=os.path.join(SV_DIR, "tokens.txt"),
    num_threads=4, provider="cpu", language="auto", use_itn=True,
)

print("[System] Loading Hindi STT (Dolphin Base CTC)...")
dolphin_hi = sherpa_onnx.OfflineRecognizer.from_dolphin_ctc(
    model=os.path.join(DOLPHIN_DIR, "model.int8.onnx"), tokens=os.path.join(DOLPHIN_DIR, "tokens.txt"),
    num_threads=4, provider="cpu",
)

def make_vad():
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = VAD_MODEL
    cfg.silero_vad.threshold = 0.5
    cfg.silero_vad.min_silence_duration = 0.5
    cfg.silero_vad.min_speech_duration = 0.25
    cfg.silero_vad.max_speech_duration = 10.0
    cfg.sample_rate = SAMPLE_RATE_STT
    return sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=30)

# ---------------------------------------------------------------------------
# Load TTS Pipelines (Kokoro)
# ---------------------------------------------------------------------------
tts_pipelines = {}
def get_tts_pipeline(lang_code):
    if lang_code not in tts_pipelines:
        print(f"[System] Loading Kokoro TTS pipeline for {lang_code}...")
        tts_pipelines[lang_code] = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
        print(f"[System] Kokoro TTS pipeline '{lang_code}' ready.")
    return tts_pipelines[lang_code]

def _preload_tts():
    for lang_info in LANGUAGE_MAP.values():
        code = lang_info["tts"]
        try:
            get_tts_pipeline(code)
        except Exception as e:
            print(f"[Warning] Failed to preload TTS pipeline '{code}': {e}")

# Preload TTS pipelines in background
threading.Thread(target=_preload_tts, daemon=True).start()

# ---------------------------------------------------------------------------
# Session Manager
# ---------------------------------------------------------------------------
class Session:
    def __init__(self, sid, lang="en"):
        self.sid = sid
        self.lang = lang
        self.lock = threading.Lock()
        self.history = [{"role": "system", "content": f"You are a helpful and extremely concise voice AI. Speak in {LANGUAGE_MAP[lang]['name']}. Do NOT use emojis. Respond in one or two short sentences."}]
        self.is_ai_speaking = False
        self.set_language(lang)

    def set_language(self, lang):
        self.lang = lang
        self.mode = "offline"
        self.stream = None
        self.vad = make_vad()
        self.last_partial = ""

    def process_audio(self, samples):
        events = []
        if self.is_ai_speaking:
            return events # Ignore mic while AI is talking

        with self.lock:
            self.vad.accept_waveform(samples)
            while not self.vad.empty():
                seg = self.vad.front.samples
                self.vad.pop()
                stream = self._offline_stream()
                stream.accept_waveform(SAMPLE_RATE_STT, np.asarray(seg, dtype=np.float32))
                self._offline_decode(stream)
                text = stream.result.text.strip()
                if text: events.append({"type": "final", "text": text})
        return events

    def _offline_stream(self):
        if self.lang in ["en", "ja"]: return sense_voice.create_stream()
        if self.lang == "hi": return dolphin_hi.create_stream()
    def _offline_decode(self, stream):
        if self.lang in ["en", "ja"]: sense_voice.decode_stream(stream)
        elif self.lang == "hi": dolphin_hi.decode_stream(stream)

sessions = {}
sessions_lock = threading.Lock()

# ---------------------------------------------------------------------------
# LLM & TTS Logic Streamer
# ---------------------------------------------------------------------------
def generate_and_speak(sid, text):
    sess = sessions.get(sid)
    if not sess: return
    
    sess.is_ai_speaking = True
    sess.history.append({"role": "user", "content": text})
    socketio.emit("ai_status", {"status": "thinking", "text": text}, to=sid)

    try:
        stream = ollama.chat(model='llama3.1:8b', messages=sess.history, stream=True)
    except Exception as e:
        socketio.emit("ai_status", {"status": "error", "error": str(e)}, to=sid)
        sess.is_ai_speaking = False
        return

    config = LANGUAGE_MAP[sess.lang]
    try:
        pipeline = get_tts_pipeline(config["tts"])
    except Exception as e:
        socketio.emit("ai_status", {"status": "error", "error": f"TTS unavailable for this language: {e}"}, to=sid)
        sess.is_ai_speaking = False
        return
    voice = config["voice"]

    current_text = ""
    full_response = ""
    chunk_idx = 0

    def synthesize_chunk(txt):
        nonlocal chunk_idx
        if not txt.strip(): return
        socketio.emit("ai_partial", {"text": txt}, to=sid)
        for _, _, audio in pipeline(txt, voice=voice, speed=1.1):
            buf = io.BytesIO()
            sf.write(buf, audio.numpy(), SAMPLE_RATE_TTS, format="WAV")
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode()
            socketio.emit("tts_chunk", {"audio": b64, "chunk": chunk_idx, "text": txt}, to=sid)
            chunk_idx += 1

    for chunk in stream:
        content = chunk.get('message', {}).get('content', '')
        if not content: continue
        current_text += content
        full_response += content

        if current_text and current_text[-1] in ' \n':
            stripped = current_text.strip()
            if stripped and stripped[-1] in ['.', '?', '!', ',', '\n']:
                words = stripped.split()
                if len(words) >= 4:
                    synthesize_chunk(current_text)
                    current_text = ""

    if current_text.strip():
        synthesize_chunk(current_text)

    sess.history.append({"role": "assistant", "content": full_response})
    socketio.emit("ai_status", {"status": "idle"}, to=sid)
    sess.is_ai_speaking = False

# ---------------------------------------------------------------------------
# Web Routes & Sockets
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("voice_bot.html", languages=LANGUAGE_MAP)

@socketio.on("connect")
def on_connect():
    with sessions_lock:
        sessions[request.sid] = Session(request.sid, "en")
    print(f"Client {request.sid} connected.")

@socketio.on("disconnect")
def on_disconnect():
    with sessions_lock:
        sessions.pop(request.sid, None)

@socketio.on("set_language")
def on_set_lang(data):
    sess = sessions.get(request.sid)
    if sess and data.get("lang") in LANGUAGE_MAP:
        sess.set_language(data["lang"])
        sess.history = [{"role": "system", "content": f"You are a helpful and extremely concise voice AI. Speak in {LANGUAGE_MAP[data['lang']]['name']}. Do NOT use emojis. Respond in one or two short sentences."}]

@socketio.on("audio")
def on_audio(data):
    sess = sessions.get(request.sid)
    if not sess: return
    samples = np.frombuffer(data, dtype=np.float32) if isinstance(data, (bytes, bytearray)) else np.asarray(data, dtype=np.float32)
    if samples.size == 0: return

    events = sess.process_audio(samples)
    for ev in events:
        if ev["type"] == "partial":
            emit("stt_partial", {"text": ev["text"]})
        elif ev["type"] == "final":
            emit("stt_final", {"text": ev["text"]})
            # Trigger LLM explicitly in background thread
            socketio.start_background_task(generate_and_speak, request.sid, ev["text"])

def run():
    print("[System] Voice Bot running on http://localhost:5002")
    socketio.run(app, host="0.0.0.0", port=5002, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    run()
