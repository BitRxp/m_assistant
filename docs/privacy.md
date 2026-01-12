# Security & Privacy Review

## Scope
- Backend WebSocket gateway (FastAPI) and demo web client.
- Local SQLite memory store; optional cloud LLM providers via proxy.
- Audio flows: microphone PCM16 → STT → dialog → LLM → TTS.

## Threat Model (high level)
- **Actors:** legitimate user, passive network observer, active MITM, compromised client, compromised backend host, rogue cloud LLM.
- **Assets:** raw audio, transcripts, embeddings, turns DB, credentials (LLM/TTS keys), system prompts, model outputs.
- **Trust boundaries:** browser ⇄ backend WS; backend ⇄ cloud LLM/TTS; local disk (SQLite, logs).

## Data Handling & Minimization
- Avoid logging raw audio and full transcripts by default; log only high-level events/metrics.
- PII: treat transcripts as potentially sensitive; store locally by default; make cloud forwarding opt-in.
- Memory: SQLite file kept local; embeddings derived from text (same sensitivity); consider full-disk encryption.
- Retention: add TTL/cleanup jobs for turns/facts/summaries (future work). For PoC, manual cleanup acceptable.

## Credentials & Secrets
- Keep API keys in environment variables (`.env`, not committed).
- Never echo secrets in logs.
- For CI, use repo secrets and least-privilege tokens.

## Transport
- Use HTTPS/WSS in production; for PoC localhost is plain WS/HTTP. If remote, put behind TLS terminator/reverse proxy.
- Validate certs when calling cloud providers (default HTTP clients already do).

## Storage Protection
- SQLite: place on encrypted disk/volume when possible.
- Backups: include SQLite and embeddings only on trusted storage; encrypt backups.

## Logging & Observability
- Structured logs only for events; avoid payloads.
- Prometheus metrics already available at `/metrics`; ensure it is not exposed publicly without auth.
- Add sampling/redaction for errors if payloads may leak PII.

## Cloud Opt-in
- Default to local STT/TTS/LLM when possible; cloud routes should require an explicit flag.
- UI should signal when a cloud provider is in use.

## Checklist
- [ ] TLS enabled in non-local deployments.
- [ ] `.env` present; no secrets in repo.
- [ ] `/metrics` restricted (auth or network).
- [ ] Logging level not DEBUG in prod; no raw audio/text in logs.
- [ ] SQLite on encrypted disk/volume.
- [ ] Cloud provider usage is opt-in and documented.
- [ ] Keys rotated regularly; stored in env/secret store.
- [ ] Retention policy documented; manual cleanup instructions.

## Incident Response (PoC-level)
- Revoke/regenerate keys on suspicion.
- Rotate `.env`, restart services.
- Purge local DB if required; redeploy.

## Future Hardening
- AuthN/Z for WS and /metrics.
- Per-user isolation and multi-tenant considerations.
- Client-side VAD to reduce unnecessary audio transmission.
- Differential logging policies per environment (dev/stage/prod).
