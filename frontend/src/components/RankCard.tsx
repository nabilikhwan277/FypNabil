import { useScript } from '../i18n/ScriptContext'
import { rankFor } from '../lib/rank'
import Bi from './Bi'
import T from './T'

/** The pupil's rank with an XP bar towards the next rank. `compact` is the sidebar version. */
export default function RankCard({
  xp,
  big = false,
  compact = false,
  className = '',
}: {
  xp: number
  big?: boolean
  compact?: boolean
  className?: string
}) {
  const { t, script } = useScript()
  const r = rankFor(xp)
  const pct = Math.round(r.fraction * 100)
  const name = script === 'jawi' ? r.jawi : r.rumi
  const badge = compact ? 'h-11 w-11 text-2xl' : big ? 'h-20 w-20 text-5xl' : 'h-16 w-16 text-4xl'
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span
        aria-hidden="true"
        className={`flex shrink-0 items-center justify-center rounded-xl border border-gold/40 bg-gold-soft ${badge}`}
      >
        {r.emoji}
      </span>
      <div className="min-w-0 flex-1">
        {!compact && (
          <p className="text-sm font-extrabold text-ink-3">
            <T k="rank" /> {r.number}
          </p>
        )}
        <Bi
          rumi={r.rumi}
          jawi={r.jawi}
          as="p"
          className={`truncate font-extrabold leading-tight text-ink ${compact ? 'text-base' : big ? 'text-2xl' : 'text-xl'}`}
        />
        <div
          className={`overflow-hidden rounded-full bg-surface-3 ${compact ? 'mt-1.5 h-2.5' : 'mt-2 h-3.5'}`}
          role="progressbar"
          aria-label={t('rank')}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-valuetext={r.next ? `${name}: ${r.into} / ${r.span} XP` : name}
        >
          <div
            className="h-full rounded-full bg-gold transition-[width] duration-700"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className={`mt-1 text-ink-2 ${compact ? 'text-xs' : 'text-sm'}`}>
          {r.next ? (
            <>
              <span className="tabular-nums">{r.toNext}</span> <T k="xpToNext" /> <span aria-hidden="true">{r.next.emoji}</span>
            </>
          ) : (
            <T k="topRank" />
          )}
        </p>
      </div>
    </div>
  )
}
