export type ActivationMode = 'ptt' | 'hotword' | 'auto'

export type ClientMessage =
  | {
      type: 'audio.chunk'
      session_id?: string
      seq?: number
      codec?: string
      sample_rate?: number
      payload_base64: string
    }
  | { type: 'control.end_of_utterance'; session_id?: string }
  | { type: 'tts.request'; text: string }
  | { type: 'wake.set_mode'; mode: ActivationMode }
  | { type: 'wake.enable' }
  | { type: 'wake.disable' }
  | { type: 'wake.get_status' }
  | { type: 'wake.report_false_positive' }
  | { type: 'wake.report_false_negative' }

export type ServerMessage = {
  type: string
  [k: string]: any
}

export class WsGatewayClient {
  private ws: WebSocket | null = null
  private seq = 0

  onOpen: (() => void) | null = null
  onClose: (() => void) | null = null
  onError: ((e: unknown) => void) | null = null
  onMessage: ((msg: ServerMessage) => void) | null = null

  constructor(private url: string) {}

  async connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return

    await new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(this.url)
      this.ws = ws

      ws.onopen = () => {
        this.onOpen?.()
        resolve()
      }
      ws.onclose = () => {
        this.onClose?.()
      }
      ws.onerror = (e) => {
        this.onError?.(e)
        reject(e)
      }
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(String(evt.data)) as ServerMessage
          this.onMessage?.(msg)
        } catch (e) {
          this.onError?.(e)
        }
      }
    })
  }

  close(): void {
    try {
      this.ws?.close()
    } finally {
      this.ws = null
    }
  }

  async send(msg: ClientMessage): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error('WebSocket not open')
    this.ws.send(JSON.stringify(msg))
  }

  sendAudioChunk(params: { sessionId: string; pcm16: Uint8Array; sampleRate: number }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return

    this.seq += 1
    const payload_base64 = WsGatewayClient.bytesToBase64(params.pcm16)
    const msg: ClientMessage = {
      type: 'audio.chunk',
      session_id: params.sessionId,
      seq: this.seq,
      codec: 'pcm16',
      sample_rate: params.sampleRate,
      payload_base64,
    }

    this.ws.send(JSON.stringify(msg))
  }

  static bytesToBase64(bytes: Uint8Array): string {
    // Avoid stack overflow for large arrays
    const chunkSize = 0x8000
    let binary = ''
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const sub = bytes.subarray(i, i + chunkSize)
      binary += String.fromCharCode(...sub)
    }
    return btoa(binary)
  }

  static base64ToBytes(b64: string): Uint8Array {
    const bin = atob(b64)
    const out = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
    return out
  }
}
