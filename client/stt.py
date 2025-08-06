import io
import asyncio
import wave
from typing import List, Tuple
import magic  # python-magic for MIME detection
from pydub import AudioSegment
import websockets


def detect_mime(file_bytes: bytes) -> str:
    """
    Определяет MIME-тип файла по его байтам.
    """
    mime = magic.from_buffer(file_bytes, mime=True)
    return mime


def prepare_wav_buffer(file_bytes: bytes) -> bytes:
    """
    Конвертирует входной аудиобуфер в WAV (PCM 16-bit, mono).
    Поддерживает WAV, MP3, другие форматы через pydub.
    """
    mime = detect_mime(file_bytes)
    # Если уже WAV, проверим параметры
    if mime == 'audio/x-wav' or mime == 'audio/wav':
        return file_bytes
    # Иначе конвертируем через pydub
    audio = AudioSegment.from_file(io.BytesIO(file_bytes))
    # Конвертируем в моно PCM 16-bit 16kHz
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    buf = io.BytesIO()
    audio.export(buf, format='wav')
    return buf.getvalue()


def get_pcm_chunks(wav_bytes: bytes, chunk_size: int = 16 * 1024) -> Tuple[List[bytes], int]:
    """
    Разбивает WAV-буфер на PCM-фреймы фиксированного размера и возвращает список фреймов и sample_rate.
    """
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
        sample_rate = wf.getframerate()
        num_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    # raw уже байты PCM interleaved
    # Разбиваем на чанки
    chunks = [raw[i:i+chunk_size] for i in range(0, len(raw), chunk_size)]
    return chunks, sample_rate


async def stream_recognition(
    chunks: List[bytes],
    sample_rate: int,
    uri: str,
    silence_duration_ms: int = 1000,
    frame_interval_ms: int = 20
) -> str:
    """
    Подключается по WebSocket к STT-сервису, шлет PCM-чанки и собирает текст.
    """
    result_parts: List[str] = []
    async with websockets.connect(uri) as ws:
        # Десктрукция send и recv во внешние таски необязательна,
        # тут простой подход: после каждого отправленного чанка читаем все пришедшие тексты.
        async def recv_loop():
            try:
                async for message in ws:
                    # Ожидаем, что сервер шлет JSON с полем text
                    # Простой парсинг без внешних зависимостей
                    import json
                    data = json.loads(message)
                    text = data.get('text') or data.get('result')
                    if text:
                        result_parts.append(text)
            except websockets.ConnectionClosed:
                pass
        recv_task = asyncio.create_task(recv_loop())

        # Отправка чанков
        for chunk in chunks:
            # В примере Rust сначала шлет метаданные (json)+pcm
            meta = {'sampleRate': sample_rate}
            import json
            meta_bytes = json.dumps(meta).encode('utf-8')
            length = len(meta_bytes)
            # Префикс из 4 байт длины
            header = length.to_bytes(4, 'little')
            payload = header + meta_bytes + chunk
            await ws.send(payload)
            await asyncio.sleep(frame_interval_ms / 1000)

        # Отправляем тишину
        silence_frames = int(silence_duration_ms / frame_interval_ms)
        silent_chunk = b'\x00' * len(chunks[0])
        for _ in range(silence_frames):
            meta = {'sampleRate': sample_rate}
            import json
            meta_bytes = json.dumps(meta).encode('utf-8')
            header = len(meta_bytes).to_bytes(4, 'little')
            payload = header + meta_bytes + silent_chunk
            await ws.send(payload)
            await asyncio.sleep(frame_interval_ms / 1000)

        await ws.close()
        await recv_task

    # Собираем итоговую строку
    return ' '.join(result_parts).strip()


async def recognize_bytes(file_bytes: bytes, uri: str) -> str:
    """
    Основная функция: конвертирует файл, шлет чанки на STT и возвращает текст.
    """
    wav = prepare_wav_buffer(file_bytes)
    chunks, sample_rate = get_pcm_chunks(wav)
    text = await stream_recognition(chunks, sample_rate, uri)
    return text
