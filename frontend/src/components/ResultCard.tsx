import { motion } from 'framer-motion'
import {
  BookOpen,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  CircleQuestionMark,
  CircleX,
  Footprints,
  Library,
  Rocket,
  Target,
  Trophy,
} from 'lucide-react'
import type { ReactNode } from 'react'
import type { Assessment } from '../api/types'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { useResearcherMode } from '../hooks/useResearcherMode'
import { useScript } from '../i18n/ScriptContext'
import type { StringKey } from '../i18n/strings'
import { useStudent } from '../session/StudentContext'
import Bi from './Bi'
import Confetti from './Confetti'
import Mascot, { type Mood } from './Mascot'
import T from './T'
import { Arrow, Stars } from './ui'

const ACTION_LABEL: Record<string, string> = {
  get_question: '📋 get_question',
  search_notes: '🔎 search_notes',
  score_rubric: '✅ score_rubric',
  get_history: '🧠 get_history',
  generate_feedback: '💬 generate_feedback',
}

// Stars are 1-3 (one star for trying).
const TONE: Record<number, { title: StringKey; mood: Mood }> = {
  3: { title: 'resultTitle3', mood: 'celebrate' },
  2: { title: 'resultTitle2', mood: 'happy' },
  1: { title: 'resultTitle1', mood: 'encourage' },
}

