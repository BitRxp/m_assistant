# m_assistant

Низколатентный голосовой ассистент с кастомным голосом и локальной памятью.

Цель: **разговор “как по телефону”** — быстрое распознавание → ответ → начало озвучки без заметных пауз, с контролем приватности.

## Выбранный стек (удобный и практичный)

Стек выбран по критериям: быстрое прототипирование, кроссплатформенность (в т.ч. Windows), хорошие готовые библиотеки под аудио/LLM, возможность потом выделять сервисы.

- **Backend:** Python 3.11 + FastAPI + Uvicorn (WebSocket gateway, orchestration)
- **STT (локально):** `faster-whisper` (CTranslate2; быстрый и без обязательного PyTorch)
- **VAD:** `webrtcvad` (лёгкий) + режимы по необходимости
- **TTS (кастомный голос):** OpenTTS (Docker) + Coqui TTS (как движок)
- **LLM интеграции/роутинг:** `litellm` (единый клиент под разных провайдеров) + `httpx` + `tenacity`
- **Память:** SQLite (turns/facts/summaries) + векторный индекс `hnswlib`
- **Embeddings:** `fastembed` (ONNX; без тяжёлых зависимостей)
- **Наблюдаемость:** `prometheus-client` + структурированные логи (`structlog`)
- **Клиент для PoC:** Web (Vite + React + TypeScript) — проще всего получить микрофон и быстро итерировать UI
- **Инфра:** Docker Compose для OpenTTS и (опционально) Redis

Почему это “лучший” старт:

- Python/FastAPI максимально ускоряет PoC и эксперименты с пайплайном.
- `faster-whisper` даёт хорошую скорость на CPU и обычно комфортен на Windows.
- OpenTTS в Docker упрощает TTS и развязывает зависимости.
- `litellm` убирает боль интеграций с разными LLM API и упрощает fallback/ротацию.

## Нефункциональные требования (ориентиры)

- **Latency (per turn, целевые):**
  - начало отображения текста (partial STT) ≤ 300–500 ms
  - *time-to-first-audio* (старт воспроизведения TTS) ≤ 800–1200 ms после финального текста
- **Надёжность:** деградация по качеству/фичам вместо падения (fallback провайдеров, ограничение контекста, отключение памяти).
- **Приватность:** локальное хранение памяти по умолчанию; облако — опциональный fallback.

## Архитектура

### Компоненты

- **Client (web/desktop/mobile):** запись микрофона, (опционально) VAD, стриминг аудио, воспроизведение аудио чанков, UI текста.
- **Gateway (WebSocket ingress):** принимает аудио-стрим, аутентификация, лимиты, маршрутизация.
- **STT adapter:** `faster-whisper` локально (или облачный streaming STT как fallback).
- **Dialog Manager:** состояние диалога, правила “когда отвечать”, политика памяти, вызовы tools.
- **Memory service (встроенный на старте):** SQLite + embeddings + retrieval (top-k) + summaries.
- **LLM Proxy (встроенный на старте):** выбор провайдера/модели, таймауты, retries/backoff, circuit breaker, кэш.
- **TTS adapter:** OpenTTS HTTP API → стриминг аудио чанков клиенту.
- **Observability:** метрики/логи по стадиям.

### Поток данных (high-level)

1) Client → Gateway: аудио чанки (по умолчанию PCM 16-bit 16kHz mono).
2) Gateway → STT: распознавание → `stt.partial` / `stt.final` → обратно в Client.
3) `stt.final` → Dialog Manager.
4) Dialog Manager → Memory retrieval (top-k) + сбор контекста.
5) Dialog Manager → LLM Proxy → выбранный провайдер → текст ответа.
6) текст ответа → (опц.) запись в память/summary → TTS → `tts.chunk` → Client.

### Контракт WebSocket (v0)

Client → Server:

- `audio.chunk`: `{session_id, seq, codec, sample_rate, payload_base64}`
- `control.end_of_utterance`: `{session_id}` (если клиент делает VAD)

Server → Client:

- `stt.partial`: `{session_id, text, stability}`
- `stt.final`: `{session_id, text}`
- `assistant.text`: `{session_id, text}`
- `tts.chunk`: `{session_id, codec, sample_rate, payload_base64}`
- `error`: `{session_id, code, message}`

## Память (минимальная модель)

- `turns`: user_text, assistant_text, timestamps, метаданные (latency, провайдер).
- `facts`: стабильные факты о пользователе (source, confidence, TTL).
- `summaries`: краткие свёртки по сессии.

Политика: в prompt попадает только **top-k** релевантного + **rolling summary** текущей сессии.

## Активация (wake word)

Поддерживаем режимы:

- **Push-to-talk (PTT)** — стартовый и самый надёжный.
- **Hotword on-device (always-on)** — как отдельная фича (PoC детектора + метрики FP/FN).
- **VAD + optional hotword** — компромиссный режим.

Acceptance criteria (ориентиры):

- wake-word latency ≤ 200 ms (цель для on-device)
- false positives: < 1/24h на бытовой тестовой выборке (ориентир)
- hotword можно отключить без перезапуска (fallback в PTT)

## LLM routing (минимум)

- cache-first для коротких частых запросов
- priority/weighted routing
- quota tracking
- timeout + fallback
- circuit breaker

Метрики: `llm_latency_ms`, `llm_errors_total`, `llm_provider_selected`, `quota_remaining`.

## Приватность и безопасность

- По умолчанию: не логировать сырой аудио-поток и полный текст.
- Шифрование локальной БД (или на уровне диска) + защита ключей.
- Режимы: полностью локально / разрешить облако как fallback.

## Структура репозитория

Рекомендуем monorepo, чтобы клиент, протокол и backend развивались синхронно.

### Вариант A (стартовый, один backend)

```text
.
  /apps
    /backend
      /src
        /api            # REST/WS endpoints (gateway)
        /domain         # dialog manager, policies, use-cases
        /adapters       # stt/tts/llm/memory adapters
        /core           # config, logging, metrics

    /web               # Vite + React клиент (PoC)

  /libs
    /protocol          # схемы сообщений WS/JSON, версия протокола
    /shared            # общие типы/ошибки/утилиты

  /infra
    /docker            # compose/контейнеры (OpenTTS, optional Redis)

  /scripts
    bench_latency.*

  /.env.example
  README.md
```


## Roadmap

### MVP (PoC)

- [ ] PoC WebSocket audio pipeline (partial/final STT)
- [ ] PoC streaming TTS (time-to-first-audio измерен)
- [ ] Dialog Manager v0 (turn-based)
- [ ] LLM Proxy v0 (таймауты + fallback + метрики)

### v0.2

- [ ] SQLite schema + retention
- [ ] Embeddings + retrieval (top-k)
- [ ] Summarization pipeline
- [ ] Cache layer

### v1

- [ ] Auth & profiles
- [ ] Metrics & dashboard
- [ ] Privacy modes (UX)
- [ ] Regression benchmarks

## Быстрый старт

В репозитории пока зафиксирован дизайн и выбран стек. Когда добавим код, сюда попадут:

- команды запуска backend/web/infra
- `.env.example`
- скрипты бенчмарков latency

## Лицензирование и этика

- Проверять лицензии моделей и права на использование голосов.
- Всегда запрашивать согласие при клонировании реального голоса.

---
Авторы: команда разработки.

