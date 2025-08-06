# client.py
import asyncio
import websockets
import wave
from typing import Optional

async def synthesize_speech(
    text: str,
    tts_url: str,
    output_path: str,
    timeout: Optional[float] = 6.0,
) -> None:
    """
    Подключается к WebSocket TTS, шлёт text и пишет WAV в output_path.
    """
    async with websockets.connect(tts_url) as ws:
        await ws.send(text)
        buf = bytearray()

        try:
            while True:
                frame = await asyncio.wait_for(ws.recv(), timeout=timeout)
                if isinstance(frame, bytes):
                    buf.extend(frame)
                else:
                    # возможно, пришёл сигнал окончания
                    break
        except asyncio.TimeoutError:
            # конец при таймауте
            pass

    # Запись в WAV (16-bit, mono, 44.1 kHz к примеру)
    with wave.open(output_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(buf)
