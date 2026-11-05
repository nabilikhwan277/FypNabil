import { BadgeCheck, BookOpen, ChevronRight, Library, Lock, Play, TriangleAlert } from 'lucide-react'
import { useEffect } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Topic } from '../api/types'
import Bi from '../components/Bi'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import NoteView from '../components/NoteView'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { ErrorBox, PageNav, ProgressRing, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import type { StringKey } from '../i18n/strings'
import { practiceTopics } from '../lib/insights'
import { useStudent } from '../session/StudentContext'

const LEVEL_DESC: Record<number, StringKey> = { 1: 'level1', 2: 'level2', 3: 'level3' }

export default function TopicPage() {
  const { topicId = '' } = useParams()
  const { student } = useStudent()
  const loc = useLocation()
  const fromResult = Boolean((loc.state as { openNote?: boolean } | null)?.openNote)
  const { data, error, loading, reload } = useAsync(() => Promise.all([api.note(topicId), api.subjects(student!.id)]), [topicId, student!.id])

  useEffect(() => {
    if (fromResult && data) document.getElementById('note-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [fromResult, data])

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  const [note, subjects] = data
  const subject = subjects.find((s) => s.babs.some((b) => b.topics.some((t) => t.id === topicId)))
  const topic: Topic = subjects.flatMap((s) => s.babs.flatMap((b) => b.topics)).find((t) => t.id === topicId) ?? {
    ...note.topic,
    mastery: 0,
    attempts: 0,
    level_unlocked: 1,
    has_questions: Object.keys(note.topic.question_counts).length > 0,
  }
  const st = SUBJECT_STYLE[topic.subject]
  const hasQuestions = Object.keys(topic.question_counts).length > 0
  const order = practiceTopics(subject ? [subject] : [])
  const next = order[order.findIndex((t) => t.id === topic.id) + 1]
  const level = Math.min(3, Math.max(1, topic.level_unlocked))

  return (
    <section aria-labelledby="topic-title" className="flex flex-col gap-6">
      <PageNav
        back={`/subjek/${topic.subject}`}
        crumbs={[
          { label: <T k="navHome" />, to: '/' },
          { label: subject ? <Bi rumi={subject.name_rumi} jawi={subject.name_jawi} /> : topic.subject, to: `/subjek/${topic.subject}` },
          { label: <Bi rumi={topic.title_rumi} jawi={topic.title_jawi} /> },
        ]}
      />

      {/* Lesson header */}
      <div className="relative flex items-end gap-6">
        <div className="min-w-0 flex-1">
          <span className="chip border-gold/40 bg-gold-soft text-ink">
            <BookOpen aria-hidden="true" className="h-4 w-4 text-gold-ink" /> <T k="lesson" />
          </span>
          <Bi id="topic-title" rumi={topic.title_rumi} jawi={topic.title_jawi} as="h1" className="mt-3 text-3xl font-extrabold text-ink sm:text-4xl" />
          <p className={`mt-2 inline-flex flex-wrap items-center gap-2 font-semibold ${st.text}`}>
            <SubjectIcon id={topic.subject} size="sm" />
            <span>
              <T k="bab" /> {topic.bab}: <Bi rumi={topic.bab_rumi} jawi={topic.bab_jawi} />
            </span>
          </p>
        </div>
        <div className="relative hidden shrink-0 sm:block" aria-hidden="true">
          <MosqueScene className="absolute end-0 bottom-0 w-72 max-w-none text-primary/10" />
          <Mascot mood="happy" size={104} className="relative drop-shadow-md" />
        </div>
      </div>

      {!topic.verified && (
        <p role="note" className="flex items-start gap-2 rounded-xl border border-accent/40 bg-accent-soft px-4 py-2.5 text-sm font-semibold text-accent-ink">
          <TriangleAlert aria-hidden="true" className="mt-0.5 h-4.5 w-4.5 shrink-0" />
          <T k="notVerified" />
        </p>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-3">
        {/* Note and source */}
        <div className="flex min-w-0 flex-col gap-5 lg:col-span-2">
          <section id="note-panel" aria-labelledby="note-title" className="card scroll-mt-20">
            <h2 id="note-title" className="section-title mb-1">
              <BookOpen aria-hidden="true" className="h-5 w-5 text-primary-ink" />
              <T k="shortNote" />
            </h2>
            <NoteView markdown={note.markdown} />
          </section>

          <section aria-labelledby="source-title" className="card bg-surface-2">
            <h2 id="source-title" className="section-title">
              <Library aria-hidden="true" className="h-5 w-5 text-primary-ink" />
              <T k="sourceNote" />
            </h2>
            <ul className="mt-3 flex flex-col gap-2 text-sm text-ink-2">
              <li className="flex items-start gap-2">
                <BadgeCheck aria-hidden="true" className="mt-0.5 h-4.5 w-4.5 shrink-0 text-primary" />
                <span>
                  <span className="font-bold text-ink">
                    <T k="source" />:
                  </span>{' '}
                  <Bi rumi={note.source.rumi} jawi={note.source.jawi} />
                </span>
              </li>
              {topic.verified && (
                <li className="flex items-start gap-2">
                  <BadgeCheck aria-hidden="true" className="mt-0.5 h-4.5 w-4.5 shrink-0 text-primary" />
                  <T k="verifiedNote" />
                </li>
              )}
            </ul>
          </section>
        </div>

        {/* Progress, levels, next topic */}
        <aside className="flex flex-col gap-5 lg:sticky lg:top-24">
          {hasQuestions && (
            <section aria-labelledby="tp-title" className="card">
              <h2 id="tp-title" className="section-title">
                <T k="topicProgress" />
              </h2>
              <div className="mt-3 flex items-center gap-4">
                <ProgressRing value={topic.mastery} size={88} stroke={9} color={st.hex}>
                  <span className="text-xl font-extrabold text-ink">{Math.round(topic.mastery * 100)}%</span>
                </ProgressRing>
                <div className="text-sm text-ink-2">
                  <p className="font-bold text-ink">
                    <T k="mastery" />
                  </p>
                  <p>
                    {level}/3 <T k="levelsOpen" />
                  </p>
                  <p>
                    {topic.attempts} <T k="attempts" />
                  </p>
                </div>
              </div>
            </section>
          )}

          {hasQuestions && (
            <section aria-labelledby="levels-title" className="card flex flex-col gap-3">
              <h2 id="levels-title" className="section-title">
                <T k="chooseLevel" />
              </h2>
              <ol className="flex flex-col gap-2">
                {[1, 2, 3].map((lvl) => {
                  const count = topic.question_counts[String(lvl)] ?? 0
                  const open = lvl <= topic.level_unlocked && count > 0
                  const body = (
                    <>
                      <span
                        aria-hidden="true"
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-extrabold ${
                          open ? 'bg-primary text-on-primary' : 'bg-surface-3 text-ink-3'
                        }`}
                      >
                        {open ? lvl : <Lock className="h-4 w-4" />}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-bold">
                          <T k="level" /> {lvl} · <T k={LEVEL_DESC[lvl]} />
                        </span>
                        <span className="block text-xs text-ink-3">
                          {open || count === 0 ? (
                            <>
                              {count} <T k="questionsCount" />
                            </>
                          ) : (
                            <T k="lockedHint" />
                          )}
                        </span>
                      </span>
                    </>
                  )
                  return (
                    <li key={lvl}>
                      {open ? (
                        <Link
                          to={`/latihan/${topic.id}/${lvl}`}
                          className="group flex items-center gap-3 rounded-xl border border-line p-2.5 text-ink transition hover:border-primary hover:bg-primary-soft/40"
                        >
                          {body}
                          <ChevronRight aria-hidden="true" className="h-5 w-5 shrink-0 text-ink-3 rtl:-scale-x-100" />
                        </Link>
                      ) : (
                        <div className="flex items-center gap-3 rounded-xl border border-dashed border-line-strong p-2.5 text-ink-3">{body}</div>
                      )}
                    </li>
                  )
                })}
              </ol>
              <Link to={`/latihan/${topic.id}/${level}`} className="btn-gold mt-1 w-full">
                <Play aria-hidden="true" className="h-4.5 w-4.5 fill-current" /> <T k="startPractice" />
              </Link>
            </section>
          )}

          {next && (
            <Link to={`/topik/${next.id}`} className="card group flex items-center gap-3 p-4 transition hover:shadow-lg">
              <SubjectIcon id={next.subject} />
              <span className="min-w-0 flex-1">
                <T k="nextTopic" className="block text-xs font-semibold text-ink-3" />
                <Bi rumi={next.title_rumi} jawi={next.title_jawi} className="block truncate font-bold text-ink" />
              </span>
              <ChevronRight aria-hidden="true" className="h-5 w-5 shrink-0 text-ink-3 transition group-hover:text-primary-ink rtl:-scale-x-100" />
            </Link>
          )}
        </aside>
      </div>
    </section>
  )
}
