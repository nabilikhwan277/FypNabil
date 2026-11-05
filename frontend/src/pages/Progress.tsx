import { motion } from 'framer-motion'
import { Award, BookOpenCheck, ChartColumn, Clock, Flame, Gem, History, Play, Sparkles, Target, TrendingUp } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Bi from '../components/Bi'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import RankCard from '../components/RankCard'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import TrendChart from '../components/TrendChart'
import { ErrorBox, MasteryBar, ScorePill, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { useScript } from '../i18n/ScriptContext'
import { BADGES, type StringKey } from '../i18n/strings'
import { lastSevenDays, recommendations, weakTopics, WEEKDAY, whenLabel } from '../lib/insights'
import { useStudent } from '../session/StudentContext'

function Stat({ icon, value, label, tint }: { icon: ReactNode; value: string | number; label: StringKey; tint: string }) {
  return (
    <li className="card flex items-center gap-4 p-4">
      <span aria-hidden="true" className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${tint}`}>
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-2xl font-extrabold text-ink tabular-nums">{value}</span>
        <T k={label} className="block text-sm text-ink-3" />
      </span>
    </li>
  )
}

export default function ProgressPage() {
  const { student } = useStudent()
  const { t } = useScript()
  const [tab, setTab] = useState<'overview' | 'history'>('overview')
  const { data, error, loading, reload } = useAsync(() => api.progress(student!.id), [student!.id])

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  const topics = data.subjects.flatMap((s) => s.topics.map((tp) => ({ ...tp, subject: s.id, subject_rumi: s.name_rumi, subject_jawi: s.name_jawi })))
  const topicById = new Map(topics.map((tp) => [tp.id, tp] as const))
  const tried = topics.filter((tp) => tp.attempts > 0).length
  const overall = data.subjects.length ? data.subjects.reduce((a, s) => a + s.mastery, 0) / data.subjects.length : 0
  const next = recommendations(topics, 1)[0]
  const weak = weakTopics(topics)
  const week = lastSevenDays(data.recent).map((d) => ({ label: WEEKDAY.format(d.day), value: d.value }))
  const words = { today: t('today'), yesterday: t('yesterday') }
  const badgeIds = Object.keys(BADGES)
  const tabCls = (on: boolean) =>
    `inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl px-4 text-sm font-bold transition ${
      on ? 'bg-brand text-on-brand shadow-sm' : 'text-ink-2 hover:bg-surface-2'
    }`

  return (
    <section aria-labelledby="progress-title" className="flex flex-col gap-6">
      <div className="relative flex items-center gap-6">
        <div className="min-w-0 flex-1">
          <T k="navProgress" as="h1" id="progress-title" className="text-3xl font-extrabold text-ink sm:text-4xl" />
          <T k="progressSub" as="p" className="mt-1 text-ink-2" />
        </div>
        <div className="relative hidden shrink-0 sm:block" aria-hidden="true">
          <MosqueScene className="absolute end-0 bottom-0 w-72 max-w-none text-primary/10" />
          <Mascot mood="celebrate" size={100} className="relative drop-shadow-md" />
        </div>
      </div>

      <div role="tablist" aria-label={t('navProgress')} className="flex w-fit gap-1 rounded-2xl border border-line bg-surface p-1 shadow-sm">
        <button type="button" role="tab" id="tab-overview" aria-selected={tab === 'overview'} aria-controls="panel-overview" onClick={() => setTab('overview')} className={tabCls(tab === 'overview')}>
          <ChartColumn aria-hidden="true" className="h-4.5 w-4.5" /> <T k="tabOverview" />
        </button>
        <button type="button" role="tab" id="tab-history" aria-selected={tab === 'history'} aria-controls="panel-history" onClick={() => setTab('history')} className={tabCls(tab === 'history')}>
          <History aria-hidden="true" className="h-4.5 w-4.5" /> <T k="tabHistory" />
        </button>
      </div>

      {tab === 'overview' ? (
        <div id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" className="flex flex-col gap-5">
          <div className="grid gap-5 lg:grid-cols-3">
            <section aria-labelledby="overall-title" className="card-brand flex flex-col justify-between gap-4 lg:col-span-2">
              <MosqueScene className="pointer-events-none absolute -end-6 bottom-0 w-80 text-white/[0.08]" />
              <div className="relative flex items-center gap-4">
                <span aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-3xl">
                  {data.student.avatar}
                </span>
                <div className="min-w-0">
                  <h2 id="overall-title" className="text-lg font-extrabold">
                    <T k="overallProgress" />
                  </h2>
                  <p className="truncate text-sm text-on-brand-2">
                    {data.student.name}
                    {data.student.kelas && ` · ${data.student.kelas}`}
                  </p>
                </div>
              </div>
              <div className="relative">
                <p className="text-5xl font-extrabold tabular-nums">{Math.round(overall * 100)}%</p>
                <div
                  className="mt-3 h-3 overflow-hidden rounded-full bg-white/20"
                  role="progressbar"
                  aria-label={t('overallProgress')}
                  aria-valuenow={Math.round(overall * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div className="h-full rounded-full bg-gold" style={{ width: `${Math.round(overall * 100)}%` }} />
                </div>
              </div>
            </section>

            <section aria-labelledby="next-title" className="card flex flex-col gap-3">
              <h2 id="next-title" className="section-title">
                <Target aria-hidden="true" className="h-5 w-5 text-danger" /> <T k="recommended" />
              </h2>
              {next ? (
                <>
                  <div className="flex items-center gap-3 rounded-xl border border-line p-3">
                    <SubjectIcon id={next.subject} />
                    <span className="min-w-0 flex-1">
                      <Bi rumi={next.title_rumi} jawi={next.title_jawi} className="block truncate font-bold text-ink" />
                      <Bi rumi={next.subject_rumi} jawi={next.subject_jawi} className="block text-sm text-ink-3" />
                    </span>
                    {next.attempts > 0 && <ScorePill value={next.mastery * 100} />}
                  </div>
                  <Link to={`/topik/${next.id}`} className="btn-gold mt-auto w-full">
                    <Play aria-hidden="true" className="h-4 w-4 fill-current" /> <T k="continueLearning" />
                  </Link>
                </>
              ) : (
                <T k="noWeakTopics" as="p" className="text-sm text-ink-3" />
              )}
            </section>
          </div>

          <ul className="grid gap-4 sm:grid-cols-3">
            <Stat icon={<Gem className="h-6 w-6" />} value={data.xp} label="xp" tint="bg-info-soft text-info-ink" />
            <Stat icon={<Flame className="h-6 w-6" />} value={data.streak_days} label="streak" tint="bg-accent-soft text-accent-ink" />
            <Stat icon={<BookOpenCheck className="h-6 w-6" />} value={`${tried}/${topics.length}`} label="topicsTried" tint="bg-primary-soft text-primary-ink" />
          </ul>

          <div className="grid gap-5 lg:grid-cols-2">
            <section aria-labelledby="subj-title" className="card flex flex-col gap-4">
              <h2 id="subj-title" className="section-title">
                <ChartColumn aria-hidden="true" className="h-5 w-5 text-primary-ink" /> <T k="subjectProgress" />
              </h2>
              {data.subjects.map((s) => (
                <Link key={s.id} to={`/subjek/${s.id}`} className="flex items-center gap-3 rounded-xl p-1 transition hover:bg-surface-2">
                  <SubjectIcon id={s.id} />
                  <span className="min-w-0 flex-1">
                    <Bi rumi={s.name_rumi} jawi={s.name_jawi} className="block font-bold text-ink" />
                    <MasteryBar value={s.mastery} color={SUBJECT_STYLE[s.id].bar} />
                  </span>
                </Link>
              ))}
            </section>

            <section aria-labelledby="trend-title" className="card flex flex-col gap-2">
              <h2 id="trend-title" className="section-title">
                <TrendingUp aria-hidden="true" className="h-5 w-5 text-primary-ink" /> <T k="weeklyProgress" />
              </h2>
              {week.some((d) => d.value !== null) ? (
                <TrendChart points={week} label={t('weeklyProgress')} />
              ) : (
                <T k="weeklyEmpty" as="p" className="py-4 text-sm text-ink-3" />
              )}
            </section>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <section aria-labelledby="pweak-title" className="card flex flex-col gap-2">
              <h2 id="pweak-title" className="section-title">
                <Target aria-hidden="true" className="h-5 w-5 text-danger" /> <T k="topicsToImprove" />
              </h2>
              {weak.length ? (
                <ul className="flex flex-col gap-1">
                  {weak.map((tp) => (
                    <li key={tp.id}>
                      <Link to={`/topik/${tp.id}`} className="flex items-center gap-3 rounded-xl px-2 py-2 transition hover:bg-surface-2">
                        <SubjectIcon id={tp.subject} size="sm" />
                        <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" />
                        <ScorePill value={tp.mastery * 100} />
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <T k="noWeakTopics" as="p" className="py-2 text-sm text-ink-3" />
              )}
            </section>

            <section aria-labelledby="rank-title" className="card flex flex-col gap-4">
              <h2 id="rank-title" className="section-title justify-between">
                <span className="flex items-center gap-2">
                  <Award aria-hidden="true" className="h-5 w-5 text-gold-ink" /> <T k="trophyShelf" />
                </span>
                <span className="chip py-0.5 text-xs">
                  {data.badges.length}/{badgeIds.length}
                </span>
              </h2>
              <RankCard xp={data.xp} className="rounded-xl bg-surface-2 p-3" />
              <ul className="grid grid-cols-3 gap-3 sm:grid-cols-5">
                {badgeIds.map((id, i) => {
                  const b = BADGES[id]
                  const earned = data.badges.includes(id)
                  return (
                    <motion.li
                      key={id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex flex-col items-center gap-1.5 text-center"
                    >
                      <span
                        className={`flex h-14 w-14 items-center justify-center rounded-full border-2 text-2xl ${
                          earned ? 'border-gold bg-gold-soft shadow-sm' : 'border-dashed border-line-strong bg-surface'
                        }`}
                      >
                        <span aria-hidden="true" className={earned ? '' : 'opacity-30 grayscale'}>
                          {b.emoji}
                        </span>
                      </span>
                      <Bi rumi={b.rumi} jawi={b.jawi} className={`text-xs font-bold ${earned ? 'text-ink' : 'text-ink-3'}`} />
                      <T k={earned ? 'earned' : 'notEarned'} className="sr-only" />
                    </motion.li>
                  )
                })}
              </ul>
              {data.badges.length === 0 && <T k="noBadges" as="p" className="text-sm text-ink-3" />}
            </section>
          </div>
        </div>
      ) : (
        <section id="panel-history" role="tabpanel" aria-labelledby="tab-history" className="card">
          <h2 className="section-title mb-3">
            <Clock aria-hidden="true" className="h-5 w-5 text-primary-ink" /> <T k="recent" />
          </h2>
          {data.recent.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center text-ink-3">
              <Sparkles aria-hidden="true" className="h-8 w-8 text-gold" />
              <T k="noRecent" as="p" />
            </div>
          ) : (
            <table className="w-full border-separate border-spacing-0 text-sm">
              <thead className="max-sm:sr-only">
                <tr className="text-start text-xs tracking-wide text-ink-3 uppercase">
                  <th scope="col" className="border-b border-line py-2 text-start font-bold">
                    <T k="dateTime" />
                  </th>
                  <th scope="col" className="border-b border-line py-2 text-start font-bold">
                    <T k="topicLabel" />
                  </th>
                  <th scope="col" className="border-b border-line py-2 text-start font-bold">
                    <T k="level" />
                  </th>
                  <th scope="col" className="border-b border-line py-2 text-end font-bold">
                    <T k="marksLabel" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.recent.map((r) => {
                  const tp = topicById.get(r.topic_id)
                  return (
                    <tr key={r.id} className="max-sm:flex max-sm:flex-wrap max-sm:items-center max-sm:gap-x-3 max-sm:border-b max-sm:border-line max-sm:py-2">
                      <td className="border-b border-line py-2.5 text-ink-2 max-sm:order-2 max-sm:w-full max-sm:border-0 max-sm:py-0 max-sm:text-xs">
                        {whenLabel(r.created_at, words)}
                      </td>
                      <td className="border-b border-line py-2.5 max-sm:order-1 max-sm:flex-1 max-sm:border-0 max-sm:py-0">
                        <span className="flex items-center gap-2">
                          <SubjectIcon id={r.subject} size="sm" />
                          <Bi rumi={tp?.title_rumi ?? r.topic_id} jawi={tp?.title_jawi} className="font-semibold text-ink" />
                        </span>
                      </td>
                      <td className="border-b border-line py-2.5 text-ink-2 max-sm:hidden">{r.level}</td>
                      <td className="border-b border-line py-2.5 text-end max-sm:order-1 max-sm:border-0 max-sm:py-0">
                        <ScorePill value={r.percent} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </section>
      )}
    </section>
  )
}
