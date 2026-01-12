# Benchmarks (PoC)

## Goals
- Track end-to-end latency for a single turn: STT latency, TTS TTFB, total turn time.
- Keep runs reproducible and comparable over time.

## Scripts
- `python scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 3`
  - Measures per-turn: `stt_latency_ms`, `tts_ttfb_ms`, `tts_total_ms`, `turn_total_ms`.

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
- `turn_total_ms_avg`: overall turn time (mic chunk → tts.end).

## Tips for Consistency
- Close other CPU/GPU heavy apps.
- Pin device/backends via env (`STT_BACKEND`, `TTS_BACKEND`, `LLM_BACKEND`).
- Use fixed prompts/text to reduce variance.
- Run multiple turns and use averages.

## Future Improvements
- Add CSV/JSON export for CI trends.
- Add load test (multiple sessions) and p95/p99 reporting.
- Include VAD/hotword scenarios separately.
