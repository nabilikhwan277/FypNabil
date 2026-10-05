import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Bi from '../components/Bi'
import RankCard from '../components/RankCard'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { Card, ErrorBox, MasteryBar, ProgressRing, Spinner, Stars } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { BADGES, type StringKey } from '../i18n/strings'
import { useStudent } from '../session/StudentContext'

// Same thresholds as the backend (memory/db.py stars_for).
const starsFor = (pct: number) => (pct >= 100 ? 3 : pct >= 50 ? 2 : 1)

function StatCard({ emoji, value, label, pulse = false }: { emoji: string; value: string | number; label: StringKey; pulse?: boolean }) {
  return (
    <li className="card flex flex-col items-center text-center">
      <motion.span
        aria-hidden="true"
        className="text-4xl"
        animate={pulse ? { scale: [1, 1.15, 1] } : undefined}
        transition={{ repeat: Infinity, duration: 1.6 }}
      >
        {emoji}
      </motion.span>
      <span className="text-3xl font-black tabular-nums">{value}</span>
      <T k={label} className="font-bold text-slate-700" />
    </li>
  )
}

export default function ProgressPage() {
  const { student } = useStudent()
  const { data, error, loading, reload } = useAsync(() => api.progress(student!.id), [student!.id])

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  const topics = data.subjects.flatMap((s) => s.topics)
  const topicById = new Map(topics.map((t) => [t.id, t] as const))
  const tried = topics.filter((t) => t.attempts > 0).length
  const badgeIds = Object.keys(BADGES)

  return (
    <section aria-labelledby="progress-title" className="flex flex-col gap-5">
      <div className="card flex flex-col gap-4 bg-linear-to-br from-violet-100 via-white to-sky-100 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="flex h-20 w-20 shrink-0 animate-floaty items-center justify-center rounded-full bg-white text-5xl shadow-md ring-4 ring-violet-200"
          >
            {data.student.avatar}
          </span>
          <div className="min-w-0">
            <T k="navProgress" as="h2" id="progress-title" className="text-2xl font-black" />
            <p className="text-lg font-bold text-slate-700">
              {data.student.name}
              {data.student.kelas && ` · ${data.student.kelas}`}
            </p>
          </div>
        </div>
        <RankCard xp={data.xp} big className="flex-1 rounded-2xl bg-white p-3 shadow-sm ring-2 ring-violet-100" />
      </div>

      <ul className="grid gap-4 sm:grid-cols-3">
        <StatCard emoji="💎" value={data.xp} label="xp" />
        <StatCard emoji="🔥" value={data.streak_days} label="streak" pulse={data.streak_days > 0} />
        <StatCard emoji="📚" value={`${tried}/${topics.length}`} label="topicsTried" />
      </ul>

      <Card>
        <h3 className="mb-3 flex items-center justify-between gap-2 text-xl font-black">
          <span>
            <span aria-hidden="true">🏆 </span>
            <T k="trophyShelf" />
          </span>
          <span className="chip bg-amber-50 tabular-nums">
            {data.badges.length}/{badgeIds.length}
          </span>
        </h3>
        <ul className="grid grid-cols-2 gap-x-3 gap-y-5 rounded-2xl bg-linear-to-b from-amber-50 to-orange-50 p-4 sm:grid-cols-5">
          {badgeIds.map((id, i) => {
            const b = BADGES[id]
            const earned = data.badges.includes(id)
            return (
              <motion.li
                key={id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="flex flex-col items-center gap-1 text-center"
              >
                <span
                  className={`relative flex h-20 w-20 items-center justify-center rounded-full text-4xl shadow-md ring-4 ring-white ${
                    earned ? 'bg-linear-to-br from-yellow-200 to-amber-400' : 'bg-slate-200'
                  }`}
                >
                  <span aria-hidden="true" className={earned ? '' : 'opacity-40 grayscale'}>
                    {b.emoji}
                  </span>
                  {!earned && (
                    <span
                      aria-hidden="true"
                      className="absolute -end-1 -bottom-1 flex h-7 w-7 items-center justify-center rounded-full bg-slate-500 text-sm"
                    >
                      🔒
                    </span>
                  )}
                </span>
                <span aria-hidden="true" className="h-2 w-24 rounded-full bg-amber-700/25" />
                <Bi rumi={b.rumi} jawi={b.jawi} className={`text-sm font-black ${earned ? 'text-ink' : 'text-slate-600'}`} />
                <T k={earned ? 'earned' : 'notEarned'} className="sr-only" />
              </motion.li>
            )
          })}
        </ul>
        {data.badges.length === 0 && <T k="noBadges" as="p" className="mt-3 text-sm font-bold text-slate-600" />}
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {data.subjects.map((s) => {
          const st = SUBJECT_STYLE[s.id]
          const triedTopics = s.topics.filter((t) => t.attempts > 0)
          return (
            <Card key={s.id} className={`ring-2 ${st.ring}`}>
              <div className="flex items-center gap-3">
                <ProgressRing value={s.mastery} size={72} stroke={8} color={st.hex} track={st.track} decorative>
                  <span className="text-3xl">{st.emoji}</span>
                </ProgressRing>
                <div className="min-w-0">
                  <Bi rumi={s.name_rumi} jawi={s.name_jawi} as="h3" className={`text-xl font-black ${st.text}`} />
                  <p className="text-sm font-bold text-slate-600">
                    <T k="mastery" /> {Math.round(s.mastery * 100)}% · {triedTopics.length}/{s.topic_count} <T k="topics" />
                  </p>
                </div>
              </div>
              {triedTopics.length === 0 && (
                <p className={`mt-3 rounded-2xl px-3 py-2 text-sm font-bold text-slate-600 ${st.soft}`}>
                  <T k="noRecent" />
                </p>
              )}
              {triedTopics.length > 0 && (
                <ul className="mt-3 flex flex-col gap-2">
                  {triedTopics.map((t) => (
                    <li key={t.id}>
                      <Link to={`/topik/${t.id}`} className={`block rounded-2xl px-3 py-2 transition hover:-translate-y-0.5 ${st.soft}`}>
                        <span className="flex flex-wrap items-center justify-between gap-x-3">
                          <Bi rumi={t.title_rumi} jawi={t.title_jawi} className="font-black" />
                          <span className="text-xs font-bold text-slate-600">
                            <T k="level" /> {t.level_unlocked} · {t.attempts} <T k="attempts" />
                          </span>
                        </span>
                        <MasteryBar value={t.mastery} color={st.bar} className="mt-1" />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )
        })}
      </div>

      <Card>
        <T k="recent" as="h3" className="mb-2 text-xl font-black" />
        {data.recent.length === 0 ? (
          <T k="noRecent" as="p" className="text-slate-600" />
        ) : (
          <ul className="flex flex-col gap-2">
            {data.recent.map((r) => {
              const t = topicById.get(r.topic_id)
              return (
                <li key={r.id} className="flex flex-wrap items-center gap-3 rounded-2xl bg-slate-50 px-3 py-2">
                  <span aria-hidden="true" className="text-2xl">
                    {SUBJECT_STYLE[r.subject].emoji}
                  </span>
                  {t ? <Bi rumi={t.title_rumi} jawi={t.title_jawi} className="font-bold" /> : <span className="font-bold">{r.topic_id}</span>}
                  <span className="text-sm text-slate-600">
                    <T k="level" /> {r.level}
                  </span>
                  <span className="ms-auto flex items-center gap-2">
                    <Stars count={starsFor(r.percent)} size="text-base" />
                    <span className="w-12 text-end font-black tabular-nums">{Math.round(r.percent)}%</span>
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </section>
  )
}
