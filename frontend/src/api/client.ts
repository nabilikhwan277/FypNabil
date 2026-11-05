// Thin wrapper over fetch for the FastAPI backend (proxied at /api in dev).
import { ADMIN_EXPIRED, loadAdmin, saveAdmin } from './adminToken'
import type {
  AdminConfig,
  AdminSession,
  Assessment,
  Book,
  ChatResponse,
  ChatTurn,
  Draft,
  EvalEstimate,
  EvalSummary,
  Health,
  Job,
  LiveConfig,
  NoteResponse,
  Progress,
  Question,
  QwenEndpoint,
  QwenStatus,
  Student,
  Subject,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function send(path: string, init?: RequestInit, admin = false): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init?.headers as Record<string, string>) }
  const session = admin ? loadAdmin() : null
  if (session) headers.Authorization = `Bearer ${session.token}`
  let res: Response
  try {
    res = await fetch(`/api${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Tidak dapat berhubung dengan pelayan.')
  }
  if (admin && res.status === 401) {
    saveAdmin(null) // expired or signed out elsewhere: back to the sign-in page
    window.dispatchEvent(new Event(ADMIN_EXPIRED))
  }
  return res
}

async function request<T>(path: string, init?: RequestInit, admin = false): Promise<T> {
  const res = await send(path, init, admin)
  if (!res.ok) {
    let msg = res.statusText
    try {
      const body = await res.json()
      msg = typeof body.detail === 'string' ? body.detail : msg
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg)
  }
  return (await res.json()) as T
}

const qs = (params: Record<string, string | number | undefined | null>) => {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => request<Health>('/health'),
  avatars: () => request<string[]>('/avatars'),
  login: (name: string, kelas: string, avatar: string) =>
    request<Student>('/auth/login', { method: 'POST', body: JSON.stringify({ name, kelas, avatar }) }),
  subjects: (studentId?: number) => request<Subject[]>(`/subjects${qs({ student_id: studentId })}`),
  note: (topicId: string) => request<NoteResponse>(`/topics/${encodeURIComponent(topicId)}/note`),
  nextQuestion: (studentId: number, opts: { subject?: string; topicId?: string; level?: number }) =>
    request<Question>(
      `/questions/next${qs({ student_id: studentId, subject: opts.subject, topic_id: opts.topicId, level: opts.level })}`,
    ),
  answer: (studentId: number, questionId: string, answer: string) =>
    request<Assessment>('/answers', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId, question_id: questionId, answer }),
    }),
  progress: (studentId: number) => request<Progress>(`/progress/${studentId}`),
  // ── admin (needs the admin sign-in) ──
  adminLogin: (password: string) => request<AdminSession>('/admin/login', { method: 'POST', body: JSON.stringify({ password }) }),
  evalSummary: () => request<EvalSummary>('/eval/summary', undefined, true),
  qwenEndpoint: () => request<QwenEndpoint>('/settings/qwen', undefined, true),
  saveQwenEndpoint: (url: string, key: string) =>
    request<{ saved: boolean; status: QwenStatus }>('/settings/qwen', { method: 'POST', body: JSON.stringify({ url, key }) }, true),
  clearQwenEndpoint: () => request<{ saved: boolean }>('/settings/qwen', { method: 'DELETE' }, true),
  adminConfig: () => request<AdminConfig>('/admin/config', undefined, true),
  setLiveConfig: (config: string) => request<LiveConfig>('/admin/config', { method: 'POST', body: JSON.stringify({ config }) }, true),
  evalEstimate: (config: string, data: string, labels: string) =>
    request<EvalEstimate>(`/admin/evaluate/estimate${qs({ config, data, labels })}`, undefined, true),
  startEvaluation: (config: string, data: string, labels: string) =>
    request<Job>('/admin/evaluate', { method: 'POST', body: JSON.stringify({ config, data, labels }) }, true),
  job: (id: number) => request<Job>(`/admin/jobs/${id}`, undefined, true),
  latestJob: (kind: Job['kind']) => request<Job | null>(`/admin/jobs/latest${qs({ kind })}`, undefined, true),
  books: () => request<Book[]>('/admin/books', undefined, true),
  uploadBook: (file: File, meta: { title: string; subject: string; kind: string }) =>
    request<Book>(
      `/admin/books${qs({ ...meta, filename: file.name })}`,
      { method: 'POST', body: file, headers: { 'Content-Type': 'application/pdf' } },
      true,
    ),
  processBook: (id: string) => request<Job>(`/admin/books/${encodeURIComponent(id)}/process`, { method: 'POST' }, true),
  drafts: (id: string) => request<Draft[]>(`/admin/books/${encodeURIComponent(id)}/drafts`, undefined, true),
  saveDraft: (id: string, path: string, content: string) =>
    request<{ path: string; errors: string[] }>(
      `/admin/books/${encodeURIComponent(id)}/drafts`,
      { method: 'POST', body: JSON.stringify({ path, content }) },
      true,
    ),
  deleteDraft: (id: string, path: string) =>
    request<{ deleted: string }>(`/admin/books/${encodeURIComponent(id)}/drafts${qs({ path })}`, { method: 'DELETE' }, true),
  bookAction: (id: string, action: 'publish' | 'remove' | 'restore') =>
    request<Book>(`/admin/books/${encodeURIComponent(id)}/${action}`, { method: 'POST' }, true),
  deleteBook: (id: string) => request<{ deleted: string }>(`/admin/books/${encodeURIComponent(id)}`, { method: 'DELETE' }, true),
  /** A page image of an uploaded book, as an object URL (the request needs the admin token). */
  pageImage: async (id: string, page: number) => {
    const res = await send(`/admin/books/${encodeURIComponent(id)}/pages/${page}`, undefined, true)
    if (!res.ok) throw new ApiError(res.status, res.statusText)
    return URL.createObjectURL(await res.blob())
  },
  chat: (studentId: number, message: string, history: ChatTurn[], subject?: string) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        student_id: studentId,
        message,
        subject: subject ?? null,
        history,
      }),
    }),
}
