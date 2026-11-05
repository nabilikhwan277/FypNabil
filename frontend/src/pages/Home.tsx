import { motion } from 'framer-motion'
import { ChevronRight, Clock, MessageCircle, Play, Sparkles, Target, TrendingUp } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Bi from '../components/Bi'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import TrendChart from '../components/TrendChart'
import { ErrorBox, MasteryBar, ScorePill, Spinner } from '../components/ui'
import { useChat } from '../chat/ChatContext'
import { useAsync } from '../hooks/useAsync'
import { useScript } from '../i18n/ScriptContext'
import type { StringKey } from '../i18n/strings'
import { answeredToday, DAILY_GOAL } from '../lib/daily'
import { lastSevenDays, practiceTopics, recommendations, weakTopics, WEEKDAY, whenLabel, type SubjectTopic } from '../lib/insights'
import { useProgress } from '../session/ProgressContext'
import { useStudent } from '../session/StudentContext'

/** Five small bars that fill as the pupil answers today's questions. */
function DailyMission({ done }: { done: number }) {
  const { t } = useScript()
  const n = Math.min(done, DAILY_GOAL)
  const complete = done >= DAILY_GOAL
  return (
    <div className="inline-flex flex-wrap items-center gap-3 rounded-full border border-line bg-surface px-4 py-2 shadow-sm">
      <Target aria-hidden="true" className="h-4.5 w-4.5 text-accent" />
      <T k={complete ? 'dailyDone' : 'dailyMission'} className="text-sm font-bold text-ink" />
      <span
        role="progressbar"
        aria-label={t('dailyMission')}
        aria-valuemin={0}
        aria-valuemax={DAILY_GOAL}
        aria-valuenow={n}
        aria-valuetext={`${n} / ${DAILY_GOAL} ${t('answeredToday')}`}
        className="flex gap-1"
      >
        {Array.from({ length: DAILY_GOAL }, (_, i) => (
          <span key={i} aria-hidden="true" className={`h-2 w-5 rounded-full ${i < n ? 'bg-gold' : 'bg-surface-3'}`} />
        ))}
      </span>
      <span className="text-sm font-bold text-ink-2 tabular-nums">
        {n}/{DAILY_GOAL}
      </span>
    </div>
  )
}

const LEVEL_LABEL: Record<number, StringKey> = { 1: 'level1', 2: 'level2', 3: 'level3' }

/** Big green card: carry on with the last topic (or start the first one). */
function ContinueCard({ topic, resume }: { topic: SubjectTopic; resume: boolean }) {
  const pct = Math.round(topic.mastery * 100)
  return (
    <Link
      to={resume ? `/latihan/${topic.id}/${topic.level_unlocked}` : `/topik/${topic.id}`}
      className="card-brand group flex min-h-52 flex-col justify-between gap-5 transition hover:shadow-lg lg:col-span-2"
    >
      <MosqueScene className="pointer-events-none absolute -end-6 bottom-0 w-72 text-white/10 sm:w-96" />
      <span className="relative">
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-on-brand-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gold text-on-gold">
            <Play aria-hidden="true" className="h-3.5 w-3.5 fill-current" />
          </span>
          <T k={resume ? 'continueLearning' : 'startLearning'} />
        </span>
        <Bi rumi={topic.subject_rumi} jawi={topic.subject_jawi} className="mt-3 block text-sm font-bold text-gold" />
        <Bi rumi={topic.title_rumi} jawi={topic.title_jawi} className="block text-2xl leading-tight font-extrabold sm:text-3xl" />
        <span className="mt-1 block text-on-brand-2">
          <T k="level" /> {topic.level_unlocked} · <T k={LEVEL_LABEL[topic.level_unlocked] ?? 'level1'} />
        </span>
      </span>
      <span className="relative flex flex-wrap items-center gap-x-5 gap-y-3">
        <span className="flex min-w-44 flex-1 items-center gap-3">
          <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/20" aria-hidden="true">
            <span className="block h-full rounded-full bg-gold" style={{ width: `${pct}%` }} />
          </span>
          <span className="font-extrabold tabular-nums">{pct}%</span>
        </span>
        <span className="btn-gold pointer-events-none">
          <Play aria-hidden="true" className="h-4 w-4 fill-current" />
          <T k={resume ? 'continueBtn' : 'startLearning'} />
        </span>
      </span>
    </Link>
  )
}

