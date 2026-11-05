import { motion } from 'framer-motion'
import { BookOpen, ChartColumn, ChevronRight, CircleCheck, CircleDashed, Hourglass, Lightbulb, Play, RotateCcw, Sparkles, Target, ThumbsUp } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Topic } from '../api/types'
import Bi from '../components/Bi'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_STYLE, type SubjectStyle } from '../components/subjects'
import T from '../components/T'
import { ErrorBox, MasteryBar, PageNav, ScorePill, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { useScript } from '../i18n/ScriptContext'
import type { StringKey } from '../i18n/strings'
import { practiceTopics, recommendations, topicState, weakTopics, type TopicState } from '../lib/insights'
import { useStudent } from '../session/StudentContext'

const STATE: Record<TopicState, { key: StringKey; icon: typeof CircleCheck; chip: string; btn: string; label: StringKey; btnIcon: typeof Play }> = {
  new: { key: 'statusNew', icon: Sparkles, chip: 'bg-surface-2 text-ink-2', btn: 'btn-secondary', label: 'startBtn', btnIcon: Play },
  learning: { key: 'statusLearning', icon: CircleDashed, chip: 'bg-gold-soft text-gold-ink', btn: 'btn-gold', label: 'continueBtn', btnIcon: Play },
  mastered: { key: 'statusDone', icon: CircleCheck, chip: 'bg-primary-soft text-primary-ink', btn: 'btn-primary', label: 'review', btnIcon: RotateCcw },
}

function TopicCard({ topic, n, st, delay }: { topic: Topic; n: number; st: SubjectStyle; delay: number }) {
  const state = STATE[topicState(topic)]
  const Icon = state.icon
  const BtnIcon = state.btnIcon
  return (
    <motion.li initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay }}>
      <Link to={`/topik/${topic.id}`} className="card group flex h-full flex-col gap-3 p-4 transition hover:-translate-y-0.5 hover:shadow-lg">
        <span className="flex items-start gap-3">
          <span aria-hidden="true" className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-base font-extrabold ${st.soft} ${st.text}`}>
            {n}
          </span>
          <span className="min-w-0 flex-1">
            <Bi rumi={topic.title_rumi} jawi={topic.title_jawi} className="block leading-snug font-bold text-ink" />
            {topic.has_questions ? (
              <span className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${state.chip}`}>
                <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                <T k={state.key} />
              </span>
            ) : (
              <span className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-info-soft px-2.5 py-0.5 text-xs font-bold text-info-ink">
                <BookOpen aria-hidden="true" className="h-3.5 w-3.5" />
                <T k="readOnly" />
              </span>
            )}
          </span>
        </span>
        {topic.has_questions ? (
          <>
            <MasteryBar value={topic.mastery} color={st.bar} className="mt-auto" />
            <span className={`${state.btn} pointer-events-none min-h-10 py-1.5 text-sm`}>
              <BtnIcon aria-hidden="true" className="h-4 w-4" /> <T k={state.label} />
            </span>
          </>
        ) : (
          <span className="btn-secondary pointer-events-none mt-auto min-h-10 py-1.5 text-sm">
            <BookOpen aria-hidden="true" className="h-4 w-4" /> <T k="readNote" />
          </span>
        )}
      </Link>
    </motion.li>
  )
}

