import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Assessment, Bi as BiText, Question } from '../api/types'
import Bi, { isArabic, textDir } from '../components/Bi'
import CelebrationModal, { type Celebration } from '../components/CelebrationModal'
import JawiKeyboard from '../components/JawiKeyboard'
import Mascot from '../components/Mascot'
import ResultCard from '../components/ResultCard'
import RoundSummary, { type RoundItem } from '../components/RoundSummary'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { Arrow, Card, ErrorBox, Spinner } from '../components/ui'
import { useSpeech } from '../hooks/useSpeech'
import { useScript } from '../i18n/ScriptContext'
import { STRINGS } from '../i18n/strings'
import { blankCount, blankLettered, blankOptions, composeBlanks, isJawiSpelling, quickKind } from '../lib/quick'
import { rankFor } from '../lib/rank'
import { useProgress } from '../session/ProgressContext'
import { useStudent } from '../session/StudentContext'
import { useSound } from '../sound/SoundContext'

type Phase = 'loading' | 'answering' | 'checking' | 'result' | 'summary' | 'error'

const ROUND_SIZE = 5
const MAX_CHARS = 2000
const MIN_CHECK_MS = 650 // keeps the "checking" screen from flickering (scoring takes ~0.1 s)
const CELEBRATE_DELAY_MS = 1100 // let the stars animate before the dialog opens

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** Up to 5 questions per round; fewer when the level has fewer questions (no repeats). */
function roundSizeFor(q: Question, level: number): number {
  const counts = q.topic.question_counts
  const n = counts[String(level)] || Object.values(counts).reduce((a, b) => a + b, 0)
  return Math.max(1, Math.min(ROUND_SIZE, n))
}

/** Fresh state for every topic/level, e.g. "next level" starts a new round. */
export default function PracticePage() {
  const { topicId = '', level = '1' } = useParams()
  return <Practice key={`${topicId}/${level}`} topicId={topicId} level={Number(level) || 1} />
}

function RoundProgress({ items, size, current }: { items: RoundItem[]; size: number; current: number }) {
  return (
    <div className="flex items-center gap-3">
      <p className="shrink-0 font-black text-slate-700">
        <T k="question" /> {Math.min(current, size)}/{size}
      </p>
      <ol aria-hidden="true" className="flex flex-1 gap-1.5">
        {Array.from({ length: size }, (_, i) => {
          const r = items[i]
          const cls = r
            ? r.stars === 3
              ? 'bg-emerald-500'
              : r.stars === 2
                ? 'bg-sky-500'
                : 'bg-violet-400'
            : i === current - 1
              ? 'animate-pulse bg-amber-300'
              : 'bg-white'
          return <li key={i} className={`h-4 flex-1 rounded-full shadow-inner ring-2 ring-white ${cls}`} />
        })}
      </ol>
    </div>
  )
}

