import { Library } from 'lucide-react'
import { useEffect, useId, useState, type FormEvent } from 'react'
import { api } from '../../api/client'
import type { Book, BookStatus, Draft } from '../../api/types'
import { JobProgress, Section, Table } from '../../components/adminUi'
import { usd } from '../../components/format'
import ConfirmDialog from '../../components/ConfirmDialog'
import { ErrorBox, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks/useAsync'
import { useJob } from '../../hooks/useJob'

// Admin → Books & syllabus: the books the system teaches from. Active books are what pupils study and what
// RAG searches. A new book (PDF: a scan or photos of the pages) is read by the AI into DRAFTS that a teacher
// checks before publishing. Removing a book takes it out of the syllabus; restoring brings it back.

const SUBJECTS: Record<Book['subject'], string> = { fiqh: 'Ibadah', jawi: 'Jawi', tajwid: 'Tajwid' }
const KINDS: Record<Book['kind'], string> = { textbook: 'Textbook (notes)', exercise: 'Exercise book (questions)' }
const STATUS: Record<BookStatus, { label: string; cls: string }> = {
  active: { label: '✅ In the syllabus', cls: 'border-primary/30 bg-primary-soft text-primary-ink' },
  draft: { label: '📝 Draft: check and publish', cls: 'bg-accent-soft text-accent-ink' },
  uploaded: { label: '📥 Uploaded: not read yet', cls: 'bg-info-soft text-info-ink' },
  processing: { label: '⏳ The AI is reading it', cls: 'bg-info-soft text-info-ink' },
  failed: { label: '❌ Reading failed', cls: 'bg-danger-soft text-danger-ink' },
  removed: { label: '📦 Removed', cls: 'text-ink-3' },
}

type Action = { book: Book; kind: 'remove' | 'restore' | 'publish' | 'delete' }

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export default function BooksPage() {
  const books = useAsync(() => api.books(), [])
  const [review, setReview] = useState<string | null>(null)
  const [action, setAction] = useState<Action | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const { job, setJob, running } = useJob('book', (j) => {
    books.reload()
    if (j.status === 'done') setReview(String((j.result as { id?: string }).id ?? '') || null)
  })

  if (books.loading && !books.data) return <Spinner />
  if (books.error || !books.data) return <ErrorBox message={books.error ?? ''} onRetry={books.reload} />
  const list = books.data
  const active = list.filter((b) => b.status === 'active')
  const reviewing = list.find((b) => b.id === review && b.status === 'draft')

  const read = async (b: Book) => {
    setMessage(null)
    try {
      setJob(await api.processBook(b.id))
      books.reload()
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message })
    }
  }

  const doAction = async () => {
    if (!action) return
    setBusy(true)
    setMessage(null)
    const { book, kind } = action
    try {
      if (kind === 'delete') await api.deleteBook(book.id)
      else await api.bookAction(book.id, kind)
      const done = { remove: 'removed from the syllabus', restore: 'back in the syllabus', publish: 'published: pupils can use it now', delete: 'deleted' }
      setMessage({ ok: true, text: `“${book.title}” ${done[kind]}.` })
      if (kind === 'publish' || kind === 'delete') setReview(null)
      books.reload()
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message })
    } finally {
      setBusy(false)
      setAction(null)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="flex items-center gap-3 text-2xl font-extrabold text-ink sm:text-3xl">
          <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-soft text-primary-ink">
            <Library className="h-6 w-6" />
          </span>
          Books & syllabus
        </h1>
        <p className="mt-2 max-w-3xl text-ink-2">
          Pupils study, and the RAG searches, only the books in the syllabus. When the UPKK syllabus changes, add the new textbook or exercise book
          here and remove the old one.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="chip">{active.length} books in the syllabus</span>
          <span className="chip">{active.reduce((n, b) => n + b.topics, 0)} topics</span>
          <span className="chip">{active.reduce((n, b) => n + b.questions, 0)} questions</span>
        </div>
      </div>

      {message && (
        <p role="status" className={`rounded-2xl px-4 py-3 font-bold ${message.ok ? 'bg-primary-soft text-primary-ink' : 'bg-danger-soft text-danger-ink'}`}>
          {message.text}
        </p>
      )}
      {job && (job.status === 'running' || job.status === 'failed') && (
        <div className="card">
          <JobProgress job={job} />
        </div>
      )}

      <Section title="Books" note="Built-in = the three Year 5 textbooks the system started with. Removing keeps the files, so a removed book can be restored.">
        <Table
          head={['Book', 'Subject', 'Kind', 'Status', 'Topics', 'Questions', '']}
          rows={list.map((b) => [
            <span className="flex flex-col">
              <b className="text-ink">{b.title}</b>
              <span className="text-xs font-bold text-ink-3">
                {b.origin === 'builtin' ? 'Built-in textbook' : `Uploaded ${b.created.slice(0, 10)} · ${b.pages} pages${b.cost ? ` · AI cost ${usd(b.cost, 3)}` : ''}`}
              </span>
              {b.error && <span className="text-xs font-bold text-danger-ink">{b.error}</span>}
            </span>,
            SUBJECTS[b.subject],
            KINDS[b.kind],
            <span className={`chip whitespace-nowrap ${STATUS[b.status].cls}`}>{STATUS[b.status].label}</span>,
            b.topics,
            b.questions,
            <span className="flex flex-wrap justify-end gap-1.5">
              {b.status === 'active' && (
                <button type="button" className="btn-ghost text-sm" onClick={() => setAction({ book: b, kind: 'remove' })}>
                  Remove
                </button>
              )}
              {b.status === 'removed' && (
                <button type="button" className="btn-secondary text-sm" onClick={() => setAction({ book: b, kind: 'restore' })}>
                  Restore
                </button>
              )}
              {(b.status === 'uploaded' || b.status === 'failed') && (
                <button type="button" className="btn-primary text-sm" disabled={running} onClick={() => read(b)}>
                  {b.status === 'failed' ? 'Try again' : `Read with AI (about ${usd(b.estimate, 2)})`}
                </button>
              )}
              {b.status === 'draft' && (
                <button type="button" className="btn-primary text-sm" onClick={() => setReview(b.id)}>
                  Check drafts
                </button>
              )}
              {b.origin === 'upload' && b.status !== 'active' && b.status !== 'processing' && (
                <button type="button" className="btn-ghost text-sm" onClick={() => setAction({ book: b, kind: 'delete' })}>
                  Delete
                </button>
              )}
            </span>,
          ])}
        />
      </Section>

      {reviewing && <Review book={reviewing} onPublish={() => setAction({ book: reviewing, kind: 'publish' })} onClose={() => setReview(null)} />}

      <AddBook
        onAdded={(b) => {
          setMessage({ ok: true, text: `“${b.title}” uploaded (${b.pages} pages). Press “Read with AI” to make the drafts.` })
          books.reload()
        }}
      />

      <ConfirmDialog
        open={action !== null}
        title={
          action
            ? { remove: 'Remove this book from the syllabus?', restore: 'Put this book back?', publish: 'Publish to the syllabus?', delete: 'Delete this book?' }[action.kind]
            : ''
        }
        confirm={action ? { remove: 'Remove', restore: 'Restore', publish: 'Publish', delete: 'Delete' }[action.kind] : ''}
        danger={action?.kind === 'remove' || action?.kind === 'delete'}
        busy={busy}
        onConfirm={doAction}
        onClose={() => setAction(null)}
      >
        {action?.kind === 'remove' && (
          <>
            <p>
              “{action.book.title}”: {action.book.topics} topics and {action.book.questions} questions leave the syllabus. Pupils stop seeing them and the
              RAG stops searching them.
            </p>
            <p>Pupils' progress is kept, and everything comes back if you restore the book.</p>
          </>
        )}
        {action?.kind === 'restore' && <p>“{action.book.title}” goes back into the syllabus and the RAG searches it again.</p>}
        {action?.kind === 'publish' && (
          <>
            <p>
              Pupils will study {action.book.topics} topics and {action.book.questions} questions from “{action.book.title}”, and the RAG will search them.
            </p>
            <p>Only publish after a teacher has checked the drafts against the book.</p>
          </>
        )}
        {action?.kind === 'delete' && <p>The uploaded PDF and its drafts are deleted. This cannot be undone.</p>}
      </ConfirmDialog>
    </div>
  )
}

