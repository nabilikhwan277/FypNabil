import { useScript } from '../i18n/ScriptContext'
import { rankFor } from '../lib/rank'
import Bi from './Bi'
import T from './T'

/** The pupil's rank with an XP bar towards the next rank. */
export default function RankCard({ xp, big = false, className = '' }: { xp: number; big?: boolean; className?: string }) {
  const { t, script } = useScript()
  const r = rankFor(xp)
  const pct = Math.round(r.fraction * 100)
  const name = script === 'jawi' ? r.jawi : r.rumi
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span
        aria-hidden="true"
        className={`flex shrink-0 items-center justify-center rounded-2xl bg-amber-100 shadow ring-4 ring-white ${
          big ? 'h-20 w-20 text-5xl' : 'h-16 w-16 text-4xl'
        }`}
      >
        {r.emoji}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-slate-600">
          <T k="rank" /> {r.number}
        </p>
        <Bi rumi={r.rumi} jawi={r.jawi} as="p" className={`font-black leading-tight ${big ? 'text-2xl' : 'text-xl'}`} />
        <div
          className="mt-2 h-4 overflow-hidden rounded-full bg-slate-200 shadow-inner"
          role="progressbar"
          aria-label={t('rank')}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-valuetext={r.next ? `${name}: ${r.into} / ${r.span} XP` : name}
        >
          <div
            className="h-full rounded-full bg-linear-to-r from-amber-300 to-amber-500 transition-[width] duration-700 rtl:bg-linear-to-l"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="mt-1 text-sm font-bold text-slate-700">
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
