# Runbook (PoC)

## Prerequisites
- Python 3.11+
- Node 20+ (for web client)
- (Optional) Docker for OpenTTS if using real TTS

## Backend (FastAPI WS)
```bash
cd apps/backend
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"

# Local PoC (stub STT/TTS, wake enabled)
set WAKE_ENABLED=true
set WAKE_BACKEND=stub
python -m uvicorn m_assistant_backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## Web Client (Vite + React)
```bash
cd apps/web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open http://127.0.0.1:5173

## OpenTTS (optional, via Docker Compose)
```bash
cd infra/docker
docker compose up -d
```
Set `TTS_BACKEND=opentts` when needed.

## Quick WS Flow (PTT)
1) Connect to `/ws`
2) Stream `audio.chunk`
3) Send `control.end_of_utterance`
4) Receive `stt.final` → `assistant.text` → `tts.chunk` → `tts.end`

## Quick WS Flow (Hotword)
1) `wake.enable`; `wake.set_mode: hotword`
2) Stream `audio.chunk`; wait for `wake.detected`
3) Continue streaming; send `control.end_of_utterance` to finalize

## Observability
- Prometheus metrics at `/metrics`
- Key metrics: `stt_latency_ms`, `tts_latency_ms`, `llm_latency_ms`, `llm_provider_selected`, `wake_fp_count`, `wake_fn_count`

## Benchmarks
- Latency: `python scripts/bench_latency.py --ws ws://127.0.0.1:8000/ws --turns 3`
- Add `--session` to isolate runs

## Troubleshooting
- If WS rejects audio: ensure `payload_base64` is valid and `codec` is `pcm16`.
- If wake not working: check `WAKE_ENABLED`, backend logs, and `/metrics` for counters.
- If TTS fails: ensure OpenTTS reachable or use `tts_backend=stub`.

## Safety/Privacy quick checks
- Ensure `/metrics` not public.
- No secrets in logs; use `.env`.
- Use TLS/WSS off localhost.
