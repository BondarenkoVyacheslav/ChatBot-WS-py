from fastapi import FastAPI, UploadFile, File, HTTPException
import wave
import aiohttp
import mimetypes
import json
import tempfile
import os

app = FastAPI()

STT_URL = "http://example.com/stt"  # <-- HTTP URL внешнего STT (НЕ WebSocket)


@app.post("/recognize")
async def recognize_audio(file: UploadFile = File(...)):
    # Проверка MIME-типа
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type not in ("audio/wav", "audio/x-wav"):
        raise HTTPException(status_code=415, detail="Unsupported media type")

    # Временное сохранение файла
    try:
        contents = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Получение sample rate
    try:
        with wave.open(tmp_path, 'rb') as wav:
            sample_rate = wav.getframerate()
            raw_pcm = wav.readframes(wav.getnframes())
    except wave.Error:
        os.unlink(tmp_path)
        raise HTTPException(status_code=415, detail="Invalid WAV file")

    os.unlink(tmp_path)

    # Пример: отправка HTTP POST на внешний STT (нужно адаптировать под реальный API!)
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "sampleRate": sample_rate,
                "audio": raw_pcm.hex(),  # Или base64, в зависимости от того, что принимает сервер
            }
            async with session.post(STT_URL, json=payload) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=500, detail="STT service failed")
                result = await resp.json()
                return { "text": result.get("text", "") }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to contact STT service")
