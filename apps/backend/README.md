# m_assistant backend

FastAPI WebSocket gateway + orchestration.

## Features

- **STT (Speech-to-Text)**: faster-whisper adapter for real-time transcription
- **TTS (Text-to-Speech)**: OpenTTS streaming adapter
- **LLM Proxy**: Multi-provider routing with fallback (OpenAI, Ollama)
- **Wake-word Detection**: PTT and hotword activation with runtime switching
- **Memory & Retrieval**: SQLite + embeddings for context-aware conversations
- **Observability**: Prometheus metrics for latency, errors, and wake FP/FN

## Dev

```bash
python -m venv .venv
. .venv/Scripts/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
python -m uvicorn m_assistant_backend.main:app --reload --host 127.0.0.1 --port 8000
```

## Wake-word PoC

Enable wake-word detection:

```bash
WAKE_ENABLED=true WAKE_BACKEND=stub python -m uvicorn m_assistant_backend.main:app --reload
```

Run demo:

```bash
python scripts/demo_wake.py
```

See [protocol_wake.md](../../docs/protocol_wake.md) for full wake-word protocol documentation.

## Tests

```bash
python -m pytest -q
```

Wake-word specific tests:

```bash
pytest tests/test_wake_word.py -v
pytest tests/test_wake_unit.py -v
```
