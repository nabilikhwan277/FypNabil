import { AnimatePresence, motion } from 'framer-motion'
import {
  BookOpen,
  CircleQuestionMark,
  Eraser,
  FileText,
  GraduationCap,
  Hand,
  Keyboard,
  Languages,
  Lightbulb,
  PenLine,
  Send,
  Sparkles,
  Square,
  Star,
  Volume2,
  type LucideIcon,
} from 'lucide-react'
import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Assessment, Bi as BiText, Question } from '../api/types'
import Bi, { isArabic, textDir } from '../components/Bi'
import CelebrationModal, { type Celebration } from '../components/CelebrationModal'
import JawiKeyboard from '../components/JawiKeyboard'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import ResultCard from '../components/ResultCard'
import RoundSummary, { type RoundItem } from '../components/RoundSummary'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_STYLE } from '../components/subjects'
import T from '../components/T'
import { Arrow, Card, ErrorBox, Spinner } from '../components/ui'
import { useSpeech } from '../hooks/useSpeech'
import { useScript } from '../i18n/ScriptContext'
import { STRINGS, type StringKey } from '../i18n/strings'
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

const CHECK_STEPS: [LucideIcon, StringKey][] = [
  [FileText, 'checkStep1'],
  [BookOpen, 'checkStep2'],
  [Sparkles, 'checkStep3'],
]

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

