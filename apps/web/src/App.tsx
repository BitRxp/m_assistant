import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties } from 'react'
import { MicStreamer } from './audio/mic.ts'
import { WavStreamPlayer } from './audio/ttsPlayer.ts'
import { WsGatewayClient, type ActivationMode, type ServerMessage } from './ws/client'

const srOnly: CSSProperties = {
  position: 'absolute',
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  borderWidth: 0,
}

function prettyJson(v: unknown): string {
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

export function App() {
  const defaultWsUrl = useMemo(() => {
    const host = window.location.hostname || '127.0.0.1'
    return `ws://${host}:8000/ws`
  }, [])

  const [wsUrl, setWsUrl] = useState(defaultWsUrl)
  const [sessionId, setSessionId] = useState('web')

  const [connected, setConnected] = useState(false)
  const [recording, setRecording] = useState(false)

  const [handsFree, setHandsFree] = useState(false)
  const [autoEnd, setAutoEnd] = useState(false)
  const [silenceMs, setSilenceMs] = useState(900)
  const [levelThreshold, setLevelThreshold] = useState(700)

  const [activationMode, setActivationMode] = useState<ActivationMode>('auto')
  const [wakeEnabled, setWakeEnabled] = useState(true)

  const [sttPartial, setSttPartial] = useState('')
  const [sttFinal, setSttFinal] = useState('')
  const [assistantText, setAssistantText] = useState('')
  const [lastWake, setLastWake] = useState<string>('')

  const [lastMsg, setLastMsg] = useState<ServerMessage | null>(null)
  const [errorText, setErrorText] = useState<string>('')

  const clientRef = useRef<WsGatewayClient | null>(null)
  const micRef = useRef<MicStreamer | null>(null)
  const playerRef = useRef<WavStreamPlayer | null>(null)

  const sessionIdRef = useRef(sessionId)
  useEffect(() => {
    sessionIdRef.current = sessionId
  }, [sessionId])

  const recordingRef = useRef(recording)
  useEffect(() => {
    recordingRef.current = recording
  }, [recording])

  const handsFreeRef = useRef(handsFree)
  useEffect(() => {
    handsFreeRef.current = handsFree
  }, [handsFree])

  const autoEndRef = useRef(autoEnd)
  useEffect(() => {
    autoEndRef.current = autoEnd
  }, [autoEnd])

  const silenceMsRef = useRef(silenceMs)
  useEffect(() => {
    silenceMsRef.current = silenceMs
  }, [silenceMs])

  const levelThresholdRef = useRef(levelThreshold)
  useEffect(() => {
    levelThresholdRef.current = levelThreshold
  }, [levelThreshold])

  const startMicRef = useRef<() => Promise<void>>(async () => {})
  const stopMicRef = useRef<() => void>(() => {})
  const endOfUtteranceRef = useRef<() => void>(() => {})

  const lastVoiceAtRef = useRef<number>(0)
  const utteranceActiveRef = useRef<boolean>(false)
  const playingTtsRef = useRef<boolean>(false)
  const pendingResumeRef = useRef<boolean>(false)

  const estimateLevel = useCallback((pcm16: Uint8Array): number => {
    // cheap peak estimate on PCM16LE bytes
    let peak = 0
    for (let i = 0; i + 1 < pcm16.length; i += 4) {
      const sample = (pcm16[i] | (pcm16[i + 1] << 8)) << 16 >> 16
      const abs = sample < 0 ? -sample : sample
      if (abs > peak) peak = abs
    }
    return peak
  }, [])

  useEffect(() => {
    playerRef.current = new WavStreamPlayer()
    return () => {
      playerRef.current?.close()
      playerRef.current = null
    }
  }, [])

  const connect = useCallback(async () => {
    setErrorText('')
    if (clientRef.current) {
      clientRef.current.close()
      clientRef.current = null
    }

    const client = new WsGatewayClient(wsUrl)
    clientRef.current = client

    client.onOpen = () => setConnected(true)
    client.onClose = () => setConnected(false)
    client.onError = (e) => setErrorText(String(e))

    client.onMessage = async (msg) => {
      setLastMsg(msg)
      if (msg.type === 'stt.partial') setSttPartial(msg.text ?? '')
      if (msg.type === 'stt.final') {
        setSttFinal(msg.text ?? '')
        setSttPartial('')
      }
      if (msg.type === 'assistant.text') setAssistantText(msg.text ?? '')
      if (msg.type === 'wake.detected') {
        setLastWake(`${msg.keyword ?? ''} (conf=${msg.confidence ?? 0})`)
      }

      if (msg.type === 'tts.chunk') {
        if (handsFreeRef.current && recordingRef.current && !playingTtsRef.current) {
          playingTtsRef.current = true
          pendingResumeRef.current = true
          stopMicRef.current()
        }
        const bytes = WsGatewayClient.base64ToBytes(msg.payload_base64)
        await playerRef.current?.pushWavChunk(bytes)
      }

      if (msg.type === 'tts.end') {
        playingTtsRef.current = false
        if (handsFreeRef.current && pendingResumeRef.current) {
          pendingResumeRef.current = false
          // small delay so audio tail doesn't re-trigger VAD
          setTimeout(() => {
            void startMicRef.current()
          }, 250)
        }
      }
    }

    await client.connect()

    // Sync wake settings on connect (best-effort)
    try {
      await client.send({ type: 'wake.set_mode', mode: activationMode })
      await client.send({ type: wakeEnabled ? 'wake.enable' : 'wake.disable' })
    } catch {
      // ignore
    }
  }, [activationMode, wakeEnabled, wsUrl])

  const disconnect = useCallback(() => {
    setRecording(false)
    micRef.current?.stop()
    micRef.current = null
    clientRef.current?.close()
    clientRef.current = null
    setConnected(false)
  }, [])

  const startMic = useCallback(async () => {
    setErrorText('')
    const client = clientRef.current
    if (!client) {
      setErrorText('Not connected')
      return
    }

    if (micRef.current) {
      return
    }

    const mic = new MicStreamer({
      targetSampleRate: 16000,
      onPcm16Chunk: (pcm16: Uint8Array) => {
        client.sendAudioChunk({
          sessionId: sessionIdRef.current,
          pcm16,
          sampleRate: 16000,
        })

        if (!autoEndRef.current) return

        const now = performance.now()
        const level = estimateLevel(pcm16)
        if (level >= levelThresholdRef.current) {
          utteranceActiveRef.current = true
          lastVoiceAtRef.current = now
          return
        }

        if (utteranceActiveRef.current && now - lastVoiceAtRef.current >= silenceMsRef.current) {
          utteranceActiveRef.current = false
          endOfUtteranceRef.current()
          if (handsFreeRef.current) {
            pendingResumeRef.current = true
            stopMicRef.current()
          }
        }
      },
    })

    micRef.current = mic
    try {
      await mic.start()
      setRecording(true)
    } catch (e) {
      micRef.current = null
      setErrorText('Mic error: ' + String(e))
    }
  }, [estimateLevel])

  const stopMic = useCallback(() => {
    setRecording(false)
    micRef.current?.stop()
    micRef.current = null
    utteranceActiveRef.current = false
  }, [])

  const endOfUtterance = useCallback(() => {
    const client = clientRef.current
    if (!client) return
    client.send({ type: 'control.end_of_utterance', session_id: sessionIdRef.current })
  }, [sessionId])

  useEffect(() => {
    startMicRef.current = startMic
  }, [startMic])
  useEffect(() => {
    stopMicRef.current = stopMic
  }, [stopMic])
  useEffect(() => {
    endOfUtteranceRef.current = endOfUtterance
  }, [endOfUtterance])

  const setMode = useCallback(async (mode: ActivationMode) => {
    setActivationMode(mode)
    const client = clientRef.current
    if (!client) return
    await client.send({ type: 'wake.set_mode', mode })
  }, [])

  const toggleWake = useCallback(async (enabled: boolean) => {
    setWakeEnabled(enabled)
    const client = clientRef.current
    if (!client) return
    await client.send({ type: enabled ? 'wake.enable' : 'wake.disable' })
  }, [])

  const reportFp = useCallback(() => {
    clientRef.current?.send({ type: 'wake.report_false_positive' })
  }, [])

  const reportFn = useCallback(() => {
    clientRef.current?.send({ type: 'wake.report_false_negative' })
  }, [])

  const getWakeStatus = useCallback(() => {
    clientRef.current?.send({ type: 'wake.get_status' })
  }, [])

  return (
    <div className="container">
      <div className="header">
        <div>
          <h1 className="h1">m_assistant Web PoC</h1>
          <div className="sub">Mic → WS audio.chunk → STT partial/final → TTS chunk playback</div>
        </div>
        <div className="pill">
          <span>{connected ? 'connected' : 'disconnected'}</span>
          <span>•</span>
          <span>{recording ? 'mic on' : 'mic off'}</span>
          <span>•</span>
          <span>{handsFree ? 'hands-free' : 'manual'}</span>
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div className="label">WebSocket URL</div>
              <input
                className="input"
                value={wsUrl}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setWsUrl(e.target.value)}
              />
            </div>
            <div>
              <div className="label">Session ID</div>
              <input
                className="input"
                value={sessionId}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSessionId(e.target.value)}
              />
            </div>
          </div>

          <div className="row" style={{ marginTop: 12 }}>
            {!connected ? (
              <button className="btn btn--primary" onClick={connect}>Connect</button>
            ) : (
              <button className="btn btn--ghost" onClick={disconnect}>Disconnect</button>
            )}

            {!recording ? (
              <button className="btn btn--primary" disabled={!connected} onClick={startMic}>
                Start Mic
              </button>
            ) : (
              <button className="btn" onClick={stopMic}>Stop Mic</button>
            )}

            <button className="btn" disabled={!connected} onClick={endOfUtterance}>
              End of utterance
            </button>
          </div>

          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div className="label">Hands-free</div>
              <div className="row">
                <label className="pill">
                  <input
                    aria-label="hands free"
                    type="checkbox"
                    checked={handsFree}
                    onChange={(e) => setHandsFree(e.target.checked)}
                  />
                  <span>{handsFree ? 'on' : 'off'}</span>
                </label>
              </div>
              <div className="mini" style={{ marginTop: 8 }}>
                Stops mic while TTS plays and resumes afterwards.
              </div>
            </div>

            <div>
              <div className="label">Auto end-of-utterance (silence)</div>
              <div className="row">
                <label className="pill">
                  <input
                    aria-label="auto end of utterance"
                    type="checkbox"
                    checked={autoEnd}
                    onChange={(e) => setAutoEnd(e.target.checked)}
                  />
                  <span>{autoEnd ? 'on' : 'off'}</span>
                </label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
                <label className="mini">
                  <span>silence ms</span>
                  <input
                    className="input"
                    value={String(silenceMs)}
                    inputMode="numeric"
                    onChange={(e) => setSilenceMs(Math.max(200, Number(e.target.value) || 0))}
                  />
                </label>
                <label className="mini">
                  <span>level threshold</span>
                  <input
                    className="input"
                    value={String(levelThreshold)}
                    inputMode="numeric"
                    onChange={(e) => setLevelThreshold(Math.max(50, Number(e.target.value) || 0))}
                  />
                </label>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <div className="label">Activation mode</div>
              <div className="row">
                <button
                  className={activationMode === 'ptt' ? 'btn btn--primary' : 'btn'}
                  onClick={() => setMode('ptt')}
                >
                  PTT
                </button>
                <button
                  className={activationMode === 'hotword' ? 'btn btn--primary' : 'btn'}
                  onClick={() => setMode('hotword')}
                >
                  Hotword
                </button>
                <button
                  className={activationMode === 'auto' ? 'btn btn--primary' : 'btn'}
                  onClick={() => setMode('auto')}
                >
                  Auto
                </button>
              </div>
            </div>

            <div>
              <div className="label">Wake enabled (runtime)</div>
              <div className="row">
                <label className="pill">
                  <input
                    aria-label="wake enabled"
                    type="checkbox"
                    checked={wakeEnabled}
                    onChange={(e) => void toggleWake(e.target.checked)}
                  />
                  <span>{wakeEnabled ? 'enabled' : 'disabled'}</span>
                </label>
                <button className="btn" onClick={getWakeStatus}>Get status</button>
              </div>
            </div>
          </div>

          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn" onClick={reportFp}>Report FP</button>
            <button className="btn" onClick={reportFn}>Report FN</button>
          </div>

          <div style={{ marginTop: 12 }} className="mini">
            <div><b>Wake:</b> {lastWake || '—'}</div>
            {errorText ? <div className="err"><b>Error:</b> {errorText}</div> : null}
          </div>

          {/* Improves screen-reader UX when using keyboard navigation */}
          <div style={srOnly} aria-live="polite">
            {connected ? 'connected' : 'disconnected'}
          </div>
        </div>

        <div className="card">
          <div className="kv">
            <div>
              <div className="label">STT partial</div>
              <div className="box">{sttPartial || '—'}</div>
            </div>
            <div>
              <div className="label">STT final</div>
              <div className="box">{sttFinal || '—'}</div>
            </div>
            <div>
              <div className="label">Assistant</div>
              <div className="box" style={{ minHeight: 72 }}>{assistantText || '—'}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="label">Last server message</div>
        <pre className="pre">{lastMsg ? prettyJson(lastMsg) : '—'}</pre>
      </div>
    </div>
  )
}
