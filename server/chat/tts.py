import logging
import os
import tempfile

from melo.api import TTS as MeloTTS

logger = logging.getLogger(__name__)

# 서버 시작 시 1회 로드 — 요청마다 재로드 금지
_tts = MeloTTS(language="KR", device="cpu")
_speaker_id = _tts.hps.data.spk2id["KR"]


def synthesize(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _tts.tts_to_file(text, _speaker_id, tmp_path, quiet=True)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)