/** "Soalan 3/5" with one dot per question: green 3 stars, gold 2, grey ring 1, pulsing gold = now. */
function RoundProgress({ items, size, current }: { items: RoundItem[]; size: number; current: number }) {
  return (
    <div className="flex items-center gap-3">
      <p className="shrink-0 text-sm font-bold text-ink">
        <T k="question" /> <span className="tabular-nums">{Math.min(current, size)}/{size}</span>
      </p>
      <ol aria-hidden="true" className="flex items-center gap-1.5">
        {Array.from({ length: size }, (_, i) => {
          const r = items[i]
          const cls = r
            ? r.stars === 3
              ? 'bg-primary'
              : r.stars === 2
                ? 'bg-gold'
                : 'bg-surface ring-2 ring-line-strong'
            : i === current - 1
              ? 'animate-pulse bg-gold ring-4 ring-gold/25'
              : 'bg-surface-3'
          return <li key={i} className={`h-3 w-3 rounded-full ${cls}`} />
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
  const [showHint, setShowHint] = useState(false)
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
    setShowHint(false)
    setCelebration(null)
    setModalOpen(false)
    try {
      const q = await api.nextQuestion(student!.id, { topicId, level })
      setQuestion(q)
      setShowKeyboard(q.subject === 'jawi' && !q.choices)
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
  const mcq = question.choices
  const kind = mcq ? null : quickKind(question)
  const options = kind === 'blanks' ? blankOptions(question, script) : []
  const blanks = blankCount(question)
  const lettered = blankLettered(question)
  const shortAnswer = question.type === 'short'
  const stemRumi = mcq?.stem_rumi ?? question.question_rumi
  const stemJawi = mcq?.stem_jawi ?? question.question_jawi
  const qText = script === 'jawi' && stemJawi ? stemJawi : stemRumi
  const otherText = script === 'jawi' ? stemRumi : stemJawi
  // The option text in the pupil's script (Jawi spelling items have Jawi-only options).
  const optionText = (o: BiText) => (script === 'jawi' || !o.rumi ? o.jawi || o.rumi : o.rumi)
  const LETTERS = 'ABCD'
  const shownAnswer = mcq && LETTERS.includes(answer) ? `${answer}. ${optionText(mcq.options[LETTERS.indexOf(answer)])}` : answer
  const qDir = textDir(qText)
  // Highest open level: from this round's results or the pupil's saved progress.
  const savedLevel = progress?.subjects.flatMap((s) => s.topics).find((tp) => tp.id === topicId)?.level_unlocked ?? level
  const canNextLevel =
    level < 3 && Math.max(unlockedTo, savedLevel) > level && (question.topic.question_counts[String(level + 1)] ?? 0) > 0

  const hint: BiText | null = mcq
    ? null
    : isJawiSpelling(question)
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

  const listen = () =>
    speech.speaking
      ? speech.stop()
      : speech.speak(
          [stemRumi.replace(/_{2,}/g, ' … '), ...(mcq && !mcq.spelling ? mcq.options.map((o, i) => `${LETTERS[i]}, ${o.rumi}`) : [])].join('. '),
        )

  const subject = progress?.subjects.find((s) => s.id === question.subject)

  return (
    <section aria-labelledby="practice-title" className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to={`/topik/${topicId}`} className="btn-secondary min-h-10 rounded-full px-4 text-sm">
          <Arrow back /> <T k="back" />
        </Link>
        {round.length > 0 && (phase === 'answering' || phase === 'result') && (
          <button type="button" onClick={stop} className="btn-secondary ms-auto min-h-10 rounded-full px-4 text-sm">
            <Hand aria-hidden="true" className="h-4 w-4" /> <T k="stopRound" />
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 border-b border-line pb-4">
        <span className="chip border-gold/40 bg-gold-soft text-ink">
          <GraduationCap aria-hidden="true" className="h-4 w-4 text-gold-ink" /> KAFA
        </span>
        <span className={`chip border-transparent font-bold ${st.soft} ${st.text}`}>
          <SubjectIcon id={question.subject} size="sm" className="-ms-1.5 h-6 w-6" />
          {subject ? <Bi rumi={subject.name_rumi} jawi={subject.name_jawi} /> : question.subject}
        </span>
        <p id="practice-title" className="chip min-w-0">
          <span>
            <T k="topicLabel" />:
          </span>
          <Bi rumi={question.topic.title_rumi} jawi={question.topic.title_jawi} className="truncate font-bold text-ink" />
          <span className="shrink-0 rounded-full bg-surface-3 px-2 text-xs whitespace-nowrap">
            <T k="level" /> {level}
          </span>
        </p>
        {phase !== 'summary' && (
          <div className="ms-auto">
            <RoundProgress items={round} size={size} current={phase === 'result' ? round.length : round.length + 1} />
          </div>
        )}
      </div>

      {phase === 'loading' && <Spinner />}
      {phase === 'error' && (
        <ErrorBox message={error ?? ''} onRetry={errorKind === 'answer' ? () => setPhase('answering') : loadQuestion} />
      )}

      {(phase === 'answering' || phase === 'checking') && (
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="card relative overflow-hidden bg-linear-to-br from-surface via-surface to-gold-soft">
            <MosqueScene className="pointer-events-none absolute -end-6 bottom-0 hidden w-60 text-primary/10 sm:block" />
            <div className="relative mb-4 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 font-bold text-ink">
                <span aria-hidden="true" className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-on-brand">
                  <CircleQuestionMark className="h-4 w-4" />
                </span>
                <T k="question" /> {Math.min(round.length + 1, size)}
              </span>
              <span className="chip border-gold/40 bg-gold-soft text-ink">
                <Star aria-hidden="true" className="h-4 w-4 fill-gold text-gold" />
                <span>
                  <T k="marksLabel" />: {question.max_marks}
                </span>
              </span>
              {speech.available && (
                <button type="button" onClick={listen} aria-pressed={speech.speaking} className="btn-secondary min-h-9 rounded-full px-3 py-1 text-sm">
                  {speech.speaking ? <Square aria-hidden="true" className="h-4 w-4" /> : <Volume2 aria-hidden="true" className="h-4 w-4" />}
                  <T k="listen" />
                </button>
              )}
              {otherText && otherText !== qText && (
                <button
                  type="button"
                  onClick={() => setShowOther((v) => !v)}
                  aria-pressed={showOther}
                  className="btn-secondary min-h-9 rounded-full px-3 py-1 text-sm"
                >
                  <Languages aria-hidden="true" className="h-4 w-4" /> <T k="showQuestionIn" />
                </button>
              )}
            </div>
            <h2
              ref={headingRef}
              tabIndex={-1}
              dir={qDir}
              lang={qDir === 'rtl' ? 'ms-Arab' : 'ms'}
              className={`relative text-2xl leading-relaxed font-extrabold text-ink sm:text-[1.65rem] ${qDir === 'rtl' ? 'font-jawi' : ''}`}
            >
              {qText}
            </h2>
            {showOther && otherText && (
              <p
                dir={textDir(otherText)}
                lang={textDir(otherText) === 'rtl' ? 'ms-Arab' : 'ms'}
                className="relative mt-3 border-t border-line pt-3 text-lg leading-relaxed text-ink-2 italic"
              >
                {otherText}
              </p>
            )}
          </div>

          {hint && (
            <div>
              <button
                type="button"
                onClick={() => setShowHint((v) => !v)}
                aria-expanded={showHint}
                className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border border-gold/50 bg-gold-soft px-4 text-sm font-bold text-ink transition hover:border-gold"
              >
                <Lightbulb aria-hidden="true" className="h-4.5 w-4.5 text-gold-ink" /> <T k="hint" />
              </button>
              {showHint && (
                <p className="mt-2 flex items-start gap-2 rounded-xl border border-gold/40 bg-gold-soft px-4 py-2.5 font-semibold text-ink">
                  <Bi rumi={hint.rumi} jawi={hint.jawi} />
                </p>
              )}
            </div>
          )}

          <Card>
            {kind === 'truefalse' && (
              <div className="mb-4">
                <T k="chooseOne" as="p" id={chipsId} className="mb-2 font-bold text-ink" />
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
                <T k="tapWords" as="p" id={chipsId} className="mb-2 font-bold text-ink" />
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
                          <span aria-hidden="true" className="rounded-full bg-primary px-2 text-sm font-bold text-on-primary">
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
                      <Eraser aria-hidden="true" className="h-4.5 w-4.5" /> <T k="clearChoice" />
                    </button>
                  )}
                </div>
              </div>
            )}

            {mcq ? (
              <div>
                <T k="chooseOption" as="p" id={chipsId} className="mb-3 font-bold text-ink" />
                <div role="radiogroup" aria-labelledby={chipsId} className="grid gap-3 sm:grid-cols-2">
                  {mcq.options.map((o, i) => {
                    const letter = LETTERS[i]
                    const on = answer === letter
                    const text = optionText(o)
                    const rtl = textDir(text) === 'rtl'
                    return (
                      <button
                        key={letter}
                        type="button"
                        role="radio"
                        aria-checked={on}
                        disabled={phase === 'checking'}
                        onClick={() => {
                          setAnswer(letter)
                          play('tap')
                        }}
                        className={`flex min-h-16 cursor-pointer items-center gap-3 rounded-xl border-2 px-4 py-3 text-start transition disabled:cursor-not-allowed ${
                          on ? 'border-primary bg-primary-soft shadow-sm' : 'border-line bg-surface hover:border-primary hover:bg-primary-soft/40'
                        }`}
                      >
                        <span
                          aria-hidden="true"
                          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-lg font-extrabold ${
                            on ? 'bg-primary text-on-primary' : 'bg-surface-2 text-ink-2'
                          }`}
                        >
                          {letter}
                        </span>
                        <span
                          dir={rtl ? 'rtl' : 'ltr'}
                          lang={rtl ? 'ms-Arab' : 'ms'}
                          className={`flex-1 font-bold text-ink ${rtl ? 'font-jawi text-2xl' : 'text-lg'}`}
                        >
                          <span className="sr-only">{letter}. </span>
                          {text}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ) : (
              <>
            <label htmlFor={answerId} className="mb-2 flex items-center gap-2 font-bold text-ink">
              <PenLine aria-hidden="true" className="h-4.5 w-4.5 text-primary-ink" />
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
              className="field font-jawi-mix text-lg"
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm text-ink-3">
              <button
                type="button"
                onClick={() => setShowKeyboard((v) => !v)}
                aria-expanded={showKeyboard}
                className="btn-secondary min-h-10 rounded-full px-4 py-1 text-sm"
              >
                <Keyboard aria-hidden="true" className="h-4.5 w-4.5" /> <T k={showKeyboard ? 'hideKeyboard' : 'showKeyboard'} />
              </button>
              <span className="tabular-nums">
                {answer.length} / {MAX_CHARS} <T k="chars" />
              </span>
            </div>
            {showKeyboard && (
              <div className="mt-3">
                <JawiKeyboard target={areaRef} value={answer} onChange={setAnswer} />
              </div>
            )}
              </>
            )}
          </Card>

          <div className="flex flex-col gap-2">
            <button type="submit" className="btn-primary min-h-14 w-full text-lg" disabled={!answer.trim() || phase === 'checking'}>
              <Send aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" /> <T k="checkAnswer" />
            </button>
            {shortAnswer && !mcq && <T k="pressEnter" as="p" id={enterId} className="text-center text-sm text-ink-3 max-sm:sr-only" />}
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
            className="fixed inset-0 z-[45] flex items-center justify-center bg-bg/95 p-6 backdrop-blur-md"
          >
            {/* Honest waiting screen: the steps say what happens, the bar does not pretend to know how far it is. */}
            <div className="flex w-full max-w-xl flex-col items-center gap-4 text-center">
              <div className="relative">
                <MosqueScene className="absolute bottom-0 left-1/2 w-[26rem] max-w-none -translate-x-1/2 text-primary/10" />
                <Mascot mood="thinking" size={128} className="relative" />
              </div>
              <T k="checkingTitle" as="p" className="text-2xl font-extrabold text-ink sm:text-3xl" />
              <T k="checkingSub" as="p" className="-mt-2 text-ink-2" />
              <div aria-hidden="true" className="relative h-2.5 w-full overflow-hidden rounded-full bg-surface-3">
                <span className="absolute inset-y-0 start-0 w-2/5 animate-indeterminate rounded-full bg-primary" />
              </div>
              <ol className="grid w-full gap-2 sm:grid-cols-3">
                {CHECK_STEPS.map(([Icon, k]) => (
                  <li
                    key={k}
                    className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2.5 text-sm font-semibold text-ink-2 sm:flex-col sm:py-3"
                  >
                    <Icon aria-hidden="true" className="h-5 w-5 shrink-0 text-primary-ink" />
                    <T k={k} />
                  </li>
                ))}
              </ol>
              {slow && <T k="thinkingSlow" as="p" className="font-semibold text-ink-2" />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {phase === 'result' && result && (
        <>
          <Card className="border-dashed bg-surface-2 shadow-none">
            <T k="yourAnswer" as="p" className="text-sm font-extrabold text-ink-3" />
            <p dir="auto" className="text-lg whitespace-pre-line text-ink">
              {shownAnswer}
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