/** One explanation block. On phones the less urgent ones start folded (progressive disclosure). */
function Section({ icon, tone, title, open, children }: { icon: ReactNode; tone: string; title: StringKey; open: boolean; children: ReactNode }) {
  return (
    <details open={open} className="group card p-0">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 sm:px-6 [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${tone}`}>
          {icon}
        </span>
        <T k={title} as="h3" className="flex-1 text-lg font-extrabold text-ink" />
        <ChevronDown aria-hidden="true" className="h-5 w-5 text-ink-3 transition group-open:rotate-180" />
      </summary>
      <div className="px-5 pb-5 sm:px-6">{children}</div>
    </details>
  )
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

/** Result → explanation → action, in words a Tahun 5 pupil understands. */
export default function ResultCard({ result, burst, lastInRound, onContinue, onNextLevel, onReadNote }: Props) {
  const { script } = useScript()
  const { student } = useStudent()
  const researcher = useResearcherMode()
  const wide = useMediaQuery('(min-width: 768px)')
  const fb = result.feedback
  const tone = TONE[fb.stars] ?? TONE[1]
  const good = result.criteria.filter((c) => c.met === 'ya')

  return (
    <motion.section aria-labelledby="result-title" aria-live="polite" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-4">
      {/* RESULT */}
      <div className="flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <h2 id="result-title" className="text-2xl font-extrabold text-ink sm:text-3xl">
            <T k={tone.title} />
            {script === 'jawi' ? '،' : ','} {student?.name}! <span aria-hidden="true">{fb.stars === 3 ? '🎉' : fb.stars === 2 ? '👍' : '💪'}</span>
          </h2>
          <Bi rumi={fb.encouragement.rumi} jawi={fb.encouragement.jawi} as="p" className="mt-1 text-ink-2" />
        </div>
        <Mascot mood={tone.mood} size={92} className="hidden shrink-0 drop-shadow-md sm:block" />
      </div>

      <div className="card-brand flex flex-wrap items-center gap-x-6 gap-y-4">
        {fb.stars === 3 && <Confetti burst={burst} />}
        <span aria-hidden="true" className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-white/10">
          <Trophy className="h-9 w-9 text-gold" />
        </span>
        <div>
          <T k="yourScore" as="p" className="text-sm font-semibold text-on-brand-2" />
          <p className="text-4xl font-extrabold tabular-nums">
            {fb.score} / {fb.max_marks}
          </p>
        </div>
        <p className="inline-flex items-center gap-2 rounded-full bg-gold px-4 py-2 font-extrabold text-on-gold">
          <Target aria-hidden="true" className="h-4.5 w-4.5" />
          <Bi rumi={fb.verdict.rumi} jawi={fb.verdict.jawi} />
        </p>
        <div className="flex items-center gap-3 sm:ms-auto">
          <Stars count={fb.stars} size="text-2xl" animate />
          <motion.span
            initial={{ y: 8, opacity: 0, scale: 0.7 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            transition={{ delay: 0.9, type: 'spring', stiffness: 300, damping: 14 }}
            className="rounded-full bg-white/15 px-3 py-1.5 font-bold"
          >
            <span aria-hidden="true">💎 </span>+{fb.xp_gained} XP
          </motion.span>
        </div>
      </div>

      {/* EXPLANATION */}
      <div className="grid items-start gap-4 md:grid-cols-2">
        <Section icon={<CircleCheck className="h-5 w-5" />} tone="bg-primary-soft text-primary-ink" title="didWell" open={wide}>
          {good.length ? (
            <ul className="flex flex-col gap-2">
              {good.map((c) => (
                <li key={c.criterion} className="flex gap-2 text-ink">
                  <CircleCheck aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  <span dir="auto">{c.criterion}</span>
                </li>
              ))}
            </ul>
          ) : (
            <T k="didWellNone" as="p" className="text-ink-2" />
          )}
        </Section>

        <Section icon={<Target className="h-5 w-5" />} tone="bg-danger-soft text-danger-ink" title="whatToImprove" open>
          {fb.mistakes.length === 0 ? (
            <p className="flex gap-2 rounded-xl bg-primary-soft px-3 py-2 font-semibold text-primary-ink">
              <CircleCheck aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
              <T k="allCorrect" />
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {fb.mistakes.map((m) => (
                <li
                  key={m.criterion}
                  className={`flex gap-2 rounded-xl px-3 py-2 font-semibold ${
                    m.status === 'separa' ? 'bg-accent-soft text-accent-ink' : 'bg-danger-soft text-danger-ink'
                  }`}
                >
                  {m.status === 'separa' ? (
                    <CircleAlert aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
                  ) : (
                    <CircleX aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
                  )}
                  <Bi rumi={m.rumi} jawi={m.jawi} />
                </li>
              ))}
            </ul>
          )}
          {fb.repeated && (
            <p className="mt-3 rounded-xl border border-accent/40 bg-accent-soft px-3 py-2 font-semibold text-accent-ink">
              <span aria-hidden="true">🔁 </span>
              <Bi rumi={fb.repeated.rumi} jawi={fb.repeated.jawi} />
            </p>
          )}
        </Section>

        {fb.ai_feedback?.rumi && (
          <Section icon={<CircleQuestionMark className="h-5 w-5" />} tone="bg-tajwid-soft text-tajwid-ink" title="why" open={wide}>
            <Bi rumi={fb.ai_feedback.rumi} jawi={fb.ai_feedback.jawi} as="p" className="text-ink" />
          </Section>
        )}

        <Section icon={<BookOpen className="h-5 w-5" />} tone="bg-gold-soft text-gold-ink" title="correctAnswer" open>
          <Bi
            rumi={fb.correct_answer.rumi}
            jawi={fb.correct_answer.jawi}
            as="p"
            className="rounded-xl border border-primary/25 bg-primary-soft px-4 py-3 font-semibold whitespace-pre-line text-ink"
          />
          {script === 'rumi' && fb.correct_answer.jawi && (
            <p dir="rtl" lang="ms-Arab" className="jawi mt-2 px-4 whitespace-pre-line text-ink-2">
              {fb.correct_answer.jawi}
            </p>
          )}
        </Section>

        <Section icon={<Library className="h-5 w-5" />} tone="bg-fiqh-soft text-fiqh-ink" title="basedOnNote" open={wide}>
          <dl className="flex flex-col gap-2 text-sm">
            <div className="flex flex-wrap items-baseline gap-2">
              <dt className="chip py-0.5 text-xs">
                <T k="topicLabel" />
              </dt>
              <dd className="font-semibold text-ink">
                <Bi rumi={fb.source.topic_rumi} jawi={fb.source.topic_jawi} />
              </dd>
            </div>
            <div className="flex flex-wrap items-baseline gap-2">
              <dt className="chip py-0.5 text-xs">
                <T k="source" />
              </dt>
              <dd className="text-ink-2">
                <Bi rumi={fb.source.rumi} jawi={fb.source.jawi} />
              </dd>
            </div>
          </dl>
          <button type="button" onClick={onReadNote} className="btn-secondary mt-3 min-h-10 text-sm">
            <BookOpen aria-hidden="true" className="h-4 w-4" /> <T k="readNote" />
          </button>
        </Section>

        <Section icon={<Footprints className="h-5 w-5" />} tone="bg-info-soft text-info-ink" title="yourNextStep" open={wide}>
          <Bi rumi={fb.suggestion.rumi} jawi={fb.suggestion.jawi} as="p" className="text-ink" />
        </Section>
      </div>

      {/* ACTION */}
      <div className="flex flex-wrap items-center justify-end gap-3">
        <button type="button" onClick={onReadNote} className="btn-secondary max-sm:flex-1">
          <BookOpen aria-hidden="true" className="h-4.5 w-4.5" /> <T k="reviewNote" />
        </button>
        {fb.level.unlocked && onNextLevel && (
          <button type="button" onClick={onNextLevel} className="btn-gold max-sm:flex-1">
            <Rocket aria-hidden="true" className="h-4.5 w-4.5" /> <T k="goNextLevel" />
          </button>
        )}
        <button type="button" onClick={onContinue} className="btn-primary max-sm:w-full">
          {lastInRound ? (
            <>
              <T k="seeRoundResult" /> <span aria-hidden="true">🏁</span>
            </>
          ) : (
            <>
              <T k="nextQuestion" /> <Arrow />
            </>
          )}
        </button>
      </div>

      {researcher && (
        <details className="rounded-2xl border border-line bg-surface p-4 text-ink shadow-sm">
          <summary className="cursor-pointer font-bold">
            <span aria-hidden="true">🤖 </span>
            <T k="howAiThinks" /> <span className="text-sm font-semibold text-ink-3">({(result.latency_ms / 1000).toFixed(1)} s)</span>
          </summary>
          <ol className="mt-3 flex flex-col gap-3">
            {result.trace.map((s) => (
              <li key={s.step} className="rounded-xl border border-line bg-surface-2 p-3 text-sm">
                <p>
                  <span className="font-bold text-accent-ink">Thought {s.step}:</span> {s.thought}
                </p>
                <p className="mt-1">
                  <span className="font-bold text-info-ink">Action:</span> <code className="text-primary-ink">{ACTION_LABEL[s.action] ?? s.action}</code>
                </p>
                <pre dir="auto" className="mt-1 max-h-48 overflow-auto rounded-lg border border-line bg-surface p-2 text-xs break-words whitespace-pre-wrap text-ink-2">
                  <span className="font-bold text-primary-ink">Observation: </span>
                  {JSON.stringify(s.observation, null, 1)}
                </pre>
              </li>
            ))}
          </ol>
        </details>
      )}
    </motion.section>
  )
}
