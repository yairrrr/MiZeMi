// Game sound effects, synthesized with the Web Audio API: no audio files to
// download or license. Everything is best effort — a browser without Web
// Audio, or one that has not been unlocked by a tap yet, simply stays silent.

const STORAGE_KEY = 'mizemi.sound'

type AudioContextConstructor = typeof AudioContext

let context: AudioContext | null = null
let noise: AudioBuffer | null = null
let muted = readMuted()
const listeners = new Set<() => void>()

function readMuted(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'off'
  } catch {
    return false
  }
}

export function isMuted(): boolean {
  return muted
}

export function setMuted(next: boolean): void {
  muted = next
  try {
    window.localStorage.setItem(STORAGE_KEY, next ? 'off' : 'on')
  } catch {
    // Private mode or blocked storage: the choice lasts for this page only.
  }
  if (next) void context?.suspend().catch(() => {})
  else void context?.resume().catch(() => {})
  listeners.forEach((listener) => listener())
}

export function subscribeMuted(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Browsers only start audio from a user gesture; call from one. */
export function unlockAudio(): void {
  const audio = getContext()
  if (audio !== null && audio.state === 'suspended' && !muted) {
    void audio.resume().catch(() => {})
  }
}

function getContext(): AudioContext | null {
  if (context !== null) return context
  const Constructor: AudioContextConstructor | undefined =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: AudioContextConstructor }).webkitAudioContext
  if (Constructor === undefined) return null
  try {
    context = new Constructor()
  } catch {
    return null
  }
  return context
}

/** A running context when sound is on, otherwise null. */
function ready(): AudioContext | null {
  if (muted) return null
  const audio = getContext()
  return audio !== null && audio.state === 'running' ? audio : null
}

function noiseBuffer(audio: AudioContext): AudioBuffer {
  if (noise === null) {
    noise = audio.createBuffer(1, audio.sampleRate, audio.sampleRate)
    const data = noise.getChannelData(0)
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1
  }
  return noise
}

/** One filtered noise burst — the building block of ticks and claps. */
function burst(audio: AudioContext, destination: AudioNode, at: number, frequency: number, q: number, peak: number, length: number) {
  const source = audio.createBufferSource()
  source.buffer = noiseBuffer(audio)
  const filter = audio.createBiquadFilter()
  filter.type = 'bandpass'
  filter.frequency.value = frequency
  filter.Q.value = q
  const gain = audio.createGain()
  gain.gain.setValueAtTime(0.0001, at)
  gain.gain.exponentialRampToValueAtTime(peak, at + 0.002)
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length)
  source.connect(filter).connect(gain).connect(destination)
  source.start(at, Math.random() * 0.9, length + 0.02)
}

/** Soft UI blip for button presses. */
export function playClick(): void {
  const audio = ready()
  if (audio === null) return
  const now = audio.currentTime
  const oscillator = audio.createOscillator()
  oscillator.type = 'triangle'
  oscillator.frequency.setValueAtTime(620, now)
  oscillator.frequency.exponentialRampToValueAtTime(940, now + 0.05)
  const gain = audio.createGain()
  gain.gain.setValueAtTime(0.0001, now)
  gain.gain.exponentialRampToValueAtTime(0.12, now + 0.006)
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.09)
  oscillator.connect(gain).connect(audio.destination)
  oscillator.start(now)
  oscillator.stop(now + 0.1)
}

let tock = false

/** Clock tick, alternating tick/tock; sharper and louder when time is short. */
export function playTick(urgent = false): void {
  const audio = ready()
  if (audio === null) return
  tock = !tock
  const frequency = (urgent ? 3400 : 2600) * (tock ? 0.78 : 1)
  burst(audio, audio.destination, audio.currentTime, frequency, 6, urgent ? 0.55 : 0.32, 0.035)
}

/** Short low chime when the question clock runs out. */
export function playTimeUp(): void {
  const audio = ready()
  if (audio === null) return
  const now = audio.currentTime
  for (const [frequency, delay] of [[523.25, 0], [392, 0.14]] as const) {
    const oscillator = audio.createOscillator()
    oscillator.type = 'sine'
    oscillator.frequency.value = frequency
    const gain = audio.createGain()
    gain.gain.setValueAtTime(0.0001, now + delay)
    gain.gain.exponentialRampToValueAtTime(0.18, now + delay + 0.01)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + 0.5)
    oscillator.connect(gain).connect(audio.destination)
    oscillator.start(now + delay)
    oscillator.stop(now + delay + 0.55)
  }
}

/** A few seconds of crowd applause: hundreds of claps that swell and fade. */
export function playApplause(seconds = 4): void {
  const audio = ready()
  if (audio === null) return
  const now = audio.currentTime + 0.05
  const master = audio.createGain()
  master.gain.value = 0.9
  master.connect(audio.destination)

  // Room wash under the individual claps.
  const wash = audio.createBufferSource()
  wash.buffer = noiseBuffer(audio)
  wash.loop = true
  const washFilter = audio.createBiquadFilter()
  washFilter.type = 'bandpass'
  washFilter.frequency.value = 1500
  washFilter.Q.value = 0.6
  const washGain = audio.createGain()
  washGain.gain.setValueAtTime(0.0001, now)
  washGain.gain.exponentialRampToValueAtTime(0.06, now + 0.4)
  washGain.gain.setValueAtTime(0.06, now + seconds * 0.55)
  washGain.gain.exponentialRampToValueAtTime(0.0001, now + seconds)
  wash.connect(washFilter).connect(washGain).connect(master)
  wash.start(now)
  wash.stop(now + seconds + 0.1)

  // Density rises quickly, holds, then thins out like a real crowd.
  const claps = Math.round(seconds * 70)
  for (let i = 0; i < claps; i++) {
    const t = Math.pow(Math.random(), 1.35) * seconds
    const envelope = Math.min(1, t / 0.35) * (t > seconds * 0.55 ? Math.max(0.05, 1 - (t - seconds * 0.55) / (seconds * 0.45)) : 1)
    if (Math.random() > envelope) continue
    burst(audio, master, now + t, 900 + Math.random() * 1800, 1.2 + Math.random() * 1.5, 0.08 + Math.random() * 0.14, 0.018 + Math.random() * 0.03)
  }
}

let installed = false

/**
 * Unlocks audio on the first gesture and adds a click sound to every enabled
 * button on the page, so new buttons get it without per-component wiring.
 */
export function installSoundEffects(): void {
  if (installed || typeof window === 'undefined') return
  installed = true
  const unlock = () => unlockAudio()
  window.addEventListener('pointerdown', unlock, { capture: true, passive: true })
  window.addEventListener('keydown', unlock, { capture: true, passive: true })
  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('button') : null
    if (target !== null && !target.disabled && !target.hasAttribute('data-silent')) {
      playClick()
    }
  }, { capture: true })
}
