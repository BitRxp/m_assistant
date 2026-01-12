# m_assistant web (PoC)

Vite + React client:
- Captures microphone audio
- Sends `audio.chunk` over WebSocket (`pcm16`, 16kHz mono, base64)
- Displays `stt.partial` / `stt.final`
- Plays back `tts.chunk` (WAV PCM16) via WebAudio
- Wake-word runtime controls (`wake.set_mode`, `wake.enable/disable`)

## Run

1) Start backend:

```bash
cd apps/backend
set WAKE_ENABLED=true
set WAKE_BACKEND=stub
python -m uvicorn m_assistant_backend.main:app --reload --host 127.0.0.1 --port 8000
```

2) Start web client:

```bash
cd apps/web
npm install
npm run dev
```

Open http://127.0.0.1:5173
