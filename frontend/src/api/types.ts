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
  /** Objective (A-D) version: stem and options only, never the correct option. */
  choices?: { stem_rumi: string; stem_jawi: string; spelling: boolean; options: Bi[] }
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
  /** Feedback written by the live LLM marker (only when KAFA_SCORER is an LLM configuration). */
  ai_feedback?: Bi & { config: string }
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
  live_scorer?: string
  researcher_mode?: boolean
  llm_location?: 'colab' | 'local' | 'none'
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

// ── Evaluation dashboard (/api/eval/summary) ─────────────────────────────────
export interface EvalMetrics {
  items?: number
  item_exact?: number
  within_1?: number
  mae_marks?: number
  mae_pct?: number
  qwk_band?: number
  crit_acc?: number
  over_marked?: number
  under_marked?: number
}

export interface EvalGrounding {
  faithfulness: number | null
  context_recall: number | null
  context_precision: number | null
  unsupported_per_answer: number | null
  answers_with_unsupported: number | null
  n: number
  judge: string
  cost: number
}

export interface EvalRun {
  file: string
  step: string
  config: string
  system: string
  model: string
  model_label: string
  rag: string
  react: string
  memory: boolean
  data: 'silver' | 'teacher'
  labels: string
  n: number
  repeats: number
  date: string
  complete: boolean
  overall: EvalMetrics
  by_subject: Record<string, EvalMetrics>
  by_level: Record<string, EvalMetrics>
  keyword_illusion: EvalMetrics | null
  success_rate: number
  latency_ms: { mean: number; p95: number }
  cost_total: number
  cost_per_100: number
  calls_per_answer: number
  tokens_per_answer: number
  cov_pct: number | null
  same_score_all_repeats: number | null
  worst: { answer_id: string; gold: number; pred: number; max: number; kind: string }[]
  grounding: EvalGrounding | null
  unsupported_examples: string[]
}

export interface EvalTarget {
  value: number | null
  target: number | string
  met: boolean | null
}

export interface EvalSummary {
  labels: 'silver' | 'teacher' | 'teacher-provisional'
  teacher_data_ready: boolean
  final: EvalRun | null
  targets: Record<'qwk' | 'within_1' | 'faithfulness' | 'context_recall' | 'win_rate' | 'likert' | 'sus' | 'cov', EvalTarget> & {
    human_level?: EvalTarget & { config: string }
  }
  teacher_compare: TeacherCompare | null
  rag_eval: RagEval | null
  rag_settings: RagSettings | null
  runs: EvalRun[]
  agreement: {
    raters?: number
    names?: string[]
    exact: number
    kappa: number
    qwk: number
    fleiss?: number
    criteria_both: number
    criteria_total: number
    same_score: number
    answers: number
    to_discuss: number
  } | null
  ab: {
    teachers: number
    comparisons: number
    memory_wins: number
    memory_losses: number
    ties: number
    win_rate: number | null
    likert: Record<'on' | 'off', Record<string, number>>
    likert_mean: Record<'on' | 'off', number | null>
  } | null
  sus: { groups: Record<string, { n: number; mean: number }>; comments: string[] } | null
  models: { key: string; label: string; id: string; provider: string; local: boolean }[]
  spend: { spent: number; budget: number }
  live_scorer: string
}

// ── Qwen on Google Colab (/api/settings/qwen) ────────────────────────────────
export interface QwenStatus {
  ok: boolean
  model?: string
  gpu?: string
  error?: string
}

export interface QwenEndpoint {
  url: string
  has_key: boolean
  local_llm: boolean
  status: QwenStatus | null
}

// ── E1 with several teachers (eval/teacher_compare.py) ───────────────────────
export interface TeacherCompareRun {
  file: string
  step: string
  config: string
  system: string
  model_label: string
  rag: string
  react: string
  memory: boolean
  n: number
  vs: Record<string, EvalMetrics>
  mean_qwk_teachers: number
  mean_exact_teachers: number
  agreed_criteria_acc: number | null
  agreed_criteria_n: number
  human_level: boolean | null
}

export interface TeacherCompare {
  date: string
  teachers: Record<string, string>
  answers: number
  agreed_answers: number
  agreed_criteria: number
  final_ready: boolean
  human: Record<string, EvalMetrics>
  human_qwk: number | null
  human_exact: number | null
  runs: TeacherCompareRun[]
}

// ── RAG evaluation (eval/rag_eval.py) ─────────────────────────────────────────
export interface RagMetrics {
  context_precision: number | null
  context_recall: number | null
  faithfulness: number | null
  answer_relevancy: number | null
  factual_correctness: number | null
}

