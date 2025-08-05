from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
import json
from typing import Any
from client import recognize_bytes

router = APIRouter()

# Симуляция broadcast-сендера (в Rust он рассылал сообщения всем клиентам через канал)
# Здесь просто возвращаем ответ (или можно сохранить в очередь, если нужно)
broadcast_messages = []


@router.post("/upload")
async def file_controller(file: UploadFile = File(...)) -> Any:
    """
    Обработка загруженного WAV-файла и вызов STT-сервиса.
    """
    try:
        file_bytes = await file.read()
        result_text = await recognize_bytes(file_bytes, "http://127.0.0.1:8002")  # HTTP вместо ws://
        broadcast_messages.append(result_text)  # имитация рассылки
        return {"text": result_text}
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/message")
async def message_controller(request: Request) -> Any:
    """
    Обработка JSON-команды клиента: { "path": ..., "data": ... }
    """
    try:
        payload = await request.json()
        path = payload.get("path")
        data = payload.get("data")

        if path == "/auth":
            raise HTTPException(status_code=400, detail="UnresolvedMessageTypes")
        elif path == "/admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        elif path == "/message":
            # Эмуляция вызова test_call_all
            broadcast_messages.append(json.dumps(data))
            return JSONResponse(content={"status": "ok", "echo": data})
        else:
            raise HTTPException(status_code=400, detail="UnresolvedMessageTypes")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid message format: {e}")