function TopicRow({ topic, score }: { topic: SubjectTopic; score?: boolean }) {
  const { t } = useScript()
  return (
    <Link
      to={`/topik/${topic.id}`}
      className="group flex items-center gap-3 rounded-xl border border-line bg-surface p-3 transition hover:border-primary hover:bg-primary-soft/40"
    >
      <SubjectIcon id={topic.subject} />
      <span className="min-w-0 flex-1">
        <Bi rumi={topic.title_rumi} jawi={topic.title_jawi} className="block truncate font-bold text-ink" />
        <span className="block truncate text-sm text-ink-3">
          <Bi rumi={topic.subject_rumi} jawi={topic.subject_jawi} /> · {topic.attempts ? `${t('level')} ${topic.level_unlocked}` : t('statusNew')}
        </span>
      </span>
      {score && topic.attempts > 0 && <ScorePill value={topic.mastery * 100} />}
      <ChevronRight aria-hidden="true" className="h-5 w-5 shrink-0 text-ink-3 transition group-hover:text-primary-ink rtl:-scale-x-100" />
    </Link>
  )
}

export default function Home() {
  const { student } = useStudent()
  const { script, t } = useScript()
  const { progress } = useProgress()
  const { setOpen: openChat } = useChat()
  const { data, error, loading, reload } = useAsync(() => api.subjects(student!.id), [student!.id])

  const topics = useMemo(() => (data ? practiceTopics(data) : []), [data])
  const recent = progress?.recent ?? []
  const lastTopic = topics.find((tp) => tp.id === recent[0]?.topic_id)
  const current = lastTopic ?? topics.find((tp) => !tp.attempts) ?? topics[0]
  const recs = recommendations(topics, 2, current?.id)
  const weak = weakTopics(topics)
  const titleOf = (id: string) => topics.find((tp) => tp.id === id)
  const week = lastSevenDays(recent).map((d) => ({ label: WEEKDAY.format(d.day), value: d.value }))
  const words = { today: t('today'), yesterday: t('yesterday') }

  return (
    <div className="flex flex-col gap-7">
      {/* Greeting */}
      <section className="relative flex items-center gap-6">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-extrabold text-ink sm:text-[2rem]">
            <T k="homeGreeting" />
            {script === 'jawi' ? '،' : ','} <span className="text-primary-ink">{student!.name}</span>! <span aria-hidden="true">👋</span>
          </h1>
          <T k="homeSub" as="p" className="mt-1 text-ink-2" />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            {progress && <DailyMission done={answeredToday(recent)} />}
            <button type="button" onClick={() => openChat(true)} className="btn-secondary min-h-11 rounded-full px-4 text-sm">
              <MessageCircle aria-hidden="true" className="h-4.5 w-4.5 text-primary-ink" /> <T k="chatAskCta" />
            </button>
          </div>
        </div>
        <div className="relative hidden shrink-0 sm:block" aria-hidden="true">
          <MosqueScene className="absolute end-0 bottom-0 w-64 max-w-none text-primary/10" />
          <Mascot mood="wave" size={112} className="relative drop-shadow-md" />
        </div>
      </section>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} onRetry={reload} />}

      {data && current && (
        <div className="grid gap-5 lg:grid-cols-3">
          <ContinueCard topic={current} resume={!!lastTopic} />
          <section aria-labelledby="rec-title" className="card flex flex-col gap-3">
            <div>
              <h2 id="rec-title" className="section-title">
                <Sparkles aria-hidden="true" className="h-5 w-5 text-gold-ink" />
                <T k="recommended" />
              </h2>
              <T k="recommendedWhy" as="p" className="mt-0.5 text-sm text-ink-3" />
            </div>
            {recs.length ? recs.map((tp) => <TopicRow key={tp.id} topic={tp} score />) : <T k="noWeakTopics" as="p" className="text-sm text-ink-3" />}
          </section>
        </div>
      )}

      {/* Subjects */}
      {data && (
        <section aria-labelledby="choose-subject">
          <T k="chooseSubject" as="h2" id="choose-subject" className="mb-3 text-xl font-extrabold text-ink" />
          <ul className="grid gap-4 sm:grid-cols-3">
            {data.map((s, i) => {
              const st = SUBJECT_STYLE[s.id]
              const tried = s.babs.flatMap((b) => b.topics).filter((tp) => tp.attempts > 0).length
              return (
                <motion.li key={s.id} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                  <Link to={`/subjek/${s.id}`} className="card group flex h-full flex-col gap-4 p-5 transition hover:-translate-y-0.5 hover:shadow-lg">
                    <span className="flex items-center gap-3">
                      <SubjectIcon id={s.id} size="lg" />
                      <span className="min-w-0">
                        <Bi rumi={s.name_rumi} jawi={s.name_jawi} className="block text-lg font-extrabold text-ink" />
                        <T k={st.desc} className="block text-sm text-ink-3" />
                      </span>
                    </span>
                    <MasteryBar value={s.mastery} color={st.bar} className="mt-auto" />
                    <span className="-mt-2 text-xs font-semibold text-ink-3">
                      {tried}/{s.topic_count} <T k="topicsTried" />
                    </span>
                  </Link>
                </motion.li>
              )
            })}
          </ul>
        </section>
      )}

      {/* Activity, week trend, weak topics */}
      {data && progress && (
        <div className="grid gap-5 lg:grid-cols-3">
          <section aria-labelledby="recent-title" className="card flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <h2 id="recent-title" className="section-title">
                <Clock aria-hidden="true" className="h-5 w-5 text-primary-ink" />
                <T k="recentActivity" />
              </h2>
              <Link to="/kemajuan" className="text-sm font-bold text-primary-ink underline-offset-4 hover:underline">
                <T k="seeAll" />
              </Link>
            </div>
            {recent.length ? (
              <ul className="flex flex-col divide-y divide-line">
                {recent.slice(0, 4).map((r) => {
                  const tp = titleOf(r.topic_id)
                  return (
                    <li key={r.id} className="flex items-center gap-3 py-2.5">
                      <SubjectIcon id={r.subject} size="sm" />
                      <span className="min-w-0 flex-1">
                        <Bi rumi={tp?.title_rumi ?? r.topic_id} jawi={tp?.title_jawi} className="block truncate text-sm font-bold text-ink" />
                        <span className="block text-xs text-ink-3">
                          <T k="level" /> {r.level} · {whenLabel(r.created_at, words)}
                        </span>
                      </span>
                      <ScorePill value={r.percent} />
                    </li>
                  )
                })}
              </ul>
            ) : (
              <T k="noRecent" as="p" className="py-4 text-sm text-ink-3" />
            )}
          </section>

          <section aria-labelledby="week-title" className="card flex flex-col gap-2">
            <h2 id="week-title" className="section-title">
              <TrendingUp aria-hidden="true" className="h-5 w-5 text-primary-ink" />
              <T k="weeklyProgress" />
            </h2>
            {week.some((d) => d.value !== null) ? (
              <TrendChart points={week} label={t('weeklyProgress')} />
            ) : (
              <T k="weeklyEmpty" as="p" className="py-4 text-sm text-ink-3" />
            )}
          </section>

          <section aria-labelledby="weak-title" className="card flex flex-col gap-2">
            <div>
              <h2 id="weak-title" className="section-title">
                <Target aria-hidden="true" className="h-5 w-5 text-danger" />
                <T k="topicsToImprove" />
              </h2>
              <T k="topicsToImproveDesc" as="p" className="mt-0.5 text-sm text-ink-3" />
            </div>
            {weak.length ? (
              <ul className="flex flex-col gap-1">
                {weak.map((tp) => (
                  <li key={tp.id}>
                    <Link to={`/topik/${tp.id}`} className="group flex items-center gap-3 rounded-xl px-2 py-2 transition hover:bg-surface-2">
                      <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" />
                      <ScorePill value={tp.mastery * 100} />
                      <ChevronRight aria-hidden="true" className="h-4.5 w-4.5 shrink-0 text-ink-3 rtl:-scale-x-100" />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <T k="noWeakTopics" as="p" className="py-4 text-sm text-ink-3" />
            )}
          </section>
        </div>
      )}
    </div>
  )
}
