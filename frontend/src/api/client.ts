// Thin wrapper over fetch for the FastAPI backend (proxied at /api in dev).
import type { Assessment, ChatResponse, ChatTurn, Health, NoteResponse, Progress, Question, Student, Subject } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiError(0, 'Tidak dapat berhubung dengan pelayan.')
  }
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