function AddBook({ onAdded }: { onAdded: (b: Book) => void }) {
  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState<Book['subject']>('fiqh')
  const [kind, setKind] = useState<Book['kind']>('textbook')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ids = { title: useId(), subject: useId(), file: useId() }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file || !title.trim()) return
    setBusy(true)
    setError(null)
    try {
      const b = await api.uploadBook(file, { title: title.trim(), subject, kind })
      setTitle('')
      setFile(null)
      ;(e.target as HTMLFormElement).reset()
      onAdded(b)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      title="Add a book"
      note="A PDF of the book: a scan or phone photos of the pages put into one PDF is fine. The AI reads each page (Jawi, Rumi and Arabic) and writes drafts; nothing reaches pupils until you publish."
    >
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        <label htmlFor={ids.title} className="flex flex-col gap-1.5 md:col-span-2">
          <span className="eyebrow">Title</span>
          <input id={ids.title} value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={120} className="field" placeholder="e.g. Buku Teks Ibadah KAFA Tahun 5 (edisi 2027)" />
        </label>
        <label htmlFor={ids.subject} className="flex flex-col gap-1.5">
          <span className="eyebrow">Subject</span>
          <select id={ids.subject} value={subject} onChange={(e) => setSubject(e.target.value as Book['subject'])} className="field">
            {Object.entries(SUBJECTS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="eyebrow mb-1.5">Kind</legend>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(KINDS) as Book['kind'][]).map((k) => (
              <button
                key={k}
                type="button"
                aria-pressed={kind === k}
                onClick={() => setKind(k)}
                className={`min-h-11 cursor-pointer rounded-xl border-2 px-3 text-sm font-black transition ${
                  kind === k ? 'border-primary bg-primary-soft text-primary-ink' : 'border-line bg-surface text-ink-2 hover:border-line-strong'
                }`}
              >
                {KINDS[k]}
              </button>
            ))}
          </div>
        </fieldset>
        <label htmlFor={ids.file} className="flex flex-col gap-1.5 md:col-span-2">
          <span className="eyebrow">PDF file (up to 150 MB, 400 pages)</span>
          <input
            id={ids.file}
            type="file"
            accept="application/pdf,.pdf"
            required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="field file:me-3 file:rounded-lg file:border-0 file:bg-surface-2 file:px-3 file:py-1.5 file:font-bold file:text-ink"
          />
        </label>
        <p className="text-sm font-bold text-ink-3 md:col-span-2">
          {kind === 'textbook'
            ? 'Textbook: every topic becomes a note (searched by RAG, shown to pupils) with 6 practice questions written from it.'
            : 'Exercise book: every question is linked to the topic it belongs to, and gets a reference answer and rubric from the notes.'}
        </p>
        {error && (
          <p role="alert" className="rounded-2xl bg-danger-soft px-4 py-2.5 font-bold text-danger-ink md:col-span-2">
            {error}
          </p>
        )}
        <div className="md:col-span-2">
          <button type="submit" disabled={busy || !file || !title.trim()} className="btn-primary">
            {busy ? '⏳ Uploading…' : '📥 Upload'}
          </button>
        </div>
      </form>
    </Section>
  )
}

