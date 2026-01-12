<!-- TODO list generated from project tracker -->
# TODO

Ниже приоритизированный список задач для m_assistant (критерии Done указаны кратко).

- [x] Project scaffold
  - Создать каркас репозитория: папки `apps/backend`,`apps/web`,`libs/protocol`,`infra/docker`,`scripts`; добавить `.env.example`, базовые README.md и `pyproject.toml`/`package.json` шаблоны.
  - Done: структура создана и проверена в репо.

- [x] Infra: OpenTTS Docker
  - Добавить Docker Compose для OpenTTS/Coqui.
  - Done: `docker-compose up` стартует TTS и `/health` возвращает 200.

- [x] PoC WebSocket audio pipeline
  - Backend WS endpoint принимает `audio.chunk`, возвращает `stt.partial`/`stt.final` используя `faster-whisper` adapter.
  - Done: стабильный 10‑минутный звонок без переподключений; лог latency STT собран.

- [x] PoC TTS streaming
  - Adapter к OpenTTS: текст → `tts.chunk` стрим; клиент воспроизводит чанки.
  - Done: измерен time-to-first-audio, нет прерываний при 60s воспроизведении.

- [x] Dialog Manager v0
  - Минимальный turn-based менеджер: финальный транскрипт → prompt → LLM (stub) → ответ → TTS.
  - Done: при включенном флаге backend после `stt.final` отправляет `assistant.text` и стримит `tts.chunk` (pytest покрывает).

- [x] LLM Proxy v0
  - Единый адаптер для 2 провайдеров (OpenAI-compatible + Ollama) с priority/weighted routing, таймаутами, retry и fallback; метрики выбора/ошибок.
  - Done: при отказе первичного провайдера запрос уходит во fallback, метрики `llm_fallback_total`/`llm_requests_total` фиксируются (pytest покрывает), `/metrics` доступен.

- [x] Memory schema & migrations
  - Создать SQLite схемы `turns`,`facts`,`summaries`, базовую миграцию (alembic).
  - Done: `alembic upgrade head` накатывается на пустую SQLite, CRUD тесты проходят локально (pytest покрывает).

- [x] Embeddings & retrieval
  - Интегрировать генерацию эмбеддингов + retrieval (HNSW если доступен, иначе fallback) и ограничение контекста по символам.
  - Done: retrieval возвращает top-k и ограничивает суммарный контекст; покрыто pytest; подключено в dialog best-effort (не ломает WS без миграций).

- [x] Wake-word PoC
  - Реализовать PTT + on-device hotword PoC (Porcupine stub или tiny NN).
  - Deliverable: переключаемый режим активации, метрики FP/FN.
  - Done: hotword можно включать/отключать на лету; метрики собираются.

- [x] PoC Web client (React)
  - Клиент на Vite+React: захват микрофона, отправка `audio.chunk` по WS, воспроизведение `tts.chunk`, показ `stt.partial`.
  - Done: end-to-end demo работает локально с backend.

- [x] Observability & metrics
  - Добавить `prometheus-client` метрики: stt_latency_ms, tts_latency_ms, llm_latency_ms, wake_fp_count, wake_fn_count, llm_provider_selected.
  - Done: метрики доступны на `/metrics` и отображаются в тестах.

- [x] Tests & benchmarks
  - Скрипты для бенчмарков latency (scripts/bench_latency.py), e2e сценарии, CI-шаблон.
  - Done: прогон сценариев записывает результаты и сравнивает с baseline.

- [ ] Security & privacy review
  - Документировать threat model, данные, шифрование DB, минимизация логов, opt-in облака.
  - Done: документ `docs/privacy.md` и checklist исполнения.

- [ ] Docs: protocol & runbook
  - Документация: `docs/protocol.md`, `docs/benchmarks.md`, `docs/runbook.md` (how to run PoC).
  - Done: инструкции покрывают запуск на Windows и Linux.

- [ ] Release v0 PoC demo
  - Собрать рабочий demo: backend + web client + OpenTTS, инструкции запуска и тест checklist.
  - Done: демонстрация работает на одной машине, latency записан.

---
Добавьте комментарии или пометьте задачи как выполненные в `manage_todo_list`, затем я синхронизирую TODO.md.
