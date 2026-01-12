# m_assistant desktop (PoC)

Minimal desktop wrapper for the existing web UI using Electron.

It reuses the web client from `apps/web` and loads the production build from `apps/web/dist`.

## Prerequisites
- Node 20+
- (Optional) Python 3.11+ + Docker (if you want the full backend demo)

## Build web UI + run desktop

```powershell
cd apps\web
npm install
npm run build

cd ..\desktop
npm install
npm start
```

## Dev mode (desktop loads Vite dev server)

```powershell
cd apps\desktop
npm install
npm run dev
```

This starts the web dev server on `http://127.0.0.1:5173` and launches Electron pointing to it.

## Notes
- The app is only a shell right now: it doesn't start the backend automatically.
- Use `scripts/run_demo.ps1` (or `-Full`) to start backend + OpenTTS.
