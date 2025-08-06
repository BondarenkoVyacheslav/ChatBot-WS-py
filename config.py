# config.py
import os

# Берём из переменной окружения, если есть, иначе – дефолт
STT_WS_URL = os.getenv("STT_WS_URL", "ws://127.0.0.1:8002/stt")
TTS_WS_URL = os.getenv("TTS_WS_URL", "ws://127.0.0.1:8003/tts")
