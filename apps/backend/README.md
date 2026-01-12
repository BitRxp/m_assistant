# m_assistant backend

FastAPI WebSocket gateway + orchestration.

## Dev

```bash
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m uvicorn m_assistant_backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests

```bash
python -m pytest -q
```
