import { motion, useReducedMotion } from 'framer-motion'
import { ArrowLeft, ArrowRight, ChevronRight, House, RotateCcw } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
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
          className={i < count ? 'drop-shadow-sm' : 'opacity-30 grayscale'}
        >
          ⭐
        </motion.span>
      ))}
    </span>
  )
}

/** Progress bar with a visible percentage (never colour alone). */
export function MasteryBar({
  value,
  className = '',
  color = 'bg-primary',
  label,
  showValue = true,
}: {
  value: number
  className?: string
  color?: string
  label?: string
  showValue?: boolean
}) {
  const { t } = useScript()
  const pct = toPct(value)
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div
        className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-3"
        role="progressbar"
        aria-label={label ?? t('mastery')}
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`h-full rounded-full ${color} transition-[width] duration-700`} style={{ width: `${pct}%` }} />
      </div>
      {showValue && <span className="w-10 text-end text-sm font-bold text-ink tabular-nums">{pct}%</span>}
    </div>
  )
}

/** Circular progress (e.g. subject mastery) with content in the middle. */
export function ProgressRing({
  value,
  size = 96,
  stroke = 10,
  color = 'var(--primary)',
  track = 'var(--surface-3)',
  label,
  decorative = false,
  children,
}: {
  value: number
  size?: number
  stroke?: number
  /** Any CSS colour, including var(--token). */
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
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" style={{ stroke: track }} strokeWidth={stroke} />
        {pct > 0 && (
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            style={{ stroke: color }}
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
  const Icon = back ? ArrowLeft : ArrowRight
  return <Icon aria-hidden="true" className="h-4.5 w-4.5 shrink-0 rtl:-scale-x-100" />
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

/** Score as a coloured pill with the number (green ≥ 80%, amber ≥ 50%, red below). `value` is 0–100. */
export function ScorePill({ value, className = '' }: { value: number; className?: string }) {
  const pct = Math.round(value)
  const cls = pct >= 80 ? 'bg-primary-soft text-primary-ink' : pct >= 50 ? 'bg-accent-soft text-accent-ink' : 'bg-danger-soft text-danger-ink'
  return <span className={`inline-flex min-w-12 shrink-0 justify-center rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${cls} ${className}`}>{pct}%</span>
}

export interface Crumb {
  label: ReactNode
  to?: string
}

/**
 * Back button plus "Utama › Tajwid › Mad Badal" trail. The back button is big for
 * young pupils; the trail shows where they are and lets them jump up a level.
 */
export function PageNav({ back, crumbs, children }: { back: string; crumbs: Crumb[]; children?: ReactNode }) {
  const { t } = useScript()
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <Link to={back} className="btn-secondary min-h-10 rounded-full px-4 text-sm">
        <Arrow back /> <T k="back" />
      </Link>
      <nav aria-label={t('breadcrumb')} className="min-w-0 flex-1">
        <ol className="flex flex-wrap items-center gap-1 text-sm font-semibold text-ink-3">
          {crumbs.map((c, i) => (
            <li key={i} className="flex min-w-0 items-center gap-1">
              {i > 0 && <ChevronRight aria-hidden="true" className="h-4 w-4 shrink-0 rtl:-scale-x-100" />}
              {c.to ? (
                <Link to={c.to} className="flex items-center gap-1.5 rounded-md px-1 underline-offset-4 hover:text-primary-ink hover:underline">
                  {i === 0 && <House aria-hidden="true" className="h-4 w-4" />}
                  {c.label}
                </Link>
              ) : (
                <span aria-current="page" className="truncate rounded-full bg-gold-soft px-2.5 py-0.5 text-ink">
                  {c.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
      {children}
    </div>
  )
}

/** Loading state: Bulan thinking. */
export function Spinner({ label }: { label?: ReactNode }) {
  return (
    <div role="status" className="flex flex-col items-center gap-2 py-12 text-ink-2">
      <Mascot mood="thinking" size={92} className="drop-shadow-md" />
      <span className="font-bold">{label ?? <T k="loading" />}</span>
    </div>
  )
}

/** Friendly error with a retry button (never a raw stack trace). */
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-2xl border border-danger/30 bg-surface p-5 text-center shadow-md sm:flex-row sm:text-start"
    >
      <Mascot mood="encourage" size={80} className="shrink-0 drop-shadow-md" />
      <div className="min-w-0 flex-1">
        <T k="loadError" as="p" className="text-lg font-extrabold text-danger-ink" />
        {message && <p className="mt-1 break-words text-ink-2">{message}</p>}
        {onRetry && (
          <button type="button" onClick={onRetry} className="btn-secondary mt-3">
            <RotateCcw aria-hidden="true" className="h-4.5 w-4.5" /> <T k="tryAgain" />
          </button>
        )}
      </div>
    </div>
  )
}
