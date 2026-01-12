# Protocol Overview (PoC)

## WebSocket Endpoint
- URL: `ws://<host>:8000/ws` (use `wss://` with TLS in prod)
- Payloads are JSON messages.

### Client → Server
- `audio.chunk`: `{session_id?, seq?, codec?, sample_rate?, payload_base64}` (PCM16 mono 16kHz recommended)
- `control.end_of_utterance`: `{session_id?}` (signals end of speech when using PTT)
- `tts.request`: `{text}` (synthesize arbitrary text)
- Wake control:
  - `wake.set_mode`: `{mode: "ptt" | "hotword" | "auto"}`
  - `wake.enable` / `wake.disable`
  - `wake.get_status`
  - `wake.report_false_positive` / `wake.report_false_negative`

### Server → Client
- STT: `stt.partial {text, stability}`, `stt.final {text}`
- Assistant: `assistant.text {text}`
- TTS streaming: `tts.chunk {seq, codec, sample_rate, payload_base64}`, `tts.end {chunks}`
- Wake: `wake.detected {keyword, confidence}`, `wake.mode_changed`, `wake.state_changed`, `wake.status`, `wake.report_ack`
- Metrics: `tts.metrics {ttfb_ms, bytes}`
- Errors: `error {code, message}`

## Activation Modes
- `ptt`: no wake detection; audio immediately buffered.
- `hotword`: buffer only after on-device wake-word trigger.
- `auto`: hybrid; respects runtime enable/disable.

## Latency Metrics (Prometheus)
- `stt_latency_ms` — STT transcription time.
- `tts_latency_ms` — TTS time-to-first-audio.
- `llm_latency_ms` — LLM completion latency.
- `llm_provider_selected`, `llm_requests_total`, `llm_fallback_total`.
- Wake: `wake_detections_total`, `wake_fp_count`, `wake_fn_count`.

## Minimal Client Flow (PTT)
1) Connect WS
2) Send `audio.chunk` frames while recording
3) Send `control.end_of_utterance`
4) Receive `stt.final` → `assistant.text` → `tts.chunk...` → `tts.end`

## Minimal Client Flow (Hotword)
1) `wake.set_mode: hotword` (and `wake.enable`)
2) Send `audio.chunk` frames; wait for `wake.detected`
3) Continue streaming audio; server buffers and returns `stt.partial`
4) Send `control.end_of_utterance` to finalize

## Error Handling
- Malformed input returns `error {code="bad_request"}`.
- Wake backend missing or disabled still allows PTT.

## References
- Wake-word details: [docs/protocol_wake.md](protocol_wake.md)
