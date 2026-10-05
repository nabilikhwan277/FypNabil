import { motion } from 'framer-motion'
import type { Assessment } from '../api/types'
import { useScript } from '../i18n/ScriptContext'
import Bi from './Bi'
import Confetti from './Confetti'
import Mascot, { type Mood } from './Mascot'
import T from './T'
import { Arrow, Card, Stars } from './ui'

const ACTION_LABEL: Record<string, string> = {
  get_question: '📋 get_question',
  search_notes: '🔎 search_notes',
  score_rubric: '✅ score_rubric',
  get_history: '🧠 get_history',
  generate_feedback: '💬 generate_feedback',
}

// Stars are 1-3 (one star for trying). White text on these is large and bold only.
const TONE: Record<number, { bg: string; mood: Mood }> = {
  3: { bg: 'from-emerald-600 to-teal-700', mood: 'celebrate' },
  2: { bg: 'from-sky-600 to-blue-700', mood: 'happy' },
  1: { bg: 'from-violet-600 to-purple-700', mood: 'encourage' },
}

interface Props {
  result: Assessment
  /** Confetti trigger (a new value fires a burst). */
  burst: number
  lastInRound: boolean
  onContinue: () => void
  onNextLevel?: () => void
  onReadNote: () => void
}

export default function ResultCard({ result, burst, lastInRound, onContinue, onNextLevel, onReadNote }: Props) {
  const { script } = useScript()
  const fb = result.feedback
  const tone = TONE[fb.stars] ?? TONE[1]

  return (
    <motion.section
      aria-labelledby="result-title"
      aria-live="polite"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col gap-4"
    >
      <div className={`relative rounded-3xl bg-linear-to-br ${tone.bg} p-5 text-white shadow-lg sm:p-6`}>
        {fb.stars === 3 && <Confetti burst={burst} />}
        <T k="result" as="h3" className="sr-only" />
        <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-center">
          <Mascot mood={tone.mood} size={120} className="shrink-0 drop-shadow-lg" />
          <div className="min-w-0 flex-1 text-center sm:text-start">
            <Stars count={fb.stars} size="text-5xl" animate />
            <Bi id="result-title" rumi={fb.verdict.rumi} jawi={fb.verdict.jawi} as="p" className="mt-1 text-2xl font-black sm:text-3xl" />
            <p className="mt-1 text-xl font-black">
              {fb.score} / {fb.max_marks} <T k="marks" /> · {Math.round(fb.percent)}%
            </p>
          </div>
          <motion.p
            initial={{ y: 12, opacity: 0, scale: 0.6 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            transition={{ delay: 1, type: 'spring', stiffness: 300, damping: 12 }}
            className="rounded-2xl bg-white px-4 py-2 text-2xl font-black text-ink shadow"
          >
            <span aria-hidden="true">💎 </span>+{fb.xp_gained} XP
          </motion.p>
        </div>
        <Bi
          rumi={fb.encouragement.rumi}
          jawi={fb.encouragement.jawi}
          as="p"
          className="mt-4 rounded-2xl bg-white/95 px-4 py-3 text-lg font-bold text-ink"
        />
      </div>

      <Card>
        <T k="whatToImprove" as="h3" className="mb-2 text-lg font-black" />
        {fb.mistakes.length === 0 ? (
          <p className="rounded-2xl bg-emerald-50 px-3 py-2 font-bold text-emerald-800">
            <span aria-hidden="true">✔ </span>
            <T k="allCorrect" />
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {fb.mistakes.map((m) => (
              <li key={m.criterion} className="flex gap-2 rounded-2xl bg-rose-50 px-3 py-2">
                <span aria-hidden="true">{m.status === 'separa' ? '🟡' : '❌'}</span>
                <Bi rumi={m.rumi} jawi={m.jawi} />
              </li>
            ))}
          </ul>
        )}
        {fb.repeated && (
          <p className="mt-3 rounded-2xl bg-amber-50 px-3 py-2 font-bold text-amber-900">
            <span aria-hidden="true">🔁 </span>
            <Bi rumi={fb.repeated.rumi} jawi={fb.repeated.jawi} />
          </p>
        )}
      </Card>

      <Card>
        <T k="correctAnswer" as="h3" className="mb-2 text-lg font-black" />
        <Bi
          rumi={fb.correct_answer.rumi}
          jawi={fb.correct_answer.jawi}
          as="p"
          className="rounded-2xl bg-emerald-50 px-4 py-3 text-lg whitespace-pre-line"
        />
        {script === 'rumi' && fb.correct_answer.jawi && (
          <p dir="rtl" lang="ms-Arab" className="jawi mt-2 px-4 whitespace-pre-line text-slate-700">
            {fb.correct_answer.jawi}
          </p>
        )}
        <p className="mt-2 text-sm font-bold text-slate-600">
          <span aria-hidden="true">📚 </span>
          <T k="source" />: <Bi rumi={fb.source.rumi} jawi={fb.source.jawi} />
        </p>
      </Card>

      <Card>
        <T k="nextStep" as="h3" className="mb-2 text-lg font-black" />
        <Bi rumi={fb.suggestion.rumi} jawi={fb.suggestion.jawi} as="p" className="font-bold" />
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" onClick={onContinue} className="btn-primary">
            {lastInRound ? (
              <>
                <T k="seeRoundResult" /> <span aria-hidden="true">🏁</span>
              </>
            ) : (
              <>
                <T k="continue" /> <Arrow />
              </>
            )}
          </button>
          {fb.level.unlocked && onNextLevel && (
            <button type="button" onClick={onNextLevel} className="btn-secondary">
              <span aria-hidden="true">🚀</span> <T k="goNextLevel" />
            </button>
          )}
          <button type="button" onClick={onReadNote} className="btn-secondary">
            <span aria-hidden="true">📖</span> <T k="readNote" />
          </button>
        </div>
      </Card>

      <details className="rounded-3xl bg-slate-800 p-4 text-slate-100 shadow-md">
        <summary className="cursor-pointer text-lg font-black">
          <span aria-hidden="true">🤖 </span>
          <T k="howAiThinks" /> <span className="text-sm font-normal text-slate-300">({(result.latency_ms / 1000).toFixed(1)} s)</span>
        </summary>
        <ol className="mt-3 flex flex-col gap-3">
          {result.trace.map((s) => (
            <li key={s.step} className="rounded-2xl bg-slate-700 p-3 text-sm">
              <p>
                <span className="font-black text-amber-300">Thought {s.step}:</span> {s.thought}
              </p>
              <p className="mt-1">
                <span className="font-black text-sky-300">Action:</span> <code>{ACTION_LABEL[s.action] ?? s.action}</code>
              </p>
              <pre dir="auto" className="mt-1 max-h-48 overflow-auto rounded-xl bg-slate-900 p-2 text-xs break-words whitespace-pre-wrap">
                <span className="font-black text-emerald-300">Observation: </span>
                {JSON.stringify(s.observation, null, 1)}
              </pre>
            </li>
          ))}
        </ol>
      </details>
    </motion.section>
  )
}