function MiniList({ topics, empty }: { topics: Topic[]; empty: StringKey }) {
  if (!topics.length) return <T k={empty} as="p" className="py-2 text-sm text-ink-3" />
  return (
    <ul className="flex flex-col gap-1">
      {topics.map((tp) => (
        <li key={tp.id}>
          <Link to={`/topik/${tp.id}`} className="flex items-center gap-3 rounded-xl px-2 py-2 transition hover:bg-surface-2">
            <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" />
            <ScorePill value={tp.mastery * 100} />
            <ChevronRight aria-hidden="true" className="h-4.5 w-4.5 shrink-0 text-ink-3 rtl:-scale-x-100" />
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default function SubjectPage() {
  const { subjectId } = useParams()
  const { student } = useStudent()
  const { t } = useScript()
  const { data, error, loading, reload } = useAsync(() => api.subjects(student!.id), [student!.id])
  const subject = data?.find((s) => s.id === subjectId)

  if (loading) return <Spinner />
  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (!subject) return <ErrorBox message={t('subjectNotFound')} />
  const st = SUBJECT_STYLE[subject.id]

  const practice = practiceTopics([subject])
  const count = (s: TopicState) => practice.filter((tp) => topicState(tp) === s).length
  const tried = practice.filter((tp) => tp.attempts > 0)
  const strongest = [...tried].sort((a, b) => b.mastery - a.mastery)[0]
  const weak = weakTopics(practice)
  const done = practice.filter((tp) => topicState(tp) === 'mastered').sort((a, b) => b.mastery - a.mastery)
  const rec = recommendations(practice, 1)[0]
  let n = 0

  return (
    <section aria-labelledby="subject-title" className="flex flex-col gap-6">
      <PageNav back="/" crumbs={[{ label: <T k="navHome" />, to: '/' }, { label: <Bi rumi={subject.name_rumi} jawi={subject.name_jawi} /> }]} />

      <div className="relative flex items-center gap-5">
        <SubjectIcon id={subject.id} size="lg" className="h-16 w-16 text-4xl" />
        <div className="min-w-0 flex-1">
          <Bi id="subject-title" rumi={subject.name_rumi} jawi={subject.name_jawi} as="h1" className="text-3xl font-extrabold text-ink sm:text-4xl" />
          <T k={st.desc} as="p" className="mt-1 text-ink-2" />
        </div>
        <div className="relative hidden shrink-0 sm:block" aria-hidden="true">
          <MosqueScene className="absolute end-0 bottom-0 w-72 max-w-none text-primary/10" />
          <Mascot mood="happy" size={100} className="relative drop-shadow-md" />
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <section aria-labelledby="sp-title" className="card-brand flex flex-col gap-4 lg:col-span-2">
          <MosqueScene className="pointer-events-none absolute -end-6 bottom-0 w-72 text-white/[0.07]" />
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <h2 id="sp-title" className="flex items-center gap-2 text-lg font-extrabold">
                <ChartColumn aria-hidden="true" className="h-5 w-5 text-gold" /> <T k="subjectProgress" />
              </h2>
              <p className="text-sm text-on-brand-2">
                <T k="overallMastery" />
              </p>
            </div>
            <p className="text-4xl font-extrabold tabular-nums">{Math.round(subject.mastery * 100)}%</p>
          </div>
          <div
            className="relative h-3 overflow-hidden rounded-full bg-white/20"
            role="progressbar"
            aria-label={t('overallMastery')}
            aria-valuenow={Math.round(subject.mastery * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="h-full rounded-full bg-gold" style={{ width: `${Math.round(subject.mastery * 100)}%` }} />
          </div>
          <dl className="relative grid grid-cols-3 divide-x divide-brand-line rtl:divide-x-reverse">
            {(
              [
                [CircleCheck, count('mastered'), 'statusDone'],
                [CircleDashed, count('learning'), 'statusLearning'],
                [Hourglass, count('new'), 'notStarted'],
              ] as const
            ).map(([Icon, value, key]) => (
              <div key={key} className="flex items-center gap-2.5 px-3 first:ps-0">
                <Icon aria-hidden="true" className="h-6 w-6 shrink-0 text-gold" />
                <div className="flex flex-col-reverse">
                  <dt className="mt-1 text-xs text-on-brand-2">
                    <T k={key} />
                  </dt>
                  <dd className="text-xl leading-none font-extrabold tabular-nums">{value}</dd>
                </div>
              </div>
            ))}
          </dl>
        </section>

        <section aria-labelledby="insight-title" className="card flex flex-col gap-1">
          <h2 id="insight-title" className="section-title mb-2">
            <Lightbulb aria-hidden="true" className="h-5 w-5 text-gold-ink" /> <T k="insight" />
          </h2>
          {(
            [
              [ThumbsUp, 'strongest', strongest, 'text-primary-ink'],
              [Target, 'needsWork', weak[0], 'text-danger'],
            ] as const
          ).map(([Icon, key, tp, cls]) => (
            <div key={key} className="flex items-center gap-3 border-b border-line py-2.5 last:border-0">
              <Icon aria-hidden="true" className={`h-5 w-5 shrink-0 ${cls}`} />
              <T k={key} className="flex-1 text-sm font-semibold text-ink" />
              {tp ? (
                <span className="min-w-0 truncate text-end text-sm text-ink-2">
                  <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} /> ({Math.round(tp.mastery * 100)}%)
                </span>
              ) : (
                <span className="text-sm text-ink-3">–</span>
              )}
            </div>
          ))}
          <div className="flex items-center gap-3 py-2.5">
            <Sparkles aria-hidden="true" className="h-5 w-5 shrink-0 text-gold-ink" />
            <T k="topicsTried" className="flex-1 text-sm font-semibold text-ink" />
            <span className="text-sm text-ink-2 tabular-nums">
              {tried.length}/{practice.length}
            </span>
          </div>
        </section>
      </div>

      <section aria-labelledby="overview-title" className="flex flex-col gap-5">
        <h2 id="overview-title" className="section-title text-xl">
          <BookOpen aria-hidden="true" className="h-5 w-5 text-primary-ink" /> <T k="topicOverview" />
        </h2>
        {subject.babs.map((b) => (
          <section key={b.bab} aria-labelledby={`bab-${b.bab}`} className="flex flex-col gap-3">
            <h3 id={`bab-${b.bab}`} className="flex flex-wrap items-center gap-2 font-bold text-ink">
              <span className={`rounded-lg px-2.5 py-0.5 text-sm ${st.soft} ${st.text}`}>
                <T k="bab" /> {b.bab}
              </span>
              <Bi rumi={b.title_rumi} jawi={b.title_jawi} />
              <span className="text-sm font-medium text-ink-3">
                · {b.topics.length} <T k="topics" />
              </span>
            </h3>
            <ol className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {b.topics.map((tp) => {
                const idx = ++n
                return <TopicCard key={tp.id} topic={tp} n={idx} st={st} delay={Math.min(idx, 9) * 0.03} />
              })}
            </ol>
          </section>
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-3">
        <section aria-labelledby="srec-title" className="card flex flex-col gap-3">
          <h2 id="srec-title" className="section-title">
            <Sparkles aria-hidden="true" className="h-5 w-5 text-gold-ink" /> <T k="recommended" />
          </h2>
          {rec ? (
            <Link to={`/topik/${rec.id}`} className="flex items-center gap-3 rounded-xl border border-line p-3 transition hover:border-primary hover:bg-primary-soft/40">
              <Bi rumi={rec.title_rumi} jawi={rec.title_jawi} className="min-w-0 flex-1 font-bold text-ink" />
              <span className="btn-gold pointer-events-none min-h-9 px-3 py-1 text-sm">
                <Play aria-hidden="true" className="h-3.5 w-3.5 fill-current" /> <T k={rec.attempts ? 'continueBtn' : 'startBtn'} />
              </span>
            </Link>
          ) : (
            <T k="noWeakTopics" as="p" className="text-sm text-ink-3" />
          )}
        </section>
        <section aria-labelledby="sweak-title" className="card flex flex-col gap-2">
          <h2 id="sweak-title" className="section-title">
            <Target aria-hidden="true" className="h-5 w-5 text-danger" /> <T k="topicsToImprove" />
          </h2>
          <MiniList topics={weak} empty="noWeakTopics" />
        </section>
        <section aria-labelledby="sdone-title" className="card flex flex-col gap-2">
          <h2 id="sdone-title" className="section-title">
            <CircleCheck aria-hidden="true" className="h-5 w-5 text-primary" /> <T k="completedTopics" />
          </h2>
          <MiniList topics={done.slice(0, 3)} empty="noneYet" />
        </section>
      </div>
    </section>
  )
}
