# Runbook (PoC)

## Prerequisites
- Python 3.11+
- Node 20+ (for web client)
- (Optional) Docker for OpenTTS if using real TTS

## One-command demo (Windows)

Starts OpenTTS (Docker), backend, and web client:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_demo.ps1
```

Stop processes (optionally bring Docker down too):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop_demo.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop_demo.ps1 -DockerDown
```

Notes:
- Use PowerShell in VS Code for the most reliable localhost binding on Windows.
- Add `-Bootstrap` on the first run to auto-create venv and install deps.

## Desktop app (Windows)

Start backend + OpenTTS, then launch a desktop (Electron) shell that loads the web UI build:

```powershell
scripts\run_desktop_demo.cmd -Bootstrap
```

Full voice demo (Grok) with the desktop app:

```powershell
scripts\run_desktop_demo.cmd -Full -Bootstrap
Quick local dialog (stub LLM):

```powershell
scripts\run_desktop_demo.cmd -Dialog -Bootstrap
```

```

Stopping services is the same as the web demo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\stop_demo.ps1
```

If you want to run desktop manually:

```powershell
cd apps\web
npm install
npm run build

cd ..\desktop
npm install
npm start
```

## Full voice demo (Grok)

This mode enables:
- `faster-whisper` STT
- dialog manager (`DIALOG_ENABLED=true`)
- LLM via Grok (xAI) using the built-in proxy
- OpenTTS (Docker)

1) Create `.env` in the repo root (next to `.env.example`) and set:

```dotenv
GROK_API_KEY=...            # required
GROK_MODEL=grok-2           # or another Grok model
GROK_BASE_URL=https://api.x.ai
```

2) Start everything:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_demo.ps1 -Full -Bootstrap
```

3) Open the web UI and enable "Hands-free" + "Auto end-of-utterance".

Troubleshooting:
- If STT fails to import, ensure backend deps were installed with `.[dev,stt]` (the `-Full -Bootstrap` path does this).
- If Grok returns auth errors, verify `GROK_API_KEY`.

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