function Review({ book, onPublish, onClose }: { book: Book; onPublish: () => void; onClose: () => void }) {
  const drafts = useAsync(() => api.drafts(book.id), [book.id])
  if (drafts.loading && !drafts.data) return <Spinner />
  if (drafts.error || !drafts.data) return <ErrorBox message={drafts.error ?? ''} onRetry={drafts.reload} />
  const list = drafts.data
  const errors = list.reduce((n, d) => n + d.errors.length, 0)
  const warnings = list.reduce((n, d) => n + d.warnings.length, 0)
  const unchecked = list.filter((d) => d.kind === 'note' && !d.verified).length
  return (
    <Section
      title={`Check the drafts: ${book.title}`}
      note="Compare each draft with its page, correct it, and mark notes as checked. Publishing needs every draft to be free of errors."
    >
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="chip">{plural(list.filter((d) => d.kind === 'note').length, 'note')}</span>
        <span className="chip">{plural(list.reduce((n, d) => n + (d.count ?? 0), 0), 'question')}</span>
        <span className={`chip ${errors ? 'bg-danger-soft text-danger-ink' : ''}`}>{plural(errors, 'error')}</span>
        <span className={`chip ${warnings ? 'bg-accent-soft text-accent-ink' : ''}`}>{plural(warnings, 'warning')}</span>
        {unchecked > 0 && <span className="chip bg-accent-soft text-accent-ink">{plural(unchecked, 'note')} not checked by a teacher</span>}
        <span className="ms-auto flex gap-2">
          <button type="button" className="btn-ghost text-sm" onClick={onClose}>
            Close
          </button>
          <button type="button" className="btn-primary text-sm" disabled={errors > 0} onClick={onPublish}>
            🚀 Publish to the syllabus
          </button>
        </span>
      </div>
      <ul className="flex flex-col gap-3">
        {list.map((d) => (
          <DraftItem key={d.path} bookId={book.id} draft={d} onChanged={drafts.reload} />
        ))}
      </ul>
    </Section>
  )
}

