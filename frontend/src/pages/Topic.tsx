import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Topic } from '../api/types'
import Bi from '../components/Bi'
import { MascotSay } from '../components/Mascot'
import NoteView from '../components/NoteView'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { Arrow, ErrorBox, ProgressRing, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import type { StringKey } from '../i18n/strings'
import { useStudent } from '../session/StudentContext'

const LEVEL_DESC: Record<number, StringKey> = { 1: 'level1', 2: 'level2', 3: 'level3' }
const LEVEL_EMOJI: Record<number, string> = { 1: '🌱', 2: '🌿', 3: '🌳' }

export default function TopicPage() {
  const { topicId = '' } = useParams()
  const { student } = useStudent()
  const loc = useLocation()
  // "Baca Nota" on the result screen opens the note straight away.
  const fromResult = Boolean((loc.state as { openNote?: boolean } | null)?.openNote)
  const [showNote, setShowNote] = useState(fromResult)
  const { data, error, loading, reload } = useAsync(
    () => Promise.all([api.note(topicId), api.subjects(student!.id)]),
    [topicId, student!.id],
  )

  useEffect(() => {
    if (fromResult && data) document.getElementById('note-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [fromResult, data])

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  const [note, subjects] = data
  // The catalog entry carries the pupil's progress; the note's own copy does not.
  const topic: Topic = subjects.flatMap((s) => s.babs.flatMap((b) => b.topics)).find((t) => t.id === topicId) ?? {
    ...note.topic,
    mastery: 0,
    attempts: 0,
    level_unlocked: 1,
    has_questions: Object.keys(note.topic.question_counts).length > 0,
  }
  const st = SUBJECT_STYLE[topic.subject]
  const hasQuestions = Object.keys(topic.question_counts).length > 0
  const noteOpen = showNote || !hasQuestions

  return (
    <section aria-labelledby="topic-title" className="flex flex-col gap-5">
      <Link to={`/subjek/${topic.subject}`} className="btn-secondary self-start">
        <Arrow back /> <T k="back" />
      </Link>

      <div className={`${st.hero} rounded-3xl p-5 text-white shadow-lg sm:p-6`}>
        <div className="flex flex-wrap items-center gap-4">
          <span aria-hidden="true" className="flex h-20 w-20 items-center justify-center rounded-3xl bg-white/20 text-5xl ring-4 ring-white/30">
            {st.emoji}
          </span>
          <div className="min-w-0 flex-1">
            <span className="chip">
              <T k="bab" /> {topic.bab}: <Bi rumi={topic.bab_rumi} jawi={topic.bab_jawi} />
            </span>
            <Bi id="topic-title" rumi={topic.title_rumi} jawi={topic.title_jawi} as="h2" className="mt-2 text-3xl font-black sm:text-4xl" />
          </div>
          {hasQuestions && (
            <ProgressRing value={topic.mastery} size={84} stroke={9} color="#fde047" track="rgb(255 255 255 / 0.3)">
              <span className="text-lg font-black text-ink">{Math.round(topic.mastery * 100)}%</span>
            </ProgressRing>
          )}
        </div>
        <p className="chip mt-3">
          <span aria-hidden="true">📚</span>
          <T k="source" />: <Bi rumi={note.source.rumi} jawi={note.source.jawi} />
        </p>
      </div>

      <MascotSay mood="encourage" size={84}>
        <T k="topicTip" />
      </MascotSay>

      {!topic.verified && (
        <p role="note" className="rounded-2xl bg-amber-50 px-4 py-2 text-sm font-bold text-amber-900 ring-2 ring-amber-200">
          <span aria-hidden="true">⚠️ </span>
          <T k="notVerified" />
        </p>
      )}

      {hasQuestions && (
        <div className="grid gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((lvl, i) => {
            const count = topic.question_counts[String(lvl)] ?? 0
            const open = lvl <= topic.level_unlocked && count > 0
            return (
              <motion.div
                key={lvl}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className={`card flex flex-col items-center gap-1 text-center ${open ? `ring-2 ${st.ring}` : 'bg-slate-100 shadow-none'}`}
              >
                <span
                  aria-hidden="true"
                  className={`flex h-16 w-16 items-center justify-center rounded-full text-4xl ${open ? st.soft : 'bg-slate-200'}`}
                >
                  {open ? LEVEL_EMOJI[lvl] : '🔒'}
                </span>
                <h3 className="text-xl font-black">
                  <T k="level" /> {lvl}
                </h3>
                <T k={LEVEL_DESC[lvl]} as="p" className="font-bold text-slate-700" />
                <p className="text-sm font-bold text-slate-600">
                  {count} <T k="questionsCount" />
                </p>
                {open ? (
                  <Link to={`/latihan/${topic.id}/${lvl}`} className="btn-primary mt-auto w-full">
                    <T k="startPractice" /> <Arrow />
                  </Link>
                ) : (
                  <p className="mt-auto text-sm font-bold text-slate-700">
                    <span className="me-1 inline-block rounded-full bg-slate-300 px-2 py-0.5 text-ink">
                      <T k="locked" />
                    </span>
                    {count > 0 && <T k="lockedHint" />}
                  </p>
                )}
              </motion.div>
            )
          })}
        </div>
      )}

      <div className="card">
        {!hasQuestions && (
          <h3 className="mb-2 text-xl font-black">
            <span aria-hidden="true">📖 </span>
            <T k="readNote" />
          </h3>
        )}
        {hasQuestions && (
          <button
            type="button"
            onClick={() => setShowNote((v) => !v)}
            aria-expanded={showNote}
            aria-controls="note-panel"
            className="btn-secondary w-full justify-between text-lg"
          >
            <span>
              <span aria-hidden="true">📖 </span>
              <T k="readNote" />
            </span>
            <span aria-hidden="true" className={`transition ${showNote ? 'rotate-180' : ''}`}>
              ▼
            </span>
          </button>
        )}
        <AnimatePresence initial={false}>
          {noteOpen && (
            <motion.div
              id="note-panel"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="scroll-mt-4 overflow-hidden"
            >
              <div className={hasQuestions ? 'pt-4' : ''}>
                <NoteView markdown={note.markdown} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}