export interface RagEval {
  date: string
  generator: string
  judge: string
  embedding: string
  n: number
  rags: {
    rag: 'R1' | 'R2' | 'R3'
    summary: RagMetrics & {
      declined: number
      answerable: number
      out_of_syllabus_declined: number
      out_of_syllabus: number
      out_of_syllabus_by_kind?: Record<'general' | 'near', { declined: number; n: number }>
      retrieved_mean?: number
      passages_given_mean?: number
      context_chars_mean?: number
      retrieval_ms_mean: number
      cost: number
      by_subject: Record<string, RagMetrics>
    }
    examples: { question: string; answer: string; reference: string }[]
  }[]
}

// ── RAG settings study of R3 (eval/rag_settings.py) ───────────────────────────
export interface GoldMetrics {
  hit_rate: number | null
  evidence_recall: number | null
  precision: number | null
  mrr: number | null
}

/** Mean change from the current option, with a 95% bootstrap interval: [mean, low, high]. */
export type DiffCI = [number, number, number] | null

export interface RagSettingOption {
  option: string
  current: boolean
  metrics: GoldMetrics & { passages: number | null; chars: number }
  rejected: number
  oos_rejected: Record<'general' | 'near', number>
  answers?: {
    faithfulness: number | null
    factual_correctness: number | null
    declined: number
    oos_declined: Record<'general' | 'near', number>
    answer_cost_per_100: number
    tokens_in_mean: number
  }
  diff?: Record<string, DiffCI>
}

export interface RagSetting {
  key: string
  setting: string
  what: string
  tested: string
  evidence: string
  selection: string
  options: RagSettingOption[]
}

export interface RagSettings {
  date: string
  rag: string
  generator: string
  judge: string
  embedding: string
  answers_run: boolean
  n: number
  n_reachable: number
  oos: Record<'general' | 'near', number>
  gold: { statements: number; statements_in_textbook: number; questions_without_evidence: string[]; pool_sections_mean: number }
  settings: RagSetting[]
  rag_types: Record<string, { metrics: GoldMetrics; n: number; judge_recall: number | null; agreement: { mean_abs_diff: number | null; pearson: number | null } }>
  similarity: {
    top_cosine: Record<'answerable' | 'general' | 'near', { min: number; median: number; max: number }>
    steps: {
      threshold: number
      chunks_removed: number
      answerable_rejected: number
      hit_rate: number | null
      evidence_recall?: number | null
      general_rejected: number
      near_rejected: number
    }[]
    chat_gate?: { threshold: number; answerable_rejected: number; general_rejected: number; near_rejected: number }
  }
  spent: number
}

// ── Admin (backend/app/admin_api.py) ──────────────────────────────────────────
export interface AdminSession {
  token: string
  expires: number
}

export interface LiveConfig {
  config: string
  system: string
  system_label: string
  model: string
  model_label: string
  rag: string
  rag_label: string
  react: string
  react_label: string
  memory: boolean | null
}

export interface ModelOption {
  key: string
  label: string
  provider: string
  ok: boolean
  where: string
  reason?: string
}

export interface EvalDataset {
  data: 'teacher' | 'silver'
  labels: string
  label: string
  answers: number
}

export interface AdminConfig {
  live: LiveConfig
  set_at: string | null
  syllabus_changed_at: string | null
  options: {
    systems: { key: string; label: string }[]
    models: ModelOption[]
    rags: { key: string; label: string }[]
    reacts: { key: string; label: string }[]
  }
  datasets: EvalDataset[]
}

export interface EvalEstimate {
  answers: number
  cost: number
  note: string
}

export interface Job {
  id: number
  kind: 'evaluation' | 'book'
  title: string
  status: 'running' | 'done' | 'failed'
  done: number
  total: number
  message: string
  result: Record<string, unknown>
  error: string
  started: number
  finished: number | null
}

export type BookStatus = 'uploaded' | 'processing' | 'draft' | 'active' | 'removed' | 'failed'

export interface Book {
  id: string
  title: string
  subject: 'fiqh' | 'jawi' | 'tajwid'
  kind: 'textbook' | 'exercise'
  year: number
  origin: 'builtin' | 'upload'
  status: BookStatus
  created: string
  updated: string
  pages: number
  cost: number
  error?: string
  source_file?: string
  topics: number
  questions: number
  estimate: number
}

export interface Draft {
  path: string
  kind: 'note' | 'questions'
  title: string
  content: string
  errors: string[]
  warnings: string[]
  pages?: number[]
  verified?: boolean
  count?: number
  skipped?: { page: number; number: string; question_rumi: string; why: string }[]
  book_status: BookStatus
}
