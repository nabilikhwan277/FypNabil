/**
 * ChatBox — floating AI chat panel on the Home page.
 *
 * Students can ask free-form questions about Ibadah, Jawi or Tajwid before
 * they practise. Bulan the mascot answers using the RAG pipeline on the
 * backend (POST /api/chat). Limited to 10 turns per session.
 */
import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ChatSource, ChatTurn } from '../api/types'
import { useScript } from '../i18n/ScriptContext'
import { useStudent } from '../session/StudentContext'
import Mascot from './Mascot'
import T from './T'

const MAX_INPUT = 500
const THINKING_MIN_MS = 600 // show thinking dots for at least this long

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
  error?: boolean
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms))
}

// ── Source chips ──────────────────────────────────────────────────────────────
function SourceList({ sources, script }: { sources: ChatSource[]; script: 'rumi' | 'jawi' }) {
  const { t } = useScript()
  if (!sources.length) return null
  return (
    <ul className="mt-2 flex flex-wrap gap-1.5" aria-label={t('chatSources')}>
      {sources.map((s, i) => (
        <li
          key={i}
          className="rounded-xl bg-sky-50 px-2 py-1 text-xs font-bold text-sky-800 ring-1 ring-sky-200"
        >
          {script === 'jawi' && s.topic_jawi ? s.topic_jawi : s.topic_rumi}
          {s.pages.length > 0 && (
            <span className="ms-1 text-sky-600">
              {t('chatPage')} {s.pages.join(', ')}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

// ── Thinking dots ─────────────────────────────────────────────────────────────
function ThinkingDots() {
  return (
    <span className="flex items-center gap-1.5 py-1" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-2.5 w-2.5 rounded-full bg-emerald-400"
          animate={{ y: [0, -6, 0] }}
          transition={{ repeat: Infinity, duration: 0.7, delay: i * 0.15 }}
        />
      ))}
    </span>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ChatBox() {
  const { student } = useStudent()
  const { t, script } = useScript()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [turnsLeft, setTurnsLeft] = useState(10)
  const [limited, setLimited] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const panelId = useId()
  const btnId = useId()

  // Scroll to latest message whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  // Focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  if (!student) return null

  const send = async () => {
    const text = input.trim()
    if (!text || busy || limited) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setBusy(true)

    // Build history for the API (last 6 turns)
    const history: ChatTurn[] = messages
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const [res] = await Promise.all([
        api.chat(student.id, text, history),
        sleep(THINKING_MIN_MS),
      ])
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.reply,
          sources: res.sources,
        },
      ])
      setTurnsLeft(res.turns_left)
      if (res.turns_left <= 0) setLimited(true)
    } catch (err) {
      const status = (err as { status?: number }).status
      if (status === 429) {
        setLimited(true)
        setMessages((m) => [...m, { role: 'assistant', content: t('chatLimit'), sources: [] }])
      } else {
        setMessages((m) => [...m, { role: 'assistant', content: t('chatError'), sources: [], error: true }])
      }
    } finally {
      setBusy(false)
      setTimeout(() => inputRef.current?.focus(), 60)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      void send()
    }
  }

  return (
    <>
      {/* ── Floating toggle button ── */}
      <button
        id={btnId}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-28 end-4 z-40 flex items-center gap-2 rounded-full border-2 border-b-4 border-emerald-700 bg-emerald-500 py-3 ps-3 pe-5 text-base font-black text-white shadow-xl transition hover:-translate-y-1 active:translate-y-0.5 active:border-b-2 sm:bottom-8"
        aria-label={open ? t('chatClose') : t('chatOpen')}
      >
        <Mascot mood={open ? 'thinking' : 'wave'} size={36} className="shrink-0" />
        <span aria-hidden="true">{open ? '✕' : '💬'}</span>
        <span className="hidden sm:inline">
          <T k={open ? 'chatClose' : 'chatOpen'} />
        </span>
      </button>

      {/* ── Chat panel ── */}
      <AnimatePresence>
        {open && (
          <motion.section
            id={panelId}
            aria-labelledby={`${panelId}-title`}
            role="dialog"
            aria-modal="false"
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 280, damping: 22 }}
            className="fixed bottom-52 end-4 z-40 flex w-[min(96vw,380px)] flex-col overflow-hidden rounded-3xl border-2 border-emerald-200 bg-white shadow-2xl sm:bottom-28"
            style={{ maxHeight: 'min(60vh, 560px)' }}
          >
            {/* Header */}
            <div className="flex shrink-0 items-center gap-3 bg-linear-to-r from-emerald-600 to-teal-700 px-4 py-3 text-white">
              <Mascot mood="happy" size={40} className="shrink-0 drop-shadow" />
              <div className="min-w-0">
                <T
                  k="chatTitle"
                  id={`${panelId}-title`}
                  as="h2"
                  className="text-lg font-black leading-tight"
                />
                <T k="chatSubtitle" as="p" className="line-clamp-2 text-xs leading-tight text-white/85" />
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t('chatClose')}
                className="ms-auto flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-white/20 text-white transition hover:bg-white/40"
              >
                ✕
              </button>
            </div>

            {/* Messages */}
            <div
              role="log"
              aria-live="polite"
              aria-label={t('chatTitle')}
              className="flex flex-1 flex-col gap-3 overflow-y-auto p-4"
            >
              {/* Welcome message */}
              {messages.length === 0 && (
                <div className="flex items-start gap-2">
                  <Mascot mood="wave" size={44} className="shrink-0 drop-shadow" />
                  <div className="rounded-2xl rounded-tl-sm bg-emerald-50 px-3 py-2 ring-1 ring-emerald-100">
                    <T k="chatSubtitle" as="p" className="text-sm font-bold text-emerald-900" />
                    <p className="mt-1 text-xs text-slate-600">
                      <T k="chatSend" /> · Enter
                    </p>
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  {msg.role === 'assistant' && (
                    <Mascot
                      mood={msg.error ? 'encourage' : 'happy'}
                      size={36}
                      className="shrink-0 drop-shadow"
                    />
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                      msg.role === 'user'
                        ? 'rounded-tr-sm bg-sky-500 font-bold text-white'
                        : msg.error
                          ? 'rounded-tl-sm bg-rose-50 text-rose-800 ring-1 ring-rose-200'
                          : 'rounded-tl-sm bg-slate-100 text-ink'
                    }`}
                    dir="auto"
                  >
                    {msg.content}
                    {msg.role === 'assistant' && !msg.error && msg.sources && (
                      <SourceList sources={msg.sources} script={script} />
                    )}
                  </div>
                </div>
              ))}

              {/* Thinking indicator */}
              {busy && (
                <div className="flex items-center gap-2">
                  <Mascot mood="thinking" size={36} className="shrink-0 drop-shadow" />
                  <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-3 py-2">
                    <T k="chatThinking" as="span" className="sr-only" />
                    <ThinkingDots />
                  </div>
                </div>
              )}

              {/* Turns left badge */}
              {turnsLeft <= 3 && !limited && (
                <p className="text-center text-xs font-bold text-amber-700">
                  {turnsLeft} soalan lagi tersisa
                </p>
              )}
              {limited && (
                <p className="rounded-2xl bg-amber-50 px-3 py-2 text-center text-xs font-bold text-amber-800 ring-1 ring-amber-200">
                  <T k="chatLimit" />
                </p>
              )}

              <div ref={bottomRef} aria-hidden="true" />
            </div>

            {/* Input row */}
            <div className="shrink-0 border-t-2 border-slate-100 bg-white px-3 py-2">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value.slice(0, MAX_INPUT))}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  placeholder={t('chatPlaceholder')}
                  disabled={busy || limited}
                  dir="auto"
                  aria-label={t('chatPlaceholder')}
                  className="field min-h-10 flex-1 resize-none py-2 text-sm"
                  style={{ maxHeight: '100px', overflowY: 'auto' }}
                />
                <button
                  type="button"
                  onClick={() => void send()}
                  disabled={!input.trim() || busy || limited}
                  aria-label={t('chatSend')}
                  className="btn-primary min-h-10 shrink-0 px-3 py-2 text-base disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ➤
                </button>
              </div>
              <p className="mt-0.5 text-end text-xs text-slate-400" aria-hidden="true">
                {input.length}/{MAX_INPUT}
              </p>
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </>
  )
}
