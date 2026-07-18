"""
STT / LLM / TTS 단계별 지연 측정 + 최적화 옵션 벤치마크
실행: cd server && uv run python bench_pipeline.py
"""
import io
import sys
import time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

INPUT_WAV = r"C:\Users\user\AppData\Local\Temp\user_voice.wav"
INPUT_TEXT = "오늘 밥을 못 먹었어"
REPLY_TEXT = "할머니 밥은 꼭 드셔야죠, 얼른 뭐라도 챙겨 드세요."


def bench(label, fn):
    t = time.perf_counter()
    result = fn()
    dt = time.perf_counter() - t
    print(f"  {label:<40} {dt:6.2f}s")
    return dt, result


def main():
    with open(INPUT_WAV, "rb") as f:
        audio = f.read()

    print("=" * 60)
    print("BASELINE (현재 세팅)")
    print("=" * 60)

    # STT: 현재 세팅 (medium, beam_size=5)
    from chat.stt import transcribe as _stt
    from chat.stt import _model as _whisper_model
    stt_time, stt_text = bench("STT medium int8 beam=5", lambda: _stt(audio))
    print(f"    → 인식: {stt_text}")

    # LLM: 현재 세팅
    from chat.session import start_session
    from chat.engine import chat as _engine_chat
    sid = start_session("bench")
    llm_time, llm_out = bench("LLM exaone3.5:7.8b num_predict=200", lambda: _engine_chat(stt_text, sid))
    print(f"    → 응답: {llm_out['reply'][:50]}")

    # TTS: 현재 세팅
    from chat.tts import synthesize as _tts
    tts_time, _ = bench("TTS MeloTTS-Korean CPU", lambda: _tts(llm_out['reply']))

    baseline = stt_time + llm_time + tts_time
    print(f"\n  TOTAL BASELINE: {baseline:.2f}s\n")

    print("=" * 60)
    print("실험 1: Whisper beam_size 축소 (정확도 소폭 하락 감수)")
    print("=" * 60)

    import tempfile, os
    def stt_beam(bs):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio)
            path = f.name
        try:
            segs, _ = _whisper_model.transcribe(path, language="ko", beam_size=bs)
            return "".join(s.text for s in segs).strip()
        finally:
            os.unlink(path)

    stt5_time, _ = bench("STT beam=5 (기본)", lambda: stt_beam(5))
    stt1_time, _ = bench("STT beam=1", lambda: stt_beam(1))
    print(f"    → 절감: {stt5_time - stt1_time:.2f}s")

    print("\n" + "=" * 60)
    print("실험 2: LLM 모델/파라미터 교체")
    print("=" * 60)

    import ollama
    def ollama_chat(model, num_predict):
        r = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "너는 한국어 손주. 다정한 한 문장으로 답해."},
                {"role": "user", "content": stt_text},
            ],
            options={"temperature": 0.7, "num_predict": num_predict},
        )
        return r.message.content

    e78_np200, _ = bench("exaone3.5:7.8b num_predict=200", lambda: ollama_chat("exaone3.5:7.8b", 200))
    e78_np80, _ = bench("exaone3.5:7.8b num_predict=80 ", lambda: ollama_chat("exaone3.5:7.8b", 80))
    qwen_np80, _ = bench("qwen2.5:3b     num_predict=80 ", lambda: ollama_chat("qwen2.5:3b", 80))

    print("\n" + "=" * 60)
    print("실험 3: TTS 응답 길이 영향")
    print("=" * 60)
    short = "네."
    med = "네, 알겠어요."
    long_ = "할머니 오늘도 건강히 잘 지내시길 바라며 조심히 다녀오세요."
    for label, txt in [("짧게(2자)", short), ("중간(9자)", med), ("길게(29자)", long_)]:
        bench(f"TTS {label}", lambda t=txt: _tts(t))

    print("\n" + "=" * 60)
    print("추천 조합 (beam=1 + qwen2.5:3b + 짧은 응답 유도)")
    print("=" * 60)
    total_optimized = stt1_time + qwen_np80 + tts_time * 0.6  # 응답 길이 짧으면 TTS도 줄음
    print(f"  예상 총 시간: {total_optimized:.1f}s (baseline: {baseline:.1f}s)")
    print(f"  절감: {baseline - total_optimized:.1f}s ({int((baseline - total_optimized)/baseline*100)}%)")


if __name__ == "__main__":
    main()
