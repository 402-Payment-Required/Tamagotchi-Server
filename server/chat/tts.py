import logging
import os
import tempfile

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