function DraftItem({ bookId, draft, onChanged }: { bookId: string; draft: Draft; onChanged: () => void }) {
  const [text, setText] = useState(draft.content)
  const [errors, setErrors] = useState(draft.errors)
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState<{ n: number; url: string } | null>(null)
  const editorId = useId()
  const dirty = text !== draft.content

  useEffect(() => () => {
    if (page) URL.revokeObjectURL(page.url)
  }, [page])

  const save = async (content = text) => {
    setSaving(true)
    try {
      const r = await api.saveDraft(bookId, draft.path, content)
      setErrors(r.errors)
      onChanged()
    } catch (e) {
      setErrors([(e as Error).message])
    } finally {
      setSaving(false)
    }
  }

  const markChecked = () => {
    const next = text.replace(/^verified:\s*false\s*$/m, 'verified: true')
    setText(next)
    save(next)
  }

  const remove = async () => {
    await api.deleteDraft(bookId, draft.path)
    onChanged()
  }

  const showPage = async (n: number) => {
    setPage(page?.n === n ? null : { n, url: await api.pageImage(bookId, n) })
  }

  return (
    <li className="rounded-2xl border border-line bg-surface-2">
      <details>
        <summary className="flex cursor-pointer flex-wrap items-center gap-2 p-3 font-black text-ink">
          <span aria-hidden="true">{draft.kind === 'note' ? '📄' : '❓'}</span>
          {draft.title}
          <span className="text-xs font-bold text-ink-3">
            {draft.kind === 'note' ? `pages ${draft.pages?.join(', ')}` : plural(draft.count ?? 0, 'question')}
          </span>
          {draft.verified && <span className="chip border-primary/30 bg-primary-soft text-primary-ink">checked</span>}
          {errors.length > 0 && <span className="chip bg-danger-soft text-danger-ink">{plural(errors.length, 'error')}</span>}
          {draft.warnings.length > 0 && <span className="chip bg-accent-soft text-accent-ink">{plural(draft.warnings.length, 'warning')}</span>}
        </summary>
        <div className="flex flex-col gap-3 border-t border-line p-3">
          {errors.map((e) => (
            <p key={e} className="text-sm font-bold text-danger-ink">
              ❌ {e}
            </p>
          ))}
          {draft.warnings.map((w) => (
            <p key={w} className="text-sm font-bold text-accent-ink">
              ⚠️ {w}
            </p>
          ))}
          {draft.skipped && draft.skipped.length > 0 && (
            <div className="text-sm font-bold text-ink-2">
              <p>Left out ({draft.skipped.length}): the AI found no answer for these in the book or the notes. Add them by hand if needed.</p>
              <ul className="ms-5 list-disc">
                {draft.skipped.map((s) => (
                  <li key={`${s.page}-${s.number}`}>
                    Page {s.page}, no. {s.number}: {s.question_rumi}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {draft.kind === 'note' && draft.pages && (
            <div className="flex flex-wrap gap-2">
              {draft.pages.map((n) => (
                <button key={n} type="button" aria-pressed={page?.n === n} className="btn-ghost text-sm" onClick={() => showPage(n)}>
                  🖼️ Page {n}
                </button>
              ))}
            </div>
          )}
          <div className={page ? 'grid gap-3 lg:grid-cols-2' : ''}>
            {page && <img src={page.url} alt={`Page ${page.n} of the book`} className="max-h-[70vh] w-full rounded-xl border border-line object-contain" />}
            <label htmlFor={editorId} className="flex flex-col gap-1.5">
              <span className="eyebrow">{draft.kind === 'note' ? 'Note (Markdown)' : 'Questions (JSON)'}</span>
              <textarea
                id={editorId}
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={18}
                spellCheck={false}
                dir="ltr"
                className="field min-h-72 font-mono text-sm leading-relaxed [unicode-bidi:plaintext]"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-primary text-sm" disabled={!dirty || saving} onClick={() => save()}>
              {saving ? '⏳ Saving…' : '💾 Save'}
            </button>
            {draft.kind === 'note' && !draft.verified && (
              <button type="button" className="btn-secondary text-sm" disabled={saving} onClick={markChecked}>
                ✅ Checked by a teacher
              </button>
            )}
            <button type="button" className="btn-ghost text-sm" onClick={remove}>
              🗑️ Leave this out
            </button>
          </div>
        </div>
      </details>
    </li>
  )
}
