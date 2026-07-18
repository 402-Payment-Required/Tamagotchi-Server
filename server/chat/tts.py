import logging
import os
import tempfile
from typing import AsyncIterator

import edge_tts

logger = logging.getLogger(__name__)

VOICE = "ko-KR-SunHiNeural"


async def synthesize(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, VOICE)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        await communicate.save(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


async def stream_synthesize(text: str) -> AsyncIterator[bytes]:
    """오디오 청크를 생성되는 즉시 yield — 전체 파일 완성 대기 없음."""
    communicate = edge_tts.Communicate(text, VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]
