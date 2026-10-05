import { motion, useReducedMotion } from 'framer-motion'
import { useId, type ReactNode } from 'react'

export type Mood = 'happy' | 'thinking' | 'celebrate' | 'encourage' | 'wave'

const INK = '#1e293b'
// 5-point star centred at (60, 14)
const STAR = '60,3 62.94,9.95 70.46,10.6 64.76,15.55 66.47,22.9 60,19 53.53,22.9 55.24,15.55 49.54,10.6 57.06,9.95'
const fillBox = { transformBox: 'fill-box', transformOrigin: 'center' } as const

/**
 * "Bulan", the app's moon mascot. Purely decorative (aria-hidden): the text
 * next to it carries the meaning. Animations stop when the pupil's device
 * asks for reduced motion.
 */
export default function Mascot({ mood = 'happy', size = 96, className = '' }: { mood?: Mood; size?: number; className?: string }) {
  const reduce = useReducedMotion()
  // useId() may contain characters that are awkward inside url(#...) references.
  const gid = useId().replace(/[^a-zA-Z0-9_-]/g, '')

  const body = {
    happy: { y: [0, -6, 0] },
    wave: { y: [0, -6, 0] },
    encourage: { y: [0, -4, 0] },
    thinking: { rotate: [-3, 3, -3] },
    celebrate: { y: [0, -16, 0], rotate: [0, -5, 5, 0] },
  }[mood]

  return (
    <motion.svg
      viewBox="0 0 120 130"
      width={size}
      height={(size * 130) / 120}
      aria-hidden="true"
      className={className}
      animate={reduce ? undefined : body}
      transition={{ duration: mood === 'celebrate' ? 0.8 : 3, repeat: Infinity, ease: 'easeInOut' }}
      style={fillBox}
    >
      <defs>
        <radialGradient id={`moon-${gid}`} cx="40%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#fef3c7" />
          <stop offset="60%" stopColor="#fde047" />
          <stop offset="100%" stopColor="#fbbf24" />
        </radialGradient>
      </defs>

      {/* hat star */}
      <motion.polygon
        points={STAR}
        fill="#f59e0b"
        stroke="#fff"
        strokeWidth={1.5}
        animate={reduce ? undefined : { rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
        style={fillBox}
      />
      <line x1="60" y1="21" x2="60" y2="29" stroke="#f59e0b" strokeWidth={3} strokeLinecap="round" />

      {/* hands */}
      {mood === 'celebrate' ? (
        <>
          <circle cx="16" cy="48" r="8" fill="#fde047" stroke="#f59e0b" strokeWidth={2.5} />
          <circle cx="104" cy="48" r="8" fill="#fde047" stroke="#f59e0b" strokeWidth={2.5} />
        </>
      ) : mood === 'wave' ? (
        <>
          <circle cx="15" cy="92" r="7.5" fill="#fde047" stroke="#f59e0b" strokeWidth={2.5} />
          <motion.circle
            cx="106"
            cy="56"
            r="8"
            fill="#fde047"
            stroke="#f59e0b"
            strokeWidth={2.5}
            animate={reduce ? undefined : { rotate: [0, 25, -10, 25, 0] }}
            transition={{ duration: 1.4, repeat: Infinity, repeatDelay: 0.6 }}
            style={{ transformBox: 'view-box', transformOrigin: '96px 76px' }}
          />
        </>
      ) : (
        <>
          <circle cx="15" cy="92" r="7.5" fill="#fde047" stroke="#f59e0b" strokeWidth={2.5} />
          <circle cx="105" cy="92" r="7.5" fill="#fde047" stroke="#f59e0b" strokeWidth={2.5} />
        </>
      )}

      {/* body */}
      <circle cx="60" cy="74" r="44" fill={`url(#moon-${gid})`} stroke="#f59e0b" strokeWidth={3} />
      <circle cx="37" cy="52" r="5" fill="#f59e0b" opacity={0.22} />
      <circle cx="86" cy="58" r="4" fill="#f59e0b" opacity={0.22} />
      <circle cx="84" cy="100" r="6" fill="#f59e0b" opacity={0.22} />

      {/* eyebrows (kind face when encouraging) */}
      {mood === 'encourage' && (
        <>
          <path d="M39 58 Q45 54 51 58" stroke={INK} strokeWidth={3} fill="none" strokeLinecap="round" />
          <path d="M69 58 Q75 54 81 58" stroke={INK} strokeWidth={3} fill="none" strokeLinecap="round" />
        </>
      )}

      {/* eyes */}
      {mood === 'celebrate' ? (
        <>
          <path d="M39 72 Q45 63 51 72" stroke={INK} strokeWidth={4} fill="none" strokeLinecap="round" />
          <path d="M69 72 Q75 63 81 72" stroke={INK} strokeWidth={4} fill="none" strokeLinecap="round" />
        </>
      ) : (
        <motion.g
          animate={reduce ? undefined : { scaleY: [1, 1, 0.1, 1] }}
          transition={{ duration: 4, times: [0, 0.9, 0.95, 1], repeat: Infinity }}
          style={fillBox}
        >
          <ellipse cx={mood === 'thinking' ? 47 : 45} cy={mood === 'thinking' ? 68 : 71} rx="5.5" ry="7.5" fill={INK} />
          <ellipse cx={mood === 'thinking' ? 77 : 75} cy={mood === 'thinking' ? 68 : 71} rx="5.5" ry="7.5" fill={INK} />
          <circle cx={mood === 'thinking' ? 49 : 47} cy={mood === 'thinking' ? 65 : 68} r="2" fill="#fff" />
          <circle cx={mood === 'thinking' ? 79 : 77} cy={mood === 'thinking' ? 65 : 68} r="2" fill="#fff" />
        </motion.g>
      )}

      {/* cheeks */}
      <ellipse cx="33" cy="86" rx="7" ry="4.5" fill="#fb7185" opacity={0.55} />
      <ellipse cx="87" cy="86" rx="7" ry="4.5" fill="#fb7185" opacity={0.55} />

      {/* mouth */}
      {mood === 'celebrate' && (
        <>
          <path d="M46 86 Q60 108 74 86 Z" fill="#9f1239" />
          <ellipse cx="60" cy="97" rx="6" ry="3.5" fill="#fb7185" />
        </>
      )}
      {(mood === 'happy' || mood === 'wave') && (
        <path d="M49 88 Q60 99 71 88" stroke={INK} strokeWidth={4} fill="none" strokeLinecap="round" />
      )}
      {mood === 'encourage' && <path d="M51 90 Q60 96 69 90" stroke={INK} strokeWidth={4} fill="none" strokeLinecap="round" />}
      {mood === 'thinking' && <circle cx="63" cy="92" r="4" fill="#9f1239" />}

      {/* thought bubbles */}
      {mood === 'thinking' && (
        <g fill="#fff" stroke="#bae6fd" strokeWidth={2}>
          <circle cx="99" cy="36" r="3" />
          <circle cx="106" cy="27" r="4.5" />
          <circle cx="113" cy="15" r="6" />
        </g>
      )}
    </motion.svg>
  )
}

/** White speech bubble whose tail points to the start side (works in RTL). */
export function SpeechBubble({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`relative rounded-3xl border-2 border-sky-100 bg-white px-4 py-3 text-lg font-bold shadow-md ${className}`}>
      <span
        aria-hidden="true"
        className="absolute bottom-6 -start-[9px] h-4 w-4 rotate-45 border-b-2 border-s-2 border-sky-100 bg-white"
      />
      <div className="relative">{children}</div>
    </div>
  )
}

/** Mascot with a speech bubble next to it. */
export function MascotSay({
  mood = 'happy',
  size = 96,
  children,
  className = '',
}: {
  mood?: Mood
  size?: number
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`flex items-end gap-3 ${className}`}>
      {/* Smaller on phones so the bubble has room for the text. */}
      <Mascot mood={mood} size={size} className="h-auto shrink-0 drop-shadow-md max-sm:w-[72px]" />
      <SpeechBubble className="mb-2 min-w-0 flex-1">{children}</SpeechBubble>
    </div>
  )
}
