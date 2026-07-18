"""
Windows 전용 호환 shim (Linux/macOS에서는 no-op).

1. `import MeCab` stub — python-mecab-ko와 mecab-python3가 case-insensitive FS에서
   충돌해서 mecab-python3 설치가 불안정. MeloTTS Japanese 모듈이 로드 시점에
   `import MeCab; MeCab.Tagger()`를 호출하므로 실제 사용은 안 하지만 통과시켜야 함.
2. `import eunjeon` shim — g2pkk가 Windows에서 mecab 대신 eunjeon을 요구하는데
   eunjeon은 Visual Studio 빌드가 필요해 설치 어려움. python-mecab-ko로 위임.
"""
import importlib.machinery as _machinery
import platform as _platform
import sys as _sys
import types as _types


def _make_stub(name: str) -> _types.ModuleType:
    # g2pkk 등이 importlib.util.find_spec()을 호출하므로 __spec__ 필수
    module = _types.ModuleType(name)
    module.__spec__ = _machinery.ModuleSpec(name, loader=None)
    return module


if _platform.system() == "Windows":
    if "MeCab" not in _sys.modules:
        _mecab_stub = _make_stub("MeCab")

        class _JpTagger:
            def __init__(self, *args, **kwargs):
                pass

            def parse(self, text):
                return ""

            def parseToNode(self, text):
                return None

        _mecab_stub.Tagger = _JpTagger
        _sys.modules["MeCab"] = _mecab_stub

    if "eunjeon" not in _sys.modules:
        try:
            import eunjeon  # noqa: F401  (site-packages에 이미 있으면 그대로 사용)
        except ImportError:
            try:
                import mecab as _pmk

                _eunjeon = _make_stub("eunjeon")

                class _EunjeonMecab:
                    def __init__(self, *args, **kwargs):
                        self._m = _pmk.MeCab()

                    def pos(self, text):
                        return self._m.pos(text)

                    def morphs(self, text):
                        return self._m.morphs(text)

                    def nouns(self, text):
                        return self._m.nouns(text)

                _eunjeon.Mecab = _EunjeonMecab
                _sys.modules["eunjeon"] = _eunjeon
            except ImportError:
                pass
