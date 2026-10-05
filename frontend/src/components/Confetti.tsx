import { motion, useReducedMotion } from 'framer-motion'
import { useMemo } from 'react'

const COLORS = ['#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#0ea5e9', '#facc15', '#f97316']

/** Small deterministic PRNG so a given burst always looks the same. */
function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Confetti burst from the centre of the parent (which must be `relative`).
 * Change `burst` to fire again. Renders nothing for reduced-motion users.
 */
export default function Confetti({ burst = 1, count = 40 }: { burst?: number; count?: number }) {
  const reduce = useReducedMotion()
  const pieces = useMemo(() => {
    const rnd = mulberry32(burst * 7919 + count)
    return Array.from({ length: count }, (_, i) => ({
      x: (rnd() - 0.5) * 640,
      up: -(rnd() * 260 + 120),
      rot: rnd() * 720 - 360,
      delay: rnd() * 0.25,
      w: 6 + rnd() * 8,
      round: rnd() > 0.6,
      color: COLORS[i % COLORS.length],
    }))
  }, [burst, count])

  if (reduce) return null
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-20 overflow-visible">
      {pieces.map((p, i) => (
        <motion.span
          key={`${burst}-${i}`}
          className="absolute left-1/2 top-1/2"
          style={{
            width: p.w,
            height: p.round ? p.w : p.w * 0.55,
            background: p.color,
            borderRadius: p.round ? '9999px' : '2px',
          }}
          initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
          animate={{ x: p.x, y: [0, p.up, p.up + 420], opacity: [1, 1, 0], rotate: p.rot }}
          transition={{ duration: 1.8, delay: p.delay, ease: 'easeOut' }}
        />
      ))}
    </div>
  )
}