function Practice({ topicId, level }: { topicId: string; level: number }) {
  const { student } = useStudent()
  const { t, script } = useScript()
  const { play } = useSound()
  const { progress, refresh } = useProgress()
  const speech = useSpeech()
  const nav = useNavigate()

  const [phase, setPhase] = useState<Phase>('loading')
  const [question, setQuestion] = useState<Question | null>(null)
  const [answer, setAnswer] = useState('')
  const [picked, setPicked] = useState<string[]>([])
  const [result, setResult] = useState<Assessment | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [errorKind, setErrorKind] = useState<'load' | 'answer'>('load')
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [showOther, setShowOther] = useState(false)
  const [slow, setSlow] = useState(false)
  const [round, setRound] = useState<RoundItem[]>([])
  const [unlockedTo, setUnlockedTo] = useState(level)
  const [celebration, setCelebration] = useState<Celebration | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [burst, setBurst] = useState(0)
  const areaRef = useRef<HTMLTextAreaElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const attempt = useRef(0) // ignores late responses from an earlier question
  const playRef = useRef(play)
  const answerId = useId()
  const chipsId = useId()
  const enterId = useId()

  useEffect(() => {
    playRef.current = play
  })

  const loadQuestion = useCallback(async () => {
    attempt.current++
    window.scrollTo({ top: 0 })
    setPhase('loading')
    setError(null)
    setAnswer('')
    setPicked([])
    setResult(null)
    setShowOther(false)
    setCelebration(null)
    setModalOpen(false)
    try {
      const q = await api.nextQuestion(student!.id, { topicId, level })
      setQuestion(q)
      setShowKeyboard(q.subject === 'jawi')
      setPhase('answering')
    } catch (e) {
      setError((e as Error).message)
      setErrorKind('load')
      setPhase('error')
    }
  }, [student, topicId, level])

  useEffect(() => {
    void loadQuestion()
  }, [loadQuestion])

  // Screen-reader and keyboard users land on the new question.
  useEffect(() => {
    if (phase === 'answering') headingRef.current?.focus({ preventScroll: true })
  }, [phase, question])

  useEffect(() => {
    if (phase !== 'checking') return
    setSlow(false)
    const id = setTimeout(() => setSlow(true), 5000)
    return () => clearTimeout(id)
  }, [phase])

  // Open the "Hebat!" dialog a moment after the result appears.
  useEffect(() => {
    if (!celebration) return
    const id = setTimeout(() => {
      setModalOpen(true)
      playRef.current('levelup')
    }, CELEBRATE_DELAY_MS)
    return () => clearTimeout(id)
  }, [celebration])

  const size = question ? roundSizeFor(question, level) : ROUND_SIZE

  const submit = async () => {
    if (!question || !answer.trim() || phase !== 'answering') return
    const mine = ++attempt.current
    speech.stop()
    play('tap')
    setPhase('checking')
    try {
      const [res] = await Promise.all([api.answer(student!.id, question.id, answer.trim()), sleep(MIN_CHECK_MS)])
      if (attempt.current !== mine) return
      const fb = res.feedback
      setResult(res)
      setRound((r) => [...r, { questionId: question.id, stars: fb.stars, percent: fb.percent, xp: fb.xp_gained }])
      setUnlockedTo((u) => Math.max(u, fb.level.after))
      setPhase('result')
      window.scrollTo({ top: 0, behavior: 'smooth' })
      play(fb.stars === 3 ? 'correct' : fb.stars === 2 ? 'partial' : 'wrong')
      if (fb.stars === 3) setBurst((b) => b + 1)

      // New totals for the header; a new rank, level or badge earns a celebration.
      const p = await refresh()
      if (attempt.current !== mine) return
      const rank = p ? rankFor(p.xp) : null
      const rankUp = p && rank && rank.number > rankFor(p.xp - fb.xp_gained).number ? rank : null
      if (rankUp || fb.level.unlocked || res.new_badges.length > 0) {
        setCelebration({ rank: rankUp, level: fb.level.unlocked ? fb.level.after : null, badges: res.new_badges })
      }
    } catch (err) {
      if (attempt.current !== mine) return
      setError((err as Error).message)
      setErrorKind('answer')
      setPhase('error')
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit()
  }

  const finishRound = () => {
    attempt.current++
    speech.stop()
    setModalOpen(false)
    setCelebration(null)
    setPhase('summary')
    setBurst((b) => b + 1)
    play('finish')
    window.scrollTo({ top: 0 })
  }

  const next = () => (round.length >= size ? finishRound() : void loadQuestion())
  const stop = () => (round.length > 0 ? finishRound() : nav(`/topik/${topicId}`))
  const playAgain = () => {
    setRound([])
    void loadQuestion()
  }
  const goNextLevel = () => nav(`/latihan/${topicId}/${Math.min(3, level + 1)}`)

  if (!question) {
    return (
      <section className="flex flex-col gap-4">
        <Link to={`/topik/${topicId}`} className="btn-secondary self-start">
          <Arrow back /> <T k="back" />
        </Link>
        {phase === 'error' ? <ErrorBox message={error ?? ''} onRetry={loadQuestion} /> : <Spinner />}
      </section>
    )
  }

  const st = SUBJECT_STYLE[question.subject]
  const kind = quickKind(question)
  const options = kind === 'blanks' ? blankOptions(question, script) : []
  const blanks = blankCount(question)
  const lettered = blankLettered(question)
  const shortAnswer = question.type === 'short'
  const qText = script === 'jawi' && question.question_jawi ? question.question_jawi : question.question_rumi
  const otherText = script === 'jawi' ? question.question_rumi : question.question_jawi
  const qDir = textDir(qText)
  // Highest open level: from this round's results or the pupil's saved progress.
  const savedLevel = progress?.subjects.flatMap((s) => s.topics).find((tp) => tp.id === topicId)?.level_unlocked ?? level
  const canNextLevel =
    level < 3 && Math.max(unlockedTo, savedLevel) > level && (question.topic.question_counts[String(level + 1)] ?? 0) > 0

  const hint: BiText | null = isJawiSpelling(question)
    ? STRINGS.hintJawi
    : kind === null && question.criteria_count >= 2
      ? {
          rumi: `${STRINGS.hintPointsBefore.rumi} ${question.criteria_count} ${STRINGS.hintPointsAfter.rumi}`,
          jawi: `${STRINGS.hintPointsBefore.jawi} ${question.criteria_count} ${STRINGS.hintPointsAfter.jawi}`,
        }
      : null

  // One blank: a tap swaps the choice. Several blanks: taps fill them in order.
  const pick = (w: string) => {
    const nextWords = picked.includes(w)
      ? picked.filter((x) => x !== w)
      : blanks === 1
        ? [w]
        : picked.length < blanks
          ? [...picked, w]
          : picked
    setPicked(nextWords)
    setAnswer(composeBlanks(question, nextWords))
    play('tap')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return
    // Short answers: Enter checks. Longer answers keep Enter for new lines (Ctrl+Enter checks).
    if (shortAnswer || e.ctrlKey || e.metaKey) {
      e.preventDefault()
      void submit()
    }
  }

  const listen = () => (speech.speaking ? speech.stop() : speech.speak(question.question_rumi.replace(/_{2,}/g, ' … ')))

  return (
    <section aria-labelledby="practice-title" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={`/topik/${topicId}`} className="btn-secondary">
          <Arrow back /> <T k="back" />
        </Link>
        <p id="practice-title" className={`chip min-h-12 px-4 text-base ${st.text}`}>
          <span aria-hidden="true">{st.emoji}</span>
          <Bi rumi={question.topic.title_rumi} jawi={question.topic.title_jawi} /> · <T k="level" /> {level}
        </p>
        {round.length > 0 && (phase === 'answering' || phase === 'result') && (
          <button type="button" onClick={stop} className="btn-secondary ms-auto">
            <span aria-hidden="true">✋</span> <T k="stopRound" />
          </button>
        )}
      </div>

      {phase !== 'summary' && (
        <RoundProgress items={round} size={size} current={phase === 'result' ? round.length : round.length + 1} />
      )}

      {phase === 'loading' && <Spinner />}
      {phase === 'error' && (
        <ErrorBox message={error ?? ''} onRetry={errorKind === 'answer' ? () => setPhase('answering') : loadQuestion} />
      )}

      {(phase === 'answering' || phase === 'checking') && (
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <Card className="relative">
            <Mascot mood="thinking" size={64} className="pointer-events-none absolute -top-8 end-4 hidden drop-shadow sm:block" />
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="chip bg-sky-50">
                <T k="question" /> · {question.max_marks} <T k="marks" />
              </span>
              {speech.available && (
                <button type="button" onClick={listen} aria-pressed={speech.speaking} className="btn-secondary min-h-10 px-3 py-1 text-sm">
                  <span aria-hidden="true">{speech.speaking ? '⏹️' : '🔊'}</span> <T k="listen" />
                </button>
              )}
              {otherText && otherText !== qText && (
                <button
                  type="button"
                  onClick={() => setShowOther((v) => !v)}
                  aria-pressed={showOther}
                  className="btn-secondary min-h-10 px-3 py-1 text-sm"
                >
                  <span aria-hidden="true">🔤</span> <T k="showQuestionIn" />
                </button>
              )}
            </div>
            <h2
              ref={headingRef}
              tabIndex={-1}
              dir={qDir}
              lang={qDir === 'rtl' ? 'ms-Arab' : 'ms'}
              className={`text-2xl leading-relaxed font-black ${qDir === 'rtl' ? 'font-jawi' : ''}`}
            >
              {qText}
            </h2>
            {showOther && otherText && (
              <p
                dir={textDir(otherText)}
                lang={textDir(otherText) === 'rtl' ? 'ms-Arab' : 'ms'}
                className="mt-3 border-t-2 border-dashed border-slate-200 pt-3 text-lg leading-relaxed text-slate-700"
              >
                {otherText}
              </p>
            )}
            {hint && (
              <p className="mt-3 flex items-start gap-2 rounded-2xl bg-yellow-50 px-4 py-2 font-bold text-amber-900 ring-2 ring-yellow-200">
                <span aria-hidden="true">💡</span>
                <Bi rumi={hint.rumi} jawi={hint.jawi} />
              </p>
            )}
          </Card>

          <Card>
            {kind === 'truefalse' && (
              <div className="mb-4">
                <T k="chooseOne" as="p" id={chipsId} className="mb-2 text-lg font-black" />
                <div role="group" aria-labelledby={chipsId} className="grid grid-cols-2 gap-3">
                  {(['betul', 'salah'] as const).map((k) => (
                    <button
                      key={k}
                      type="button"
                      aria-pressed={answer.trim() === t(k)}
                      disabled={phase === 'checking'}
                      onClick={() => {
                        setAnswer(t(k))
                        play('tap')
                      }}
                      className="btn-choice text-2xl"
                    >
                      <span aria-hidden="true">{k === 'betul' ? '✅' : '❌'}</span> <T k={k} />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {kind === 'blanks' && options.length > 0 && (
              <div className="mb-4">
                <T k="tapWords" as="p" id={chipsId} className="mb-2 text-lg font-black" />
                <div role="group" aria-labelledby={chipsId} className="flex flex-wrap gap-2">
                  {options.map((w) => {
                    const pos = picked.indexOf(w)
                    const on = pos >= 0
                    const arabic = isArabic(w)
                    return (
                      <button
                        key={w}
                        type="button"
                        aria-pressed={on}
                        disabled={phase === 'checking' || (blanks > 1 && !on && picked.length >= blanks)}
                        onClick={() => pick(w)}
                        className="btn-choice min-h-12 px-4 text-lg"
                      >
                        {on && (
                          <span aria-hidden="true" className="rounded-full bg-emerald-700 px-2 text-sm text-white">
                            {lettered ? `(${String.fromCharCode(97 + pos)})` : pos + 1}
                          </span>
                        )}
                        <span dir="auto" lang={arabic ? 'ms-Arab' : 'ms'} className={arabic ? 'font-jawi text-xl' : ''}>
                          {w}
                        </span>
                      </button>
                    )
                  })}
                  {picked.length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setPicked([])
                        setAnswer('')
                      }}
                      className="btn-secondary min-h-12"
                    >
                      <span aria-hidden="true">🧹</span> <T k="clearChoice" />
                    </button>
                  )}
                </div>
              </div>
            )}

            <label htmlFor={answerId} className="mb-2 block text-lg font-black">
              <T k="yourAnswer" />
            </label>
            <textarea
              id={answerId}
              ref={areaRef}
              dir="auto"
              value={answer}
              onChange={(e) => setAnswer(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={onKeyDown}
              rows={shortAnswer ? 2 : question.type === 'structured' ? 4 : 7}
              placeholder={t('typeHere')}
              disabled={phase === 'checking'}
              aria-describedby={shortAnswer ? enterId : undefined}
              className="field font-jawi-mix text-xl"
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600">
              <button
                type="button"
                onClick={() => setShowKeyboard((v) => !v)}
                aria-expanded={showKeyboard}
                className="btn-secondary min-h-10 py-1"
              >
                <span aria-hidden="true">⌨️</span> <T k={showKeyboard ? 'hideKeyboard' : 'showKeyboard'} />
              </button>
              <span className="font-bold tabular-nums">
                {answer.length}/{MAX_CHARS}
              </span>
            </div>
            {showKeyboard && (
              <div className="mt-3">
                <JawiKeyboard target={areaRef} value={answer} onChange={setAnswer} />
              </div>
            )}
          </Card>

          <div className="flex flex-wrap items-center justify-end gap-3">
            {shortAnswer && <T k="pressEnter" as="p" id={enterId} className="text-sm font-bold text-slate-600" />}
            <button type="submit" className="btn-primary text-2xl" disabled={!answer.trim() || phase === 'checking'}>
              <T k="checkAnswer" /> <span aria-hidden="true">✔</span>
            </button>
          </div>
        </form>
      )}

      <AnimatePresence>
        {phase === 'checking' && (
          <motion.div
            role="status"
            aria-live="polite"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 flex flex-col items-center justify-center gap-4 bg-sky-50/95 p-6 text-center"
          >
            <Mascot mood="thinking" size={150} />
            <T k="thinking" as="p" className="text-2xl font-black" />
            <div aria-hidden="true" className="flex gap-2">
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="h-3 w-3 rounded-full bg-emerald-500"
                  animate={{ y: [0, -8, 0] }}
                  transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }}
                />
              ))}
            </div>
            {slow && <T k="thinkingSlow" as="p" className="font-bold text-slate-700" />}
          </motion.div>
        )}
      </AnimatePresence>

      {phase === 'result' && result && (
        <>
          <Card className="bg-slate-50 shadow-none">
            <T k="yourAnswer" as="p" className="text-sm font-bold text-slate-600" />
            <p dir="auto" className="text-lg whitespace-pre-line">
              {answer}
            </p>
          </Card>
          <ResultCard
            result={result}
            burst={burst}
            lastInRound={round.length >= size}
            onContinue={next}
            onNextLevel={level < 3 ? goNextLevel : undefined}
            onReadNote={() => nav(`/topik/${topicId}`, { state: { openNote: true } })}
          />
        </>
      )}

      {phase === 'summary' && (
        <RoundSummary
          items={round}
          burst={burst}
          canNextLevel={canNextLevel}
          subject={question.subject}
          onPlayAgain={playAgain}
          onNextLevel={goNextLevel}
        />
      )}

      <CelebrationModal open={modalOpen} data={celebration} onClose={() => setModalOpen(false)} />
    </section>
  )
}
