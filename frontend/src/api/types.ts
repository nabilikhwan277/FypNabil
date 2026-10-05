// Types mirroring the FastAPI responses (backend/app/main.py).

export interface Bi {
  rumi: string
  jawi: string
}

export interface Student {
  id: number
  name: string
  kelas: string
  avatar: string
}

/** Topic as stored in the catalog (what /questions/next and /topics/{id}/note return). */
export interface TopicMeta {
  id: string
  subject: SubjectId
  bab: number
  bab_rumi: string
  bab_jawi: string
  title_rumi: string
  title_jawi: string
  book_pages: number[]
  order: number
  question_counts: Record<string, number>
  verified: boolean
}

/** Topic with the pupil's progress (from /subjects?student_id=...). */
export interface Topic extends TopicMeta {
  mastery: number
  attempts: number
  level_unlocked: number
  has_questions: boolean
}

export type SubjectId = 'fiqh' | 'jawi' | 'tajwid'

export interface Bab {
  bab: number
  title_rumi: string
  title_jawi: string
  topics: Topic[]
}

export interface Subject {
  id: SubjectId
  name_rumi: string
  name_jawi: string
  babs: Bab[]
  topic_count: number
  mastery: number
}

export interface Source extends Bi {
  topic_rumi: string
  topic_jawi: string
  book_pages: number[]
}

export interface NoteResponse {
  topic: TopicMeta
  markdown: string
  source: Source
}

export interface Question {
  id: string
  topic_id: string
  subject: SubjectId
  level: number
  type: 'short' | 'structured' | 'essay'
  question_rumi: string
  question_jawi: string
  max_marks: number
  origin: string
  criteria_count: number
  topic: TopicMeta
}

export interface Mistake extends Bi {
  criterion: string
  status: 'separa' | 'tidak'
}

export interface Feedback {
  score: number
  max_marks: number
  percent: number
  stars: number
  xp_gained: number
  verdict: Bi
  mistakes: Mistake[]
  correct_answer: Bi
  source: Source
  repeated: Bi | null
  suggestion: Bi & { action: 'next_level' | 'read_note' | 'similar' | 'continue'; level: number }
  encouragement: Bi & { source: string }
  mastery: { before: number; after: number }
  level: { before: number; after: number; unlocked: boolean }
}

export interface TraceStep {
  step: number
  thought: string
  action: string
  action_input: Record<string, unknown>
  observation: Record<string, unknown>
  ms: number
}

export interface Criterion {
  criterion: string
  marks: number
  awarded: number
  met: 'ya' | 'separa' | 'tidak'
  layer: string
  evidence: string
}

export interface Assessment {
  attempt_id: number | null
  question_id: string
  score: number
  max_marks: number
  percent: number
  feedback: Feedback
  criteria: Criterion[]
  trace: TraceStep[]
  new_badges: string[]
  latency_ms: number
}

export interface ProgressTopic {
  id: string
  title_rumi: string
  title_jawi: string
  mastery: number
  attempts: number
  level_unlocked: number
}

export interface Progress {
  student: Student
  xp: number
  streak_days: number
  last_active_date: string | null
  badges: string[]
  subjects: { id: SubjectId; name_rumi: string; name_jawi: string; mastery: number; topic_count: number; topics: ProgressTopic[] }[]
  recent: { id: number; question_id: string; topic_id: string; subject: SubjectId; level: number; percent: number; created_at: string }[]
}

export interface Health {
  status: string
  llm_model: string
  llm_loaded: boolean
  embed_model: string
  embedder_loaded: boolean
  warm_up: 'idle' | 'loading' | 'ready' | 'error'
  scoring_config?: string
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatSource {
  topic_rumi: string
  topic_jawi: string
  pages: number[]
}

export interface ChatResponse {
  reply: string
  sources: ChatSource[]
  turns_left: number
}
