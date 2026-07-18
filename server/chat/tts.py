import logging
import os
import tempfile

from piper.voice import Voice

logger = logging.getLogger(__name__)

# 서버 시작 시 1회 로드 — 요청마다 재로드 금지
_voice = Voice.load("kor_KO-female_low")


def synthesize(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        with open(tmp_path, "wb") as wav_file:
            _voice.synthesize(text, wav_file)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)
