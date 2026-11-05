import { motion } from 'framer-motion'
import { Map as MapIcon, Rocket, RotateCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { SubjectId } from '../api/types'
import type { StringKey } from '../i18n/strings'
import Confetti from './Confetti'
import Mascot from './Mascot'
import T from './T'
import { Stars } from './ui'

export interface RoundItem {
  questionId: string
  stars: number
  percent: number
  xp: number
}

function Stat({ emoji, value, label }: { emoji: string; value: string; label: StringKey }) {
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-4 text-center">
      <p aria-hidden="true" className="text-3xl">
        {emoji}
      </p>
      <p className="mt-1 text-3xl font-extrabold text-ink tabular-nums">{value}</p>
      <T k={label} as="p" className="mt-0.5 text-sm text-ink-3" />
    </div>
  )
}

interface Props {
  items: RoundItem[]
  burst: number
  canNextLevel: boolean
  subject: SubjectId
  onPlayAgain: () => void
  onNextLevel: () => void
}

/** End-of-round screen: stars per question, totals and what to do next. */
export default function RoundSummary({ items, burst, canNextLevel, subject, onPlayAgain, onNextLevel }: Props) {
  const total = items.reduce((s, r) => s + r.stars, 0)
  const perfect = items.filter((r) => r.stars === 3).length
  const xp = items.reduce((s, r) => s + r.xp, 0)
  const good = total >= items.length * 2

  return (
    <motion.section
      aria-labelledby="summary-title"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="card relative flex flex-col items-center gap-5 p-6 text-center sm:p-8"
    >
      <Confetti burst={burst} count={80} />
      <Mascot mood={good ? 'celebrate' : 'happy'} size={150} />
      <T k={good ? 'roundDone' : 'roundKeepGoing'} as="h2" id="summary-title" className="text-3xl font-extrabold text-ink" />
      <ol className="flex flex-wrap justify-center gap-2">
        {items.map((r, i) => (
          <li key={i} className="flex flex-col items-center rounded-xl border border-line bg-surface-2 px-3 py-2">
            <span className="text-sm font-bold text-ink-3">
              <T k="question" /> {i + 1}
            </span>
            <Stars count={r.stars} size="text-xl" />
          </li>
        ))}
      </ol>
      <div className="grid w-full gap-3 sm:grid-cols-3">
        <Stat emoji="⭐" value={`${total}/${items.length * 3}`} label="roundStars" />
        <Stat emoji="🎯" value={`${perfect}/${items.length}`} label="roundPerfect" />
        <Stat emoji="💎" value={`+${xp}`} label="roundXp" />
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <button type="button" onClick={onPlayAgain} className="btn-primary">
          <RotateCcw aria-hidden="true" className="h-4.5 w-4.5" /> <T k="playAgain" />
        </button>
        {canNextLevel && (
          <button type="button" onClick={onNextLevel} className="btn-gold">
            <Rocket aria-hidden="true" className="h-4.5 w-4.5" /> <T k="goNextLevel" />
          </button>
        )}
        <Link to={`/subjek/${subject}`} className="btn-secondary">
          <MapIcon aria-hidden="true" className="h-4.5 w-4.5" /> <T k="chooseOtherTopic" />
        </Link>
      </div>
    </motion.section>
  )
}
