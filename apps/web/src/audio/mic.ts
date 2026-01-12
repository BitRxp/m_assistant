import { downsampleLinear, floatToPcm16LE } from './resample'

export class MicStreamer {
  private audioContext: AudioContext | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private processor: ScriptProcessorNode | null = null
  private mediaStream: MediaStream | null = null

  private readonly targetSampleRate: number
  private readonly onPcm16Chunk: (pcm16: Uint8Array) => void

  constructor(opts: { targetSampleRate: number; onPcm16Chunk: (pcm16: Uint8Array) => void }) {
    this.targetSampleRate = opts.targetSampleRate
    this.onPcm16Chunk = opts.onPcm16Chunk
  }

  async start(): Promise<void> {
    if (this.audioContext) return

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })

    const audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(stream)

    // 4096 is a decent compromise between CPU and latency
    const processor = audioContext.createScriptProcessor(4096, 1, 1)

    processor.onaudioprocess = (ev) => {
      const input = ev.inputBuffer.getChannelData(0)
      const copied = new Float32Array(input.length)
      copied.set(input)

      const down = downsampleLinear(copied, audioContext.sampleRate, this.targetSampleRate)
      const pcm16 = floatToPcm16LE(down)
      this.onPcm16Chunk(pcm16)
    }

    source.connect(processor)
    processor.connect(audioContext.destination)

    this.mediaStream = stream
    this.audioContext = audioContext
    this.source = source
    this.processor = processor
  }

  stop(): void {
    try {
      this.processor?.disconnect()
      this.source?.disconnect()
      this.audioContext?.close()
    } catch {
      // ignore
    }

    if (this.mediaStream) {
      for (const t of this.mediaStream.getTracks()) t.stop()
    }

    this.processor = null
    this.source = null
    this.audioContext = null
    this.mediaStream = null
  }
}
