import { motion, useReducedMotion } from 'framer-motion'
import type { ReactNode } from 'react'
import { useScript } from '../i18n/ScriptContext'
import Mascot from './Mascot'
import T from './T'

const toPct = (v: number) => Math.round(Math.max(0, Math.min(1, v || 0)) * 100)

export function Stars({
  count,
  max = 3,
  size = 'text-3xl',
  animate = false,
}: {
  count: number
  max?: number
  size?: string
  animate?: boolean
}) {
  const { t } = useScript()
  return (
    <span className={`inline-flex gap-1 ${size}`} role="img" aria-label={`${count} / ${max} ${t('stars')}`}>
      {Array.from({ length: max }, (_, i) => (
        <motion.span
          key={i}
          aria-hidden="true"
          initial={animate ? { scale: 0, rotate: -90 } : false}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ delay: animate ? 0.25 + i * 0.25 : 0, type: 'spring', stiffness: 260, damping: 12 }}
          className={i < count ? 'drop-shadow' : 'opacity-25 grayscale'}
        >
          ⭐
        </motion.span>
      ))}
    </span>
  )
}

/** Chunky progress bar with a visible percentage (never colour alone). */
export function MasteryBar({
  value,
  className = '',
  color = 'bg-emerald-500',
  label,
}: {
  value: number
  className?: string
  color?: string
  label?: string
}) {
  const { t } = useScript()
  const pct = toPct(value)
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className="h-4 flex-1 overflow-hidden rounded-full bg-slate-200 shadow-inner"
        role="progressbar"
        aria-label={label ?? t('mastery')}
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`relative h-full rounded-full ${color} transition-[width] duration-700`} style={{ width: `${pct}%` }}>
          <span className="absolute inset-x-2 top-0.5 h-1 rounded-full bg-white/40" />
        </div>
      </div>
      <span className="w-12 text-end text-sm font-black tabular-nums">{pct}%</span>
    </div>
  )
}

/** Circular progress (e.g. subject mastery) with content in the middle. */
export function ProgressRing({
  value,
  size = 96,
  stroke = 10,
  color = '#10b981',
  track = '#e2e8f0',
  label,
  decorative = false,
  children,
}: {
  value: number
  size?: number
  stroke?: number
  color?: string
  track?: string
  label?: string
  /** Hide from screen readers when the percentage is already shown as text nearby. */
  decorative?: boolean
  children?: ReactNode
}) {
  const { t } = useScript()
  const reduce = useReducedMotion()
  const pct = toPct(value)
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const offset = c * (1 - pct / 100)
  const a11y = decorative
    ? ({ 'aria-hidden': true } as const)
    : ({ role: 'img', 'aria-label': `${label ?? t('mastery')}: ${pct}%` } as const)
  return (
    <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }} {...a11y}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="#fff" stroke={track} strokeWidth={stroke} />
        {pct > 0 && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            initial={{ strokeDashoffset: reduce ? offset : c }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
        {children}
      </div>
    </div>
  )
}

/** Decorative arrow that flips in right-to-left (Jawi) mode. */
export function Arrow({ back = false }: { back?: boolean }) {
  return (
    <span aria-hidden="true" className="inline-block rtl:rotate-180">
      {back ? '←' : '▶'}
    </span>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

/** Loading state: Bulan thinking. */
export function Spinner({ label }: { label?: ReactNode }) {
  return (
    <div role="status" className="flex flex-col items-center gap-2 py-10 text-slate-700">
      <Mascot mood="thinking" size={100} className="drop-shadow-md" />
      <span className="text-lg font-black">{label ?? <T k="loading" />}</span>
    </div>
  )
}

/** Friendly error with a retry button. */
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="card flex flex-col items-center gap-3 text-center ring-2 ring-rose-200 sm:flex-row sm:text-start"
    >
      <Mascot mood="encourage" size={88} className="shrink-0 drop-shadow-md" />
      <div className="min-w-0 flex-1">
        <p className="text-xl font-black text-rose-800">
          <T k="loadError" />
        </p>
        {message && <p className="mt-1 break-words text-slate-700">{message}</p>}
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn-secondary mt-3">
            <span aria-hidden="true">🔄</span> <T k="tryAgain" />
          </button>
        )}
      </div>
    </div>
  )
}
