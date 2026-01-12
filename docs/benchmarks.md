# Benchmarks (PoC)

## Goals
- Track end-to-end latency for a single turn: STT latency, TTS TTFB, total turn time.
- Keep runs reproducible and comparable over time.

## Scripts
- `python scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 3`
  - Measures per-turn: `stt_latency_ms`, `tts_ttfb_ms`, `tts_total_ms`.

## How to Run
1) Start backend (stub or real backends):
```bash
cd apps/backend
set WAKE_ENABLED=false
python -m uvicorn m_assistant_backend.main:app --host 127.0.0.1 --port 8000 --reload
```
2) Run benchmark:
```bash
python scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 5
```
3) Record the summary printed at the end.

## Interpreting Results
- `stt_latency_ms_avg`: transcription time per utterance.
- `tts_ttfb_ms_avg`: time to first audio chunk for TTS.
- (Optional) If dialog is enabled, you may also see `dialog_to_assistant_ms` and `auto_tts_*` keys per turn.

## Tips for Consistency
- Close other CPU/GPU heavy apps.
- Pin device/backends via env (`STT_BACKEND`, `TTS_BACKEND`, `LLM_BACKEND`).
- Use fixed prompts/text to reduce variance.
- Run multiple turns and use averages.

## Future Improvements
- Add CSV/JSON export for CI trends.
- Add load test (multiple sessions) and p95/p99 reporting.
- Include VAD/hotword scenarios separately.

---

### Baseline (2026-01-12)

Run command:

```bash
python -u scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 5 --verbose
```

Per-turn results (measured on local Windows machine, backend running with stub STT and OpenTTS enabled):

- turn 1: {'stt_latency_ms': 0.7441, 'tts_ttfb_ms': 4584.3102, 'tts_total_ms': 4584.5305}
- turn 2: {'stt_latency_ms': 0.4653, 'tts_ttfb_ms': 1034.8203, 'tts_total_ms': 1035.0449}
- turn 3: {'stt_latency_ms': 0.4233, 'tts_ttfb_ms': 930.7008, 'tts_total_ms': 930.8776}
- turn 4: {'stt_latency_ms': 0.7315, 'tts_ttfb_ms': 936.6361, 'tts_total_ms': 936.8274}
- turn 5: {'stt_latency_ms': 0.4643, 'tts_ttfb_ms': 796.2264, 'tts_total_ms': 796.3989}

Summary:

- turns: 5
- stt_latency_ms_avg: 0.57 ms
- tts_ttfb_ms_avg: 1656.54 ms
- tts_total_ms_avg: 1656.74 ms

Notes:
- The first-turn TTS TTFB is high (~4.6s) — likely a warm-up (OpenTTS cold start or model load).
- Subsequent turns show ~0.8–1.0s TTS TTFB.
- STT is a local stub; replace with `faster-whisper` for realistic STT latency measurements.

