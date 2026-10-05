import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

export type SoundName = 'tap' | 'correct' | 'partial' | 'wrong' | 'levelup' | 'finish'

/** [frequency in Hz, start in s, duration in s] */
type Note = readonly [number, number, number]
interface Tune {
  wave: OscillatorType
  level: number
  notes: readonly Note[]
}

// Short, soft tunes made with the Web Audio API (no audio files to load).
// "wrong" is a gentle falling pair, not a buzzer: mistakes are part of learning.
const TUNES: Record<SoundName, Tune> = {
  tap: { wave: 'triangle', level: 0.5, notes: [[880, 0, 0.07]] },
  correct: {
    wave: 'triangle',
    level: 0.9,
    notes: [
      [523.25, 0, 0.13],
      [659.25, 0.1, 0.13],
      [783.99, 0.2, 0.3],
    ],
  },
  partial: {
    wave: 'triangle',
    level: 0.8,
    notes: [
      [523.25, 0, 0.14],
      [659.25, 0.13, 0.28],
    ],
  },
  wrong: {
    wave: 'sine',
    level: 0.9,
    notes: [
      [392, 0, 0.18],
      [311.13, 0.17, 0.34],
    ],
  },
  levelup: {
    wave: 'triangle',
    level: 0.9,
    notes: [
      [523.25, 0, 0.1],
      [659.25, 0.09, 0.1],
      [783.99, 0.18, 0.1],
      [1046.5, 0.27, 0.45],
      [1318.51, 0.27, 0.45],
    ],
  },
  finish: {
    wave: 'triangle',
    level: 0.9,
    notes: [
      [392, 0, 0.12],
      [523.25, 0.13, 0.12],
      [659.25, 0.26, 0.12],
      [783.99, 0.39, 0.22],
      [659.25, 0.62, 0.12],
      [783.99, 0.75, 0.55],
      [1046.5, 0.75, 0.55],
    ],
  },
}

const VOLUME = 0.14
const KEY = 'kafa.sound'

function playTune(ctx: AudioContext, tune: Tune) {
  const t0 = ctx.currentTime + 0.02
  const master = ctx.createGain()
  master.gain.value = VOLUME * tune.level
  master.connect(ctx.destination)
  for (const [freq, start, dur] of tune.notes) {
    const osc = ctx.createOscillator()
    const env = ctx.createGain()
    osc.type = tune.wave
    osc.frequency.value = freq
    env.gain.setValueAtTime(0.0001, t0 + start)
    env.gain.exponentialRampToValueAtTime(1, t0 + start + 0.015)
    env.gain.exponentialRampToValueAtTime(0.0001, t0 + start + dur)
    osc.connect(env).connect(master)
    osc.start(t0 + start)
    osc.stop(t0 + start + dur + 0.05)
  }
}

interface SoundState {
  enabled: boolean
  toggle: () => void
  play: (name: SoundName) => void
}

const SoundContext = createContext<SoundState | null>(null)

/** Sound effects on/off (saved in localStorage, on by default). */
export function SoundProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useState(() => localStorage.getItem(KEY) !== 'off')
  const ctxRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    localStorage.setItem(KEY, enabled ? 'on' : 'off')
  }, [enabled])

  const output = useCallback((name: SoundName) => {
    try {
      const AC =
        window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!AC) return
      ctxRef.current ??= new AC()
      const ctx = ctxRef.current
      if (ctx.state === 'suspended') ctx.resume().catch(() => {})
      playTune(ctx, TUNES[name])
    } catch {
      /* no audio device: stay silent */
    }
  }, [])

  const play = useCallback(
    (name: SoundName) => {
      if (enabled) output(name)
    },
    [enabled, output],
  )
  const toggle = useCallback(() => {
    if (!enabled) output('tap') // confirm that sound is back on
    setEnabled(!enabled)
  }, [enabled, output])

  const value = useMemo(() => ({ enabled, toggle, play }), [enabled, toggle, play])
  return <SoundContext.Provider value={value}>{children}</SoundContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSound(): SoundState {
  const ctx = useContext(SoundContext)
  if (!ctx) throw new Error('useSound must be used inside <SoundProvider>')
  return ctx
}
