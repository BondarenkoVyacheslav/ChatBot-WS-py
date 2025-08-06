# controller.py
from fastapi import APIRouter, Request, UploadFile, File, Body, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Coroutine
from uuid import uuid4
from pathlib import Path

from starlette.responses import FileResponse

from config import STT_WS_URL, TTS_WS_URL

from client.stt import recognize_bytes
from client.tts import synthesize_speech

router = APIRouter()

# 1) POST /api/message
class MessagePayload(BaseModel):
    path: str
    data: Dict[str, Any]

@router.post("/message", summary="Обработка JSON-команды клиента")
async def message_controller(
    request: Request,
    payload: MessagePayload = Body(...),
) -> Any:
    """
    Аналог вашего message_controller:
    - проверяет payload.path
    - сохраняет в state.broadcast_messages
    - возвращает echo или ошибку
    """
    path, data = payload.path, payload.data
    if path == "/auth":
        raise HTTPException(400, "UnresolvedMessageTypes")
    if path == "/admin":
        raise HTTPException(403, "Forbidden")
    if path == "/message":
        request.app.state.broadcast_messages.append(data)
        return {"status": "ok", "echo": data}
    raise HTTPException(400, "UnresolvedMessageTypes")


# 2) POST /api/upload
@router.post("/upload", summary="Обработка аудио-файла (STT)")
async def file_controller(
    request: Request,
    file: UploadFile = File(...),
) -> Any:
    """
    Аналог вашего file_controller:
    - принимает WAV/MP3
    - вызывает recognize_bytes
    - сохраняет текст в state.broadcast_messages
    - возвращает JSON {"text": "..."}
    """
    try:
        data = await file.read()
        text = await recognize_bytes(data, STT_WS_URL)
        request.app.state.broadcast_messages.append(text)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(415, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {e}")


# 3) POST /api/synthesize
class TextPayload(BaseModel):
    text: str

@router.post("/synthesize", summary="Генерация WAV-аудио (TTS)")
async def tts_controller(
    payload: TextPayload = Body(...),
) -> FileResponse:
    """
    - принимает JSON {"text": "..."}
    - вызывает synthesize_speech
    - возвращает WAV-аудио в ответе
    """
    out_path = Path("/tmp") / f"{uuid4()}.wav"
    await synthesize_speech(payload.text, TTS_WS_URL, str(out_path))
    return FileResponse(out_path, media_type="audio/wav")


# 4) GET /api/messages
@router.get("/messages", summary="Получить накопленные события")
async def get_messages(request: Request) -> Any:
    """
    - возвращает и очищает request.app.state.broadcast_messages
    - эмулирует поведение broadcast
    """
    msgs: List[Any] = request.app.state.broadcast_messages.copy()
    request.app.state.broadcast_messages.clear()
    return {"messages": msgs}


# (Опционально) 5) SSE-поток на /api/events
from fastapi.responses import EventSourceResponse
import asyncio, json

@router.get("/events", summary="SSE-стрим событий")
async def events(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            if request.app.state.broadcast_messages:
                msg = request.app.state.broadcast_messages.pop(0)
                yield f"data: {json.dumps(msg)}\n\n"
            else:
                await asyncio.sleep(0.5)
    return EventSourceResponse(event_generator())
