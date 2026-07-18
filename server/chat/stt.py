import logging
import os
import tempfile

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# 서버 시작 시 1회 로드 — 요청마다 재로드 금지
_model = WhisperModel("base", device="cpu", compute_type="int8")


def transcribe(audio_bytes: bytes) -> str:
    # ffmpeg이 파일 헤더로 포맷 감지하므로 확장자 불필요
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        segments, info = _model.transcribe(tmp_path, language="ko", beam_size=1)
        text = "".join(seg.text for seg in segments).strip()
        logger.debug("STT 결과 (%.2fs): %s", info.duration, text)
        return text
    finally:
        os.unlink(tmp_path)
