"""
AI 파이프라인 단독 검증 스크립트
실행: cd server && python test_pipeline.py
각 단계를 순서대로 테스트한다.
"""

import sys


def test_session():
    print("\n[1/4] session.py 테스트")
    from chat.session import start_session, get_history, add_turn, end_session

    sid = start_session("test_user")
    assert sid, "session_id가 비어있음"

    add_turn(sid, "user", "안녕")
    add_turn(sid, "assistant", "안녕하세요!")
    history = get_history(sid)
    assert len(history) == 2, f"히스토리 길이 오류: {len(history)}"

    end_session(sid)
    assert get_history(sid) == [], "세션 종료 후 히스토리가 남아있음"
    print("  OK — 세션 생성/히스토리/종료 정상")


def test_stt():
    print("\n[2/4] stt.py 테스트 (faster-whisper 모델 로드 — 첫 실행 시 다운로드)")
    from chat.stt import transcribe

    # 빈 오디오로 로드만 확인 (실제 오디오 없이 import 오류 체크)
    print("  OK — faster-whisper 모델 로드 성공")
    print("  (실제 음성 파일 테스트는 아래 주석 해제 후 실행)")
    # with open("test.wav", "rb") as f:
    #     result = transcribe(f.read())
    #     print(f"  STT 결과: {result}")


def test_tts():
    print("\n[3/4] tts.py 테스트 (MeloTTS 모델 로드 — 첫 실행 시 다운로드)")
    from chat.tts import synthesize

    audio_bytes = synthesize("할머니 밥은 꼭 드셔야죠.")
    assert isinstance(audio_bytes, bytes), "bytes가 아님"
    assert len(audio_bytes) > 0, "오디오 bytes가 비어있음"

    with open("test_tts_output.wav", "wb") as f:
        f.write(audio_bytes)
    print(f"  OK — TTS 생성 성공 ({len(audio_bytes):,} bytes)")
    print("  출력 파일: server/test_tts_output.wav (재생해서 확인)")


def test_engine():
    print("\n[4/4] engine.py 테스트 (Ollama 서버가 실행 중이어야 함)")
    from chat.session import start_session
    from chat.engine import chat

    sid = start_session("test_user")

    cases = [
        ("오늘 밥을 못 먹었어", "worried"),
        ("오늘 기분이 너무 좋아", "happy"),
        ("손이 시려워", None),
    ]

    for msg, expected_emotion in cases:
        result = chat(msg, sid)
        assert "reply" in result, "reply 키 없음"
        assert "emotion" in result, "emotion 키 없음"
        assert "signals" in result, "signals 키 없음"
        assert result["emotion"] in {"happy", "worried", "excited", "sad", "neutral"}, \
            f"잘못된 emotion: {result['emotion']}"
        emotion_ok = "✓" if (expected_emotion is None or result["emotion"] == expected_emotion) else "△"
        print(f"  {emotion_ok} 입력: {msg}")
        print(f"     reply  : {result['reply']}")
        print(f"     emotion: {result['emotion']} (예상: {expected_emotion or '무관'})")
        print(f"     signals: {result['signals']}")

    print("  OK — engine 멀티턴 정상")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"

    try:
        if step in ("all", "session"):
            test_session()
        if step in ("all", "stt"):
            test_stt()
        if step in ("all", "tts"):
            test_tts()
        if step in ("all", "engine"):
            test_engine()
        print("\n모든 테스트 통과")
    except AssertionError as e:
        print(f"\n실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n오류: {e}")
        sys.exit(1)
