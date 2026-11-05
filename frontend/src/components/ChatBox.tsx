/**
 * ChatBox: the "Tanya Bulan" AI chat panel.
 *
 * Students can ask free-form questions about Ibadah, Jawi or Tajwid before
 * they practise. Bulan the mascot answers using the RAG pipeline on the
 * backend (POST /api/chat). Limited to 10 turns per session. Opened from the
 * sidebar, the mobile tab bar or the home page (ChatContext).
 */
import { AnimatePresence, motion } from 'framer-motion'
import { Send, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ChatSource, ChatTurn } from '../api/types'
import { useChat } from '../chat/ChatContext'
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
        <li key={i} className="rounded-lg bg-primary-soft px-2 py-1 text-xs font-extrabold text-primary-ink">
          <span aria-hidden="true">📚 </span>
          {script === 'jawi' && s.topic_jawi ? s.topic_jawi : s.topic_rumi}
          {s.pages.length > 0 && (
            <span className="ms-1">
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
          className="h-2.5 w-2.5 rounded-full bg-primary"
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
  const { open, setOpen } = useChat()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [turnsLeft, setTurnsLeft] = useState(10)
  const [limited, setLimited] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const panelId = useId()

  // Scroll to latest message whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  // Focus input when panel opens; Escape closes it.
  useEffect(() => {
    if (!open) return
    const timer = setTimeout(() => inputRef.current?.focus(), 50)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => {
      clearTimeout(timer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, setOpen])

  if (!student) return null

  const send = async () => {
    const text = input.trim()
    if (!text || busy || limited) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setBusy(true)

    // Build history for the API (last 6 turns)
    const history: ChatTurn[] = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }))

    try {
      const [res] = await Promise.all([api.chat(student.id, text, history), sleep(THINKING_MIN_MS)])
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, sources: res.sources }])
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
          transition={{ type: 'spring', stiffness: 280, damping: 24 }}
          className="fixed inset-x-2 bottom-[84px] z-40 flex flex-col overflow-hidden rounded-2xl border border-line bg-surface text-ink shadow-lg md:inset-x-auto md:end-5 md:bottom-5 md:w-[400px]"
          style={{ maxHeight: 'min(70vh, 600px)' }}
        >
          {/* Header */}
          <div className="on-brand flex shrink-0 items-center gap-3 bg-linear-to-r from-brand-2 to-brand px-4 py-3 text-on-brand">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/10">
              <Mascot mood="happy" size={40} />
            </span>
            <div className="min-w-0">
              <T k="chatTitle" id={`${panelId}-title`} as="h2" className="text-lg leading-tight font-extrabold" />
              <T k="chatSubtitle" as="p" className="line-clamp-2 text-xs leading-tight text-on-brand-2" />
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t('chatClose')}
              className="ms-auto flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-full bg-white/10 transition hover:bg-white/20"
            >
              <X aria-hidden="true" className="h-5 w-5" />
            </button>
          </div>

          {/* Messages */}
          <div role="log" aria-live="polite" aria-label={t('chatTitle')} className="scroll-thin flex flex-1 flex-col gap-3 overflow-y-auto bg-surface-2 p-4">
            {messages.length === 0 && (
              <div className="flex items-start gap-2">
                <Mascot mood="wave" size={44} className="shrink-0" />
                <div className="rounded-2xl rounded-ss-sm border border-line bg-surface px-3.5 py-2.5 shadow-sm">
                  <T k="chatSubtitle" as="p" className="font-bold text-ink" />
                  <p className="mt-1 text-xs font-bold text-ink-3">
                    <T k="chatSend" /> · Enter
                  </p>
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                {msg.role === 'assistant' && <Mascot mood={msg.error ? 'encourage' : 'happy'} size={36} className="shrink-0" />}
                <div
                  className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 leading-relaxed ${
                    msg.role === 'user'
                      ? 'rounded-se-sm bg-primary font-bold text-on-primary'
                      : msg.error
                        ? 'rounded-ss-sm border border-danger/30 bg-danger-soft text-danger-ink'
                        : 'rounded-ss-sm border border-line bg-surface text-ink shadow-sm'
                  }`}
                  dir="auto"
                >
                  {msg.content}
                  {msg.role === 'assistant' && !msg.error && msg.sources && <SourceList sources={msg.sources} script={script} />}
                </div>
              </div>
            ))}

            {busy && (
              <div className="flex items-center gap-2">
                <Mascot mood="thinking" size={36} className="shrink-0" />
                <div className="rounded-2xl rounded-ss-sm border border-line bg-surface px-3 py-2">
                  <T k="chatThinking" as="span" className="sr-only" />
                  <ThinkingDots />
                </div>
              </div>
            )}

            {turnsLeft <= 3 && !limited && (
              <p className="text-center text-xs font-extrabold text-accent-ink">
                {turnsLeft} <T k="chatTurnsLeft" />
              </p>
            )}
            {limited && (
              <p className="rounded-2xl bg-accent-soft px-3 py-2 text-center text-sm font-bold text-accent-ink">
                <T k="chatLimit" />
              </p>
            )}

            <div ref={bottomRef} aria-hidden="true" />
          </div>

          {/* Input row */}
          <div className="shrink-0 border-t border-line bg-surface px-3 py-2.5">
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
                className="field min-h-12 flex-1 resize-none py-2.5 text-base"
                style={{ maxHeight: '110px', overflowY: 'auto' }}
              />
              <button
                type="button"
                onClick={() => void send()}
                disabled={!input.trim() || busy || limited}
                aria-label={t('chatSend')}
                className="btn-primary min-h-12 shrink-0 px-4 py-2"
              >
                <Send aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" />
              </button>
            </div>
            <p className="mt-1 text-end text-xs font-bold text-ink-3" aria-hidden="true">
              {input.length}/{MAX_INPUT}
            </p>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  )
}
