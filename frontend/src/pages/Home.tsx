import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Bi from '../components/Bi'
import { MascotSay } from '../components/Mascot'
import RankCard from '../components/RankCard'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { Arrow, ErrorBox, ProgressRing, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { useScript } from '../i18n/ScriptContext'
import { useProgress } from '../session/ProgressContext'
import { useStudent } from '../session/StudentContext'

/** Greeting, rank, "continue" shortcut and the three subject cards. */
export default function Home() {
  const { student } = useStudent()
  const { script } = useScript()
  const { progress } = useProgress()
  const { data, error, loading, reload } = useAsync(() => api.subjects(student!.id), [student!.id])

  // "Continue" goes to the most recently practised topic, at its highest unlocked level.
  const last = progress?.recent[0]
  const lastTopic = last ? progress?.subjects.flatMap((s) => s.topics).find((tp) => tp.id === last.topic_id) : undefined
  const lastStyle = last ? SUBJECT_STYLE[last.subject] : null

  return (
    <div className="flex flex-col gap-6">
      <section className="card bg-linear-to-br from-sky-100 via-white to-amber-50 p-5 sm:p-6">
        <MascotSay mood="happy" size={104}>
          <p className="text-2xl font-black">
            <T k="homeGreeting" />
            {script === 'jawi' ? '،' : ','} {student!.name}! <span aria-hidden="true">👋</span>
          </p>
          <T k="homeCheer" as="p" className="mt-1 text-base font-bold text-slate-700" />
        </MascotSay>
        {progress && (
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-stretch">
            <RankCard xp={progress.xp} className="flex-1 rounded-2xl bg-white p-3 shadow-sm ring-2 ring-sky-100" />
            <div className="flex gap-3 sm:flex-col">
              <p className="chip flex-1 justify-center px-4 py-2 text-lg">
                <span aria-hidden="true">💎</span>
                <span className="tabular-nums">{progress.xp}</span> XP
              </p>
              <p className="chip flex-1 justify-center px-4 py-2 text-lg">
                <span aria-hidden="true">🔥</span>
                <span className="tabular-nums">{progress.streak_days}</span> <T k="days" />
              </p>
            </div>
          </div>
        )}
      </section>

      {last && lastTopic && lastStyle && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <Link
            to={`/latihan/${lastTopic.id}/${lastTopic.level_unlocked}`}
            className={`card flex flex-wrap items-center gap-4 ring-2 ${lastStyle.ring} transition hover:-translate-y-1`}
          >
            <span
              aria-hidden="true"
              className={`${lastStyle.solid} ${lastStyle.edge} flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border-b-4 text-3xl`}
            >
              {lastStyle.emoji}
            </span>
            <span className="min-w-0 flex-1">
              <T k="continueLearning" className="block text-sm font-bold text-slate-600" />
              <Bi rumi={lastTopic.title_rumi} jawi={lastTopic.title_jawi} className="block text-xl font-black" />
              <span className="text-sm font-bold text-slate-600">
                <T k="level" /> {lastTopic.level_unlocked}
              </span>
            </span>
            <span className="btn-primary pointer-events-none">
              <T k="continueBtn" /> <Arrow />
            </span>
          </Link>
        </motion.div>
      )}

      <section aria-labelledby="choose-subject">
        <T k="chooseSubject" as="h2" id="choose-subject" className="mb-4 text-2xl font-black" />
        {loading && <Spinner />}
        {error && <ErrorBox message={error} onRetry={reload} />}
        {data && (
          <ul className="grid gap-5 sm:grid-cols-3">
            {data.map((s, i) => {
              const st = SUBJECT_STYLE[s.id]
              return (
                <motion.li
                  key={s.id}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1, type: 'spring', stiffness: 200 }}
                >
                  <Link
                    to={`/subjek/${s.id}`}
                    className={`group flex h-full flex-col overflow-hidden rounded-3xl border-b-8 ${st.edge} bg-white text-center shadow-lg transition hover:-translate-y-1 hover:shadow-xl active:translate-y-0.5 active:border-b-4`}
                  >
                    <span className={`${st.hero} flex justify-center px-4 pt-5 pb-9`}>
                      <ProgressRing value={s.mastery} size={112} stroke={11} color="#fde047" track="rgb(255 255 255 / 0.35)" decorative>
                        <span className="text-5xl transition group-hover:scale-110">{st.emoji}</span>
                      </ProgressRing>
                    </span>
                    <span className="-mt-5 flex flex-1 flex-col items-center gap-1 rounded-t-3xl bg-white px-4 pt-4 pb-5">
                      <Bi rumi={s.name_rumi} jawi={s.name_jawi} className={`text-2xl font-black ${st.text}`} />
                      <T k={st.desc} className="font-bold text-slate-700" />
                      <span className="mt-1 flex flex-wrap items-center justify-center gap-2">
                        <span className={`chip ${st.soft}`}>
                          {s.topic_count} <T k="topics" />
                        </span>
                        <span className={`chip ${st.soft}`}>
                          {Math.round(s.mastery * 100)}% <T k="mastery" />
                        </span>
                      </span>
                      <span
                        className={`mt-auto inline-flex min-h-12 items-center gap-2 rounded-2xl border-b-4 px-6 pt-1 text-xl font-black text-white ${st.solid} ${st.edge}`}
                      >
                        <T k="letsGo" /> <Arrow />
                      </span>
                    </span>
                  </Link>
                </motion.li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}
