import importlib.metadata
import importlib.util
import logging
import os
import sys
import tempfile
import types

# pkg_resources가 없는 환경에서 MeloTTS가 실패하므로 shim 주입
if "pkg_resources" not in sys.modules:
    try:
        import pkg_resources  # noqa: F401
    except ImportError:
        _mod = types.ModuleType("pkg_resources")

        def _get_distribution(name: str):
            class _Dist:
                version = importlib.metadata.version(name)
            return _Dist()

        def _resource_filename(package: str, resource: str) -> str:
            spec = importlib.util.find_spec(package)
            if spec and spec.submodule_search_locations:
                return os.path.join(list(spec.submodule_search_locations)[0], resource)
            return resource

        _mod.get_distribution = _get_distribution
        _mod.resource_filename = _resource_filename
        _mod.resource_string = lambda pkg, res: b""
        _mod.resource_listdir = lambda pkg, res: []
        sys.modules["pkg_resources"] = _mod

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
