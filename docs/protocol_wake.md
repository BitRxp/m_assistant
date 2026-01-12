# Wake-Word Detection Protocol

## Overview

The wake-word detection system supports multiple activation modes and runtime configuration through WebSocket messages.

## Activation Modes

Three activation modes are supported:

- **`ptt` (Push-to-Talk)**: Audio is always accumulated; no wake-word detection. User manually triggers recording.
- **`hotword`**: Audio is only accumulated after wake-word detection. System waits for keyword before listening.
- **`auto`**: Hybrid mode that supports both PTT and hotword depending on configuration.

## WebSocket Messages

### Client → Server

#### Set Activation Mode
```json
{
  "type": "wake.set_mode",
  "mode": "ptt" | "hotword" | "auto"
}
```

#### Enable/Disable Wake Detection
```json
{
  "type": "wake.enable"
}
```

```json
{
  "type": "wake.disable"
}
```

#### Get Current Status
```json
{
  "type": "wake.get_status"
}
```

#### Report False Positive
When the wake-word detector triggers incorrectly:
```json
{
  "type": "wake.report_false_positive"
}
```

#### Report False Negative
When the wake-word should have triggered but didn't:
```json
{
  "type": "wake.report_false_negative"
}
```

### Server → Client

#### Wake Detected
```json
{
  "type": "wake.detected",
  "keyword": "computer",
  "confidence": 0.95
}
```

#### Mode Changed
```json
{
  "type": "wake.mode_changed",
  "mode": "ptt" | "hotword" | "auto"
}
```

#### State Changed
```json
{
  "type": "wake.state_changed",
  "enabled": true | false
}
```

#### Status Response
```json
{
  "type": "wake.status",
  "enabled": true,
  "mode": "auto",
  "listening": true,
  "available": true
}
```

#### Report Acknowledgment
```json
{
  "type": "wake.report_ack",
  "reported": "false_positive" | "false_negative"
}
```

## Metrics

The following Prometheus metrics are exposed on `/metrics`:

- `wake_detections_total{keyword="<keyword>"}` - Total number of wake-word detections
- `wake_false_positives_total` - Manually reported false positive detections
- `wake_false_negatives_total` - Manually reported false negative (missed) detections

## Configuration

Wake-word detection is configured via environment variables:

```bash
# Enable wake-word detection
WAKE_ENABLED=true

# Backend implementation: stub | porcupine
WAKE_BACKEND=stub

# Porcupine-specific settings (when WAKE_BACKEND=porcupine)
WAKE_PORCUPINE_ACCESS_KEY=your_access_key
WAKE_PORCUPINE_KEYWORDS=computer,jarvis  # comma-separated
WAKE_PORCUPINE_SENSITIVITY=0.5  # 0.0 to 1.0
```

## Behavior by Mode

### PTT Mode
1. Audio chunks are immediately accumulated
2. Wake-word detector is bypassed
3. Client controls when to send `control.end_of_utterance`

### Hotword Mode
1. Audio chunks are processed by wake-word detector
2. Detection triggers `wake.detected` message
3. Subsequent audio is accumulated until `control.end_of_utterance`
4. After utterance ends, system resets to listening for wake-word

### Auto Mode
1. Behaves like hotword mode when wake detection is enabled
2. Falls back to PTT-like behavior when wake detection is disabled runtime

## Example Flow

### Hotword Mode
```
Client                          Server
  |                               |
  |-- wake.set_mode: hotword ---->|
  |<---- wake.mode_changed -------|
  |                               |
  |-- audio.chunk --------------->| (detecting...)
  |-- audio.chunk --------------->| (detecting...)
  |-- audio.chunk --------------->| (detecting... DETECTED!)
  |<---- wake.detected ----------|
  |                               |
  |-- audio.chunk --------------->| (accumulating)
  |<---- stt.partial -------------|
  |-- audio.chunk --------------->| (accumulating)
  |<---- stt.partial -------------|
  |                               |
  |-- control.end_of_utterance -->|
  |<---- stt.final ---------------|
  |<---- assistant.text ----------|
  |<---- tts.chunk ---------------|
  |                               | (reset to detecting)
```

### PTT Mode
```
Client                          Server
  |                               |
  |-- wake.set_mode: ptt -------->|
  |<---- wake.mode_changed -------|
  |                               |
  |-- audio.chunk --------------->| (accumulating immediately)
  |<---- stt.partial -------------|
  |-- audio.chunk --------------->| (accumulating)
  |<---- stt.partial -------------|
  |                               |
  |-- control.end_of_utterance -->|
  |<---- stt.final ---------------|
```

## Testing

Run wake-word tests:
```bash
cd apps/backend
pytest tests/test_wake_word.py -v
pytest tests/test_wake_unit.py -v
```

Tests cover:
- Stub detector triggering after threshold
- Mode switching (PTT, hotword, auto)
- Runtime enable/disable
- False positive/negative reporting
- Status queries
