export function downsampleLinear(input: Float32Array, inRate: number, outRate: number): Float32Array {
  if (outRate === inRate) return input
  if (outRate > inRate) {
    // Up-sampling isn't needed for our use-case; keep it simple.
    return input
  }

  const ratio = inRate / outRate
  const outLength = Math.floor(input.length / ratio)
  const output = new Float32Array(outLength)

  for (let i = 0; i < outLength; i++) {
    const pos = i * ratio
    const idx = Math.floor(pos)
    const frac = pos - idx
    const a = input[idx] ?? 0
    const b = input[idx + 1] ?? a
    output[i] = a + (b - a) * frac
  }

  return output
}

export function floatToPcm16LE(input: Float32Array): Uint8Array {
  const out = new Uint8Array(input.length * 2)
  const view = new DataView(out.buffer)

  for (let i = 0; i < input.length; i++) {
    let s = input[i]
    if (s > 1) s = 1
    if (s < -1) s = -1
    const v = Math.round(s * 32767)
    view.setInt16(i * 2, v, true)
  }

  return out
}
