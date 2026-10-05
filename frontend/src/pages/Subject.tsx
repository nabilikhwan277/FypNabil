import { motion } from 'framer-motion'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Topic } from '../api/types'
import Bi from '../components/Bi'
import { MascotSay } from '../components/Mascot'
import { SUBJECT_STYLE, type SubjectStyle } from '../components/subjects'
import T from '../components/T'
import { Arrow, ErrorBox, ProgressRing, Spinner, Stars } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import { useScript } from '../i18n/ScriptContext'
import { useStudent } from '../session/StudentContext'

// Horizontal zigzag of the path, in units of --step.
const OFFSETS = [0, 1, 1.6, 1, 0, -1, -1.6, -1]

function masteryStars(t: Topic): number {
  if (!t.attempts) return 0
  if (t.mastery >= 0.9) return 3
  if (t.mastery >= 0.6) return 2
  return 1
}

function nodeLook(t: Topic, st: SubjectStyle): { cls: string; content: string | number | null } {
  if (!t.has_questions) return { cls: 'border-sky-400 bg-sky-100 text-sky-900', content: '📘' }
  const stars = masteryStars(t)
  if (stars === 3) return { cls: 'border-amber-600 bg-amber-300 text-amber-950', content: '👑' }
  if (t.attempts > 0) return { cls: `${st.solid} ${st.edge} text-white`, content: null }
  return { cls: `${st.edge} bg-white ${st.text} ring-4 ${st.ring}`, content: null }
}

/** Game-style path of topics for one subject, grouped by bab. */
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

  // "Start here": first topic not tried yet, else the first one without 3 stars.
  const practice = subject.babs.flatMap((b) => b.topics).filter((tp) => tp.has_questions)
  const recommended = (practice.find((tp) => tp.attempts === 0) ?? practice.find((tp) => masteryStars(tp) < 3))?.id

  let n = 0 // running node number across babs (keeps the zigzag continuous)

  return (
    <section aria-labelledby="subject-title" className="flex flex-col gap-6">
      <Link to="/" className="btn-secondary self-start">
        <Arrow back /> <T k="back" />
      </Link>

      <div className={`${st.hero} flex flex-wrap items-center gap-4 rounded-3xl p-5 text-white shadow-lg sm:p-6`}>
        <span aria-hidden="true" className="flex h-20 w-20 items-center justify-center rounded-3xl bg-white/20 text-5xl ring-4 ring-white/30">
          {st.emoji}
        </span>
        <div className="min-w-0 flex-1">
          <Bi id="subject-title" rumi={subject.name_rumi} jawi={subject.name_jawi} as="h2" className="text-3xl font-black sm:text-4xl" />
          <span className="chip mt-2">
            <T k={st.desc} />
          </span>
        </div>
        <ProgressRing value={subject.mastery} size={84} stroke={9} color="#fde047" track="rgb(255 255 255 / 0.3)">
          <span className="text-lg font-black text-ink">{Math.round(subject.mastery * 100)}%</span>
        </ProgressRing>
      </div>

      <MascotSay mood="happy" size={84}>
        <T k="subjectTip" />
      </MascotSay>

      {subject.babs.map((b) => (
        <section key={b.bab} aria-labelledby={`bab-${b.bab}`} className="flex flex-col items-center gap-3">
          <h3
            id={`bab-${b.bab}`}
            className={`max-w-full rounded-2xl border-b-4 px-5 py-2 text-center text-xl font-black text-white shadow-md ${st.solid} ${st.edge}`}
          >
            <T k="bab" /> {b.bab}: <Bi rumi={b.title_rumi} jawi={b.title_jawi} />
          </h3>
          <ol className="flex w-full flex-col items-center [--step:2.5rem] sm:[--step:4.5rem]">
            {b.topics.map((tp) => {
              const idx = n++
              const off = OFFSETS[idx % OFFSETS.length]
              const prev = idx > 0 ? OFFSETS[(idx - 1) % OFFSETS.length] : off
              const look = nodeLook(tp, st)
              const isRec = tp.id === recommended
              return (
                <li
                  key={tp.id}
                  className="flex flex-col items-center"
                  style={{ transform: `translateX(calc(var(--step) * ${off}))` }}
                >
                  {/* stepping stones from the previous node */}
                  <span
                    aria-hidden="true"
                    className="flex flex-col items-center gap-1.5 py-2"
                    style={{ transform: `translateX(calc(var(--step) * ${(prev - off) / 2}))` }}
                  >
                    <span className={`h-2.5 w-2.5 rounded-full opacity-40 ${st.solid}`} />
                    <span className={`h-2.5 w-2.5 rounded-full opacity-40 ${st.solid}`} />
                  </span>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: Math.min(idx, 8) * 0.04 }}
                  >
                    <Link to={`/topik/${tp.id}`} className="group flex flex-col items-center gap-2 rounded-3xl p-1">
                      {isRec && (
                        <span className="relative animate-floaty rounded-2xl border-2 border-emerald-200 bg-white px-3 py-1 text-sm font-black text-emerald-800 shadow-md">
                          <T k="startHere" />
                          <span
                            aria-hidden="true"
                            className="absolute -bottom-[7px] left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-r-2 border-b-2 border-emerald-200 bg-white"
                          />
                        </span>
                      )}
                      <span className="relative">
                        {isRec && (
                          <span aria-hidden="true" className="absolute inset-0 animate-ping rounded-full bg-yellow-300 opacity-60" />
                        )}
                        <span
                          aria-hidden="true"
                          className={`relative flex h-20 w-20 items-center justify-center rounded-full border-b-8 text-3xl font-black shadow-lg transition group-hover:-translate-y-1 group-active:translate-y-0.5 group-active:border-b-4 ${look.cls}`}
                        >
                          {look.content ?? idx + 1}
                        </span>
                      </span>
                      <span className="max-w-44 rounded-2xl bg-white px-3 py-1.5 text-center shadow-sm ring-2 ring-white">
                        <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} className="block text-base leading-snug font-black" />
                        <span className="block text-xs font-bold text-slate-600">
                          {tp.has_questions ? (
                            <>
                              <T k="level" /> {tp.level_unlocked}/3 · {tp.attempts} <T k="attempts" />
                            </>
                          ) : (
                            <T k="readOnly" />
                          )}
                        </span>
                      </span>
                      {tp.has_questions && <Stars count={masteryStars(tp)} size="text-lg" />}
                    </Link>
                  </motion.div>
                </li>
              )
            })}
          </ol>
        </section>
      ))}
    </section>
  )
}
