type WavInfo = {
  sampleRate: number
  channels: number
  bitsPerSample: number
  dataOffset: number
}

function readFourCC(bytes: Uint8Array, offset: number): string {
  return String.fromCharCode(bytes[offset] ?? 0, bytes[offset + 1] ?? 0, bytes[offset + 2] ?? 0, bytes[offset + 3] ?? 0)
}

function parseWavHeader(bytes: Uint8Array): WavInfo {
  if (bytes.length < 44) throw new Error('WAV chunk too small')
  if (readFourCC(bytes, 0) !== 'RIFF' || readFourCC(bytes, 8) !== 'WAVE') throw new Error('Not a WAV file')

  let offset = 12
  let fmt: { channels: number; sampleRate: number; bitsPerSample: number } | null = null
  let dataOffset = -1

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)

  while (offset + 8 <= bytes.length) {
    const id = readFourCC(bytes, offset)
    const size = view.getUint32(offset + 4, true)
    const payloadOffset = offset + 8

    if (id === 'fmt ') {
      const audioFormat = view.getUint16(payloadOffset + 0, true)
      const channels = view.getUint16(payloadOffset + 2, true)
      const sampleRate = view.getUint32(payloadOffset + 4, true)
      const bitsPerSample = view.getUint16(payloadOffset + 14, true)
      if (audioFormat !== 1) throw new Error(`Unsupported WAV format: ${audioFormat}`)
      fmt = { channels, sampleRate, bitsPerSample }
    }

    if (id === 'data') {
      dataOffset = payloadOffset
      break
    }

    // Chunks are word-aligned
    offset = payloadOffset + size + (size % 2)
  }

  if (!fmt) throw new Error('WAV fmt chunk not found')
  if (dataOffset < 0) throw new Error('WAV data chunk not found')

  return {
    sampleRate: fmt.sampleRate,
    channels: fmt.channels,
    bitsPerSample: fmt.bitsPerSample,
    dataOffset,
  }
}

export class WavStreamPlayer {
  private ctx: AudioContext
  private processor: ScriptProcessorNode

  private wavInfo: WavInfo | null = null
  private queue: Float32Array[] = []
  private queueOffset = 0

  constructor() {
    this.ctx = new AudioContext({ sampleRate: 16000 })
    this.processor = this.ctx.createScriptProcessor(2048, 0, 1)

    this.processor.onaudioprocess = (e) => {
      const out = e.outputBuffer.getChannelData(0)
      out.fill(0)

      let written = 0
      while (written < out.length) {
        const cur = this.queue[0]
        if (!cur) break

        const available = cur.length - this.queueOffset
        const need = out.length - written
        const n = Math.min(available, need)

        out.set(cur.subarray(this.queueOffset, this.queueOffset + n), written)

        written += n
        this.queueOffset += n

        if (this.queueOffset >= cur.length) {
          this.queue.shift()
          this.queueOffset = 0
        }
      }
    }

    this.processor.connect(this.ctx.destination)
  }

  async pushWavChunk(bytes: Uint8Array): Promise<void> {
    // Ensure audio can start after user gesture
    if (this.ctx.state !== 'running') {
      try {
        await this.ctx.resume()
      } catch {
        // ignore
      }
    }

    let pcmBytes = bytes

    if (!this.wavInfo) {
      const info = parseWavHeader(bytes)
      this.wavInfo = info

      // We support only PCM16 mono for now.
      if (info.channels !== 1) throw new Error(`Unsupported channels: ${info.channels}`)
      if (info.bitsPerSample !== 16) throw new Error(`Unsupported bits: ${info.bitsPerSample}`)

      pcmBytes = bytes.subarray(info.dataOffset)
    }

    if (pcmBytes.length === 0) return

    // Convert PCM16LE to Float32
    const view = new DataView(pcmBytes.buffer, pcmBytes.byteOffset, pcmBytes.byteLength)
    const n = Math.floor(pcmBytes.length / 2)
    const floats = new Float32Array(n)
    for (let i = 0; i < n; i++) {
      const s = view.getInt16(i * 2, true)
      floats[i] = s / 32768
    }

    this.queue.push(floats)
  }

  close(): void {
    try {
      this.processor.disconnect()
      this.ctx.close()
    } catch {
      // ignore
    }
  }
}
