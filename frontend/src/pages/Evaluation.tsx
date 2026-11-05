import { ChartColumn, RotateCcw } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { api } from '../api/client'
import type {
  DiffCI,
  EvalMetrics,
  EvalRun,
  EvalSummary,
  EvalTarget,
  GoldMetrics,
  RagEval,
  RagMetrics,
  RagSetting,
  RagSettings,
  TeacherCompare,
  TeacherCompareRun,
} from '../api/types'
import { Section, Table } from '../components/adminUi'
import { num, pct, usd } from '../components/format'
import { ErrorBox, Spinner } from '../components/ui'
import { useAsync } from '../hooks/useAsync'
import SystemSetup from './admin/SystemSetup'

// Researcher page (blueprint §4): results of the experiments and the three evaluations.
// Read-only; written in English (researcher page), unlike the pupil-facing pages.

const STEP_TITLES: Record<string, string> = {
  step1: 'Step 1 · LLM models',
  step0: 'Step 0 · Baselines (B1–B4)',
  step2: 'Step 2 · RAG types',
  step3: 'Step 3 · ReAct types',
  step4: 'Step 4 · Final configuration (memory off / on, 3 repeats)',
}
const STEP_ORDER = ['step1', 'step0', 'step2', 'step3', 'step4']
const SYSTEM_LABEL: Record<string, string> = {
  b1: 'B1 Zero-shot',
  b2: 'B2 Embedding similarity',
  b3: 'B3 RAG + rubric',
  b4: 'B4 RAG + rubric + verifier',
  proposed: 'Proposed system',
}
const TABS = ['System setup', 'Summary', 'RAG Evaluation', 'E1 Accuracy', 'Experiments', 'E2 Grounding', 'E3 Users', 'Cost & Performance', 'Qwen on Colab'] as const
type Tab = (typeof TABS)[number]

/** Short label: the proposed system is the default, so only baselines name their system. */
function runLabel(r: EvalRun): string {
  if (r.system === 'b2') return 'B2 · rules + bge-m3'
  const parts = r.system === 'proposed' ? [r.model_label] : [SYSTEM_LABEL[r.system].split(' ')[0], r.model_label]
  if (r.rag) parts.push(r.rag)
  if (r.react) parts.push(r.react)
  if (r.system === 'proposed') parts.push(r.memory ? 'memory on' : 'memory off')
  return parts.filter(Boolean).join(' · ')
}

function Status({ met }: { met: boolean | null }) {
  if (met === null) return <span className="chip text-ink-3">⏳ No data yet</span>
  return met ? (
    <span className="chip border-primary/30 bg-primary-soft text-primary-ink">✅ Target met</span>
  ) : (
    <span className="chip border-danger/30 bg-danger-soft text-danger-ink">❌ Not met</span>
  )
}

function TargetTile({ title, t, fmt, hint }: { title: string; t: EvalTarget; fmt: (v: number | null) => string; hint: string }) {
  return (
    <li className="flex flex-col gap-1 rounded-xl border border-line bg-surface-2 p-4">
      <span className="text-sm font-bold text-ink-3">{title}</span>
      <span className="text-3xl font-extrabold text-ink tabular-nums">{fmt(t.value)}</span>
      <span className="text-sm text-ink-3">
        Target: {typeof t.target === 'number' ? fmt(t.target) : t.target}
      </span>
      <span className="mt-1">
        <Status met={t.met} />
      </span>
      <span className="mt-1 text-xs font-bold text-ink-3">{hint}</span>
    </li>
  )
}

/** Horizontal single-series bar chart: one hue, value labels, optional target line, hover details. */
function BarChart({
  rows,
  max = 1,
  target,
  fmt,
  label,
  narrow = false,
}: {
  narrow?: boolean
  rows: { key: string; label: string; value: number | null; detail?: string }[]
  max?: number
  target?: number
  fmt: (v: number) => string
  label: string
}) {
  const [hover, setHover] = useState<string | null>(null)
  const scale = (v: number) => `${Math.max(0, Math.min(1, v / max)) * 100}%`
  return (
    <figure>
      <div role="img" aria-label={`${label}: ${rows.map((r) => `${r.label} ${r.value === null ? 'none' : fmt(r.value)}`).join(', ')}`}>
        <ul className="flex flex-col gap-2" aria-hidden="true">
          {rows.map((r) => (
            <li
              key={r.key}
              className={`grid items-center gap-3 ${narrow ? 'grid-cols-[2.5rem_1fr_3.5rem]' : 'grid-cols-[minmax(0,19rem)_1fr_4.5rem] max-sm:grid-cols-[1fr_4rem]'}`}
              onMouseEnter={() => setHover(r.key)}
              onMouseLeave={() => setHover(null)}
            >
              <span className={`truncate text-sm font-bold text-ink-2 ${narrow ? '' : 'max-sm:col-span-2'}`} title={r.label}>
                {r.label}
              </span>
              <span className="relative h-6 rounded-md bg-surface-2">
                {r.value !== null && (
                  <span
                    className={`absolute inset-y-0 start-0 rounded-e-[4px] transition-[width] duration-500 ${hover === r.key ? 'bg-primary-hover' : 'bg-primary'}`}
                    style={{ width: scale(r.value) }}
                  />
                )}
                {target !== undefined && (
                  <span className="absolute inset-y-[-3px] w-0.5 bg-ink-3" style={{ insetInlineStart: scale(target) }} />
                )}
                {hover === r.key && r.detail && (
                  <span className="absolute start-0 bottom-full z-10 mb-1 w-max max-w-xs rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-bold text-ink shadow-md">
                    {r.label}: {r.value === null ? 'no data' : fmt(r.value)} · {r.detail}
                  </span>
                )}
              </span>
              <span className="text-end text-sm font-black text-ink tabular-nums">{r.value === null ? '–' : fmt(r.value)}</span>
            </li>
          ))}
        </ul>
      </div>
      {target !== undefined && (
        <figcaption className="mt-2 flex items-center gap-2 text-xs font-bold text-ink-3">
          <span aria-hidden="true" className="inline-block h-3 w-0.5 bg-ink-3" /> Line = blueprint target ({fmt(target)})
        </figcaption>
      )}
    </figure>
  )
}

function metricRow(name: string, m: EvalMetrics): ReactNode[] {
  return [name, m.items ?? '–', num(m.qwk_band), pct(m.item_exact), pct(m.within_1), num(m.mae_marks, 2), pct(m.over_marked), pct(m.under_marked)]
}
const METRIC_HEAD = ['Group', 'n', 'QWK', 'Exact', 'Within 1 mark', 'MAE', 'Over-marked', 'Under-marked']

function DataBadge({ labels }: { labels: string }) {
  if (labels.startsWith('teacher:') || labels === 'teacher-provisional')
    return <span className="chip border-info-ink/30 bg-info-soft text-info-ink">👩‍🏫 Teacher marks (provisional, not settled yet)</span>
  return labels === 'teacher' ? (
    <span className="chip border-primary/30 bg-primary-soft text-primary-ink">👩‍🏫 Teacher marks (final result)</span>
  ) : (
    <span className="chip border-accent/40 bg-accent-soft text-accent-ink">🧪 Silver set (development only)</span>
  )
}

function Summary({ d }: { d: EvalSummary }) {
  const t = d.targets
  return (
    <div className="flex flex-col gap-5">
      {d.labels === 'silver' && (
        <p role="note" className="rounded-2xl border border-accent/40 bg-accent-soft px-4 py-3 font-bold text-accent-ink">
          ⚠️ These results come from the <b>silver</b> set (AI-written answers and AI marks), for building and checking the system only.
          The thesis result (E1) comes from the 50 teacher-marked answers: run the experiments with <code>--data teacher</code> after the Google Form is filled in.
        </p>
      )}
      <Section title="Blueprint targets (§4.4)" note={d.final ? `Final configuration: ${runLabel(d.final)}` : 'No final configuration yet (Step 4).'}>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {t.human_level && (
            <TargetTile
              title="E1 · Human level"
              t={t.human_level}
              fmt={(v) => num(v)}
              hint="Mean QWK with each teacher; target = QWK between the teachers"
            />
          )}
          <TargetTile title="E1 · QWK with reference marks" t={t.qwk} fmt={(v) => num(v)} hint="Agreement with the markers (1 = perfect)" />
          <TargetTile title="E1 · Within 1 mark" t={t.within_1} fmt={(v) => pct(v)} hint="Answers that differ by at most 1 mark" />
          <TargetTile title="E2 · Faithfulness" t={t.faithfulness} fmt={(v) => num(v, 2)} hint="Feedback facts supported by the textbook" />
          <TargetTile title="E2 · Context recall" t={t.context_recall} fmt={(v) => num(v, 2)} hint="Retrieved text contains the answer" />
          <TargetTile title="E3 · Memory win-rate" t={t.win_rate} fmt={(v) => pct(v)} hint="Teachers prefer feedback with memory" />
          <TargetTile title="E3 · Teacher rating (Likert)" t={t.likert} fmt={(v) => num(v, 2)} hint="Mean of 1–5 over four aspects" />
          <TargetTile title="E3 · SUS (teachers)" t={t.sus} fmt={(v) => num(v, 1)} hint="Usability, ≥ 68 = above average" />
          <TargetTile
            title="Consistency · CoV"
            t={{ ...t.cov, target: d.agreement ? 'lower than between teachers' : 'low' }}
            fmt={(v) => (v === null ? '–' : `${v.toFixed(1)}%`)}
            hint="Spread of marks over 3 repeats (0% = same every time)"
          />
        </ul>
      </Section>
      {d.final && (
        <Section title="Final configuration">
          <Table
            head={['Part', 'Choice']}
            rows={[
              ['Model', `${d.final.model_label} (${d.final.model})`],
              ['RAG', d.final.rag],
              ['ReAct', d.final.react],
              ['Student memory', d.final.memory ? 'On' : 'Off'],
              ['Data', `${d.final.data} · ${d.final.n} answers · ${d.final.repeats} repeats`],
              ['Marker used in the app now', d.live_scorer === 'b2' ? 'b2 (local, no API)' : d.live_scorer],
            ]}
          />
        </Section>
      )}
    </div>
  )
}

function Accuracy({ d }: { d: EvalSummary }) {
  const f = d.final
  const a = d.agreement
  return (
    <div className="flex flex-col gap-5">
      <Section
        title="Agreement between teachers"
        note="Needed before the teacher marks can be used as the reference (scripts/teacher_sheet.py from-form)."
      >
        {a ? (
          <Table
            head={['Measure', 'Value']}
            rows={[
              ['Number of teachers', a.raters ?? 2],
              ['Exact agreement (all teachers the same)', pct(a.exact, 1)],
              [`Cohen's kappa${(a.raters ?? 2) > 2 ? ' (mean of pairs)' : ''}`, num(a.kappa)],
              ['QWK between teachers', num(a.qwk)],
              ["Fleiss' kappa", num(a.fleiss)],
              ['Answers with the same total score', `${a.same_score} / ${a.answers}`],
              ['Criteria discussed (no majority)', a.to_discuss],
            ]}
          />
        ) : (
          <p className="font-bold text-ink-3">⏳ Not yet. Download the Google Form responses, then run teacher_sheet.py from-form.</p>
        )}
      </Section>
      {d.teacher_compare && <PerTeacher c={d.teacher_compare} />}
      <Section title="System vs reference marks" note={f ? runLabel(f) : undefined}>
        {f ? (
          <div className="flex flex-col gap-4">
            <DataBadge labels={f.labels} />
            <Table head={METRIC_HEAD} rows={[metricRow('Overall', f.overall), ...Object.entries(f.by_subject).map(([k, m]) => metricRow(k, m)), ...Object.entries(f.by_level).map(([k, m]) => metricRow(k, m))]} />
            {f.keyword_illusion && (
              <p className="rounded-2xl bg-surface-2 px-4 py-3 font-bold text-ink-2">
                🪤 “Keyword illusion” check ({f.keyword_illusion.items} answers with the right words but a wrong ruling): over-marked {pct(f.keyword_illusion.over_marked)}, exact{' '}
                {pct(f.keyword_illusion.item_exact)}.
              </p>
            )}
            {f.worst.length > 0 && (
              <Table head={['Answer', 'Type', 'Reference', 'System', 'Max']} rows={f.worst.map((w) => [w.answer_id, w.kind, w.gold, w.pred, w.max])} />
            )}
          </div>
        ) : (
          <p className="font-bold text-ink-3">⏳ No Step 4 result yet.</p>
        )}
      </Section>
    </div>
  )
}

function compareLabel(r: TeacherCompareRun): string {
  if (r.system === 'b2') return 'B2 · rules + bge-m3'
  const parts = r.system === 'proposed' ? [r.model_label] : [SYSTEM_LABEL[r.system].split(' ')[0], r.model_label]
  if (r.rag) parts.push(r.rag)
  if (r.react) parts.push(r.react)
  if (r.system === 'proposed') parts.push(r.memory ? 'memory on' : 'memory off')
  return parts.filter(Boolean).join(' · ')
}

/** System vs each teacher, with the teacher-vs-teacher agreement as the human baseline. */
function PerTeacher({ c }: { c: TeacherCompare }) {
  const gurus = Object.keys(c.teachers)
  return (
    <>
      <Section
        title="Human baseline: teacher vs teacher"
        note={`${c.answers} answers · ${c.agreed_answers} answers and ${c.agreed_criteria} criteria where every teacher agreed`}
      >
        <Table
          head={['Pair', 'QWK', 'Exact', 'Within 1 mark', 'MAE']}
          rows={Object.entries(c.human).map(([k, m]) => [
            k.replace(/guru_\d+/g, (g) => c.teachers[g] ?? g),
            num(m.qwk_band),
            pct(m.item_exact),
            pct(m.within_1),
            num(m.mae_marks, 2),
          ])}
        />
      </Section>
      <Section
        title="System vs each teacher"
        note="Human level = the system agrees with the teachers at least as well as they agree with each other (line on the chart)."
      >
        {c.runs.length ? (
          <div className="flex flex-col gap-4">
            <BarChart
              label="Mean QWK with the teachers"
              target={c.human_qwk ?? undefined}
              fmt={(v) => v.toFixed(2)}
              rows={c.runs.map((r) => ({
                key: r.file,
                label: compareLabel(r),
                value: r.mean_qwk_teachers,
                detail: gurus.map((g) => `${c.teachers[g]} ${num(r.vs[g]?.qwk_band, 2)}`).join(', '),
              }))}
            />
            <Table
              head={['Configuration', ...gurus.map((g) => `QWK vs ${c.teachers[g]}`), 'Mean QWK', 'Agreed answers (QWK)', 'Agreed criteria correct', 'Human level']}
              rows={c.runs.map((r) => [
                compareLabel(r),
                ...gurus.map((g) => num(r.vs[g]?.qwk_band)),
                num(r.mean_qwk_teachers),
                num(r.vs.agreed?.qwk_band),
                r.agreed_criteria_acc === null ? '–' : `${pct(r.agreed_criteria_acc, 1)} of ${r.agreed_criteria_n}`,
                r.human_level === null ? '–' : r.human_level ? '✅ yes' : '❌ no',
              ])}
            />
          </div>
        ) : (
          <p className="font-bold text-ink-3">⏳ No runs on the teacher set yet. Run: eval\experiments.py plan --data teacher --n 0 --labels guru_1</p>
        )}
      </Section>
    </>
  )
}

const RAG_NAMES: Record<string, string> = {
  R1: 'R1 Naive Dense RAG',
  R2: 'R2 Hybrid RAG + Reranker',
  R3: 'R3 Parent-Document RAG',
}
const RAG_METRICS: { key: keyof RagMetrics; label: string; hint: string }[] = [
  { key: 'context_precision', label: 'Context precision', hint: 'Retrieved passages are relevant (rank-weighted)' },
  { key: 'context_recall', label: 'Context recall', hint: 'Retrieved text contains the reference answer' },
  { key: 'faithfulness', label: 'Faithfulness', hint: 'Answer claims supported by the retrieved text' },
  { key: 'answer_relevancy', label: 'Answer relevancy', hint: 'Answer addresses the question' },
  { key: 'factual_correctness', label: 'Factual correctness', hint: 'Claim F1 against the textbook reference answer' },
]
// Blueprint §6.2 targets per RAG type
const RAG_TARGETS = [
  { rag: 'R1', text: 'Baseline context precision about 0.60', check: (m: RagMetrics) => m.context_precision },
  { rag: 'R2', text: 'Retrieval recall and precision at least 0.78', check: (m: RagMetrics) => Math.min(m.context_recall ?? 0, m.context_precision ?? 0), target: 0.78 },
  { rag: 'R3', text: 'Highest faithfulness, at least 0.85', check: (m: RagMetrics) => m.faithfulness, target: 0.85 },
]

const RAG_VIEWS = [
  { key: 'types', label: '1 · RAG types (R1–R3)' },
  { key: 'settings', label: '2 · Settings of R3' },
] as const

/** RAG evaluation in two steps: choose the RAG type, then tune the settings inside it. */
function RagTab({ r, s }: { r: RagEval | null; s: RagSettings | null }) {
  const [view, setView] = useState<(typeof RAG_VIEWS)[number]['key']>('types')
  return (
    <div className="flex flex-col gap-5">
      <div role="group" aria-label="RAG evaluation step" className="flex flex-wrap gap-2">
        {RAG_VIEWS.map((v) => (
          <button
            key={v.key}
            type="button"
            aria-pressed={view === v.key}
            onClick={() => setView(v.key)}
            className={`min-h-11 cursor-pointer rounded-xl border-2 px-4 text-sm font-black transition ${
              view === v.key ? 'border-primary bg-primary-soft text-primary-ink' : 'border-line bg-surface text-ink-2 hover:border-line-strong'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>
      {view === 'types' ? <RagTypes r={r} /> : <RagSettingsView s={s} />}
    </div>
  )
}

/** RAG types R1-R3 compared with RAGAS-style metrics (eval/rag_eval.py), table in the style of a RAGAS results table. */
function RagTypes({ r }: { r: RagEval | null }) {
  if (!r) return <p className="card font-bold text-ink-3">⏳ Not run yet. Run: eval\rag_eval.py</p>
  const rags = r.rags
  const best = (key: keyof RagMetrics) => Math.max(...rags.map((x) => x.summary[key] ?? -1))
  const minDeclined = Math.min(...rags.map((x) => x.summary.declined))
  const cell = (v: number | null, isBest: boolean, digits = 3) => (
    <span className={`inline-block min-w-14 rounded-md px-2 py-0.5 font-black tabular-nums ${isBest ? 'bg-primary-soft text-primary-ink' : ''}`}>
      {v === null ? '–' : v.toFixed(digits)}
    </span>
  )
  return (
    <div className="flex flex-col gap-5">
      <Section
        title={`RAGAS results, mean over the ${r.n} answerable questions`}
        note={`Answer model ${r.generator} (fixed for every RAG type) · judge ${r.judge} (another provider) · embedding ${r.embedding} · ${r.date.slice(0, 10)}. Green = best in the row.`}
      >
        <Table
          head={['Metric', ...rags.map((x) => RAG_NAMES[x.rag])]}
          rows={[
            ...RAG_METRICS.map((m) => [m.label, ...rags.map((x) => cell(x.summary[m.key], x.summary[m.key] === best(m.key)))]),
            [`Declined answers (of ${r.n})`, ...rags.map((x) => cell(x.summary.declined, x.summary.declined === minDeclined, 0))],
            [
              `Out-of-syllabus correctly declined (of ${rags[0]?.summary.out_of_syllabus ?? 6})`,
              ...rags.map((x) => `${x.summary.out_of_syllabus_declined} / ${x.summary.out_of_syllabus}`),
            ],
            ...(rags[0]?.summary.out_of_syllabus_by_kind
              ? (['general', 'near'] as const).map((k) => [
                  `· ${k === 'general' ? 'general questions' : 'near the syllabus'}`,
                  ...rags.map((x) => {
                    const b = x.summary.out_of_syllabus_by_kind?.[k]
                    return b ? `${b.declined} / ${b.n}` : '–'
                  }),
                ])
              : []),
            ...(rags[0]?.summary.passages_given_mean !== undefined
              ? [
                  [
                    'Passages retrieved → read by the model',
                    ...rags.map((x) => `${x.summary.retrieved_mean} → ${x.summary.passages_given_mean}`),
                  ],
                  ['Characters read (mean)', ...rags.map((x) => (x.summary.context_chars_mean ?? 0).toLocaleString('en'))],
                ]
              : []),
            [
              'Retrieval time (mean)',
              ...rags.map((x) => {
                const ms = x.summary.retrieval_ms_mean
                return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
              }),
            ],
            ['Cost (answers + judge)', ...rags.map((x) => usd(x.summary.cost, 3))],
          ]}
        />
      </Section>

      <Section title="Each metric by RAG type">
        <div className="grid gap-5 lg:grid-cols-2">
          {RAG_METRICS.map((m) => (
            <div key={m.key}>
              <p className="mb-2 font-black text-ink">{m.label}</p>
              <BarChart
                narrow
                label={m.label}
                fmt={(v) => v.toFixed(2)}
                rows={rags.map((x) => ({ key: x.rag, label: x.rag, value: x.summary[m.key], detail: `${RAG_NAMES[x.rag]}: ${m.hint}` }))}
              />
            </div>
          ))}
        </div>
      </Section>

      <Section title="Blueprint targets for the RAG types (§6.2)">
        <Table
          head={['RAG type', 'Target', 'Result', 'Met?']}
          rows={RAG_TARGETS.map((t) => {
            const x = rags.find((y) => y.rag === t.rag)
            const v = x ? t.check(x.summary) : null
            const met = v === null || v === undefined || t.target === undefined ? null : v >= t.target
            return [RAG_NAMES[t.rag], t.text, num(v ?? null), met === null ? 'reference' : met ? '✅ yes' : '❌ no']
          })}
        />
      </Section>

      <Section title="By subject">
        <Table
          head={['Metric', ...rags.flatMap((x) => ['fiqh', 'jawi', 'tajwid'].map((sub) => `${x.rag} · ${sub}`))]}
          rows={RAG_METRICS.map((m) => [m.label, ...rags.flatMap((x) => ['fiqh', 'jawi', 'tajwid'].map((sub) => num(x.summary.by_subject[sub]?.[m.key] ?? null, 2)))])}
        />
      </Section>

      <Section title="Example answers">
        <ul className="flex flex-col gap-3">
          {rags.flatMap((x) =>
            x.examples.map((e, i) => (
              <li key={`${x.rag}-${i}`} className="rounded-2xl border border-line bg-surface-2 p-3 text-sm">
                <p className="font-black text-ink">
                  <span className="chip me-2">{x.rag}</span>
                  {e.question}
                </p>
                <p className="mt-2 text-ink-2">
                  <b className="text-ink">System:</b> {e.answer}
                </p>
                <p className="mt-1 text-ink-3">
                  <b>Textbook reference:</b> {e.reference}
                </p>
              </li>
            )),
          )}
        </ul>
      </Section>
    </div>
  )
}

const GOLD_METRICS: { key: keyof GoldMetrics; label: string; hint: string }[] = [
  { key: 'hit_rate', label: 'Hit rate', hint: 'questions where the text the model reads holds at least one supporting textbook line' },
  { key: 'evidence_recall', label: 'Evidence recall', hint: 'statements of the reference answer whose supporting line the model reads' },
  { key: 'precision', label: 'Precision', hint: 'relevant sections among those read, weighted by rank (RAGAS average precision)' },
  { key: 'mrr', label: 'MRR', hint: '1 / rank of the first relevant section' },
]

/** Change from the current option; "clear" when its 95% bootstrap interval leaves out 0. */
function Delta({ d }: { d?: DiffCI }) {
  if (!d) return null
  const [m, lo, hi] = d
  const clear = lo > 0 || hi < 0
  const sign = (v: number) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(2)}`
  return (
    <span
      className={`block text-xs ${clear ? 'font-black text-ink' : 'font-bold text-ink-3'}`}
      title={`Change from the current option: ${sign(m)} (95% interval ${sign(lo)} to ${sign(hi)})`}
    >
      {sign(m)}
      {clear ? ' clear' : ''}
    </span>
  )
}

function withDelta(v: number | null | undefined, d?: DiffCI) {
  return (
    <>
      <span className="font-black text-ink">{num(v ?? null)}</span>
      <Delta d={d} />
    </>
  )
}

function SettingDetail({ x, nAll, oosAll }: { x: RagSetting; nAll: number; oosAll: number }) {
  const withAnswers = x.options.some((o) => o.answers)
  const head = [
    'Option',
    ...GOLD_METRICS.map((m) => m.label),
    'Sections read',
    'Characters read',
    ...(withAnswers ? ['Faithfulness', 'Factual correctness', `Declined (of ${nAll})`, `Out-of-syllabus declined (of ${oosAll})`] : []),
  ]
  const rows = x.options.map((o) => [
    <span className="font-bold text-ink">
      {o.option}
      {o.current && <span className="chip ms-2 border-primary/30 bg-primary-soft text-primary-ink">current</span>}
    </span>,
    ...GOLD_METRICS.map((m) => withDelta(o.metrics[m.key], o.diff?.[m.key])),
    num(o.metrics.passages, 2),
    o.metrics.chars.toLocaleString('en'),
    ...(withAnswers
      ? o.answers
        ? [
            withDelta(o.answers.faithfulness, o.diff?.faithfulness),
            withDelta(o.answers.factual_correctness, o.diff?.factual_correctness),
            o.answers.declined,
            o.answers.oos_declined.general + o.answers.oos_declined.near,
          ]
        : ['–', '–', '–', '–']
      : []),
  ])
  return (
    <Section title={x.setting} note={x.what}>
      <Table head={head} rows={rows} />
    </Section>
  )
}

function SimilarityDetail({ s }: { s: RagSettings }) {
  const c = s.similarity.top_cosine
  const g = s.similarity.chat_gate
  const r = (v: { min: number; median: number; max: number }) => `${v.min.toFixed(2)}–${v.max.toFixed(2)} (median ${v.median.toFixed(2)})`
  return (
    <Section
      title="Minimum similarity"
      note={
        `bge-m3 cosine of the best matched chunk: answerable questions ${r(c.answerable)} · general out-of-syllabus ${r(c.general)} · near the syllabus ${r(c.near)}.` +
        (g
          ? ` Tanya Bulan's own gate (${g.threshold.toFixed(2)} on its best match in the subject) turns away ${g.answerable_rejected} of ${s.n} answerable, ` +
            `${g.general_rejected} of ${s.oos.general} general and ${g.near_rejected} of ${s.oos.near} near-syllabus questions.`
          : '')
      }
    >
      <Table
        head={[
          'Threshold',
          'Matched chunks removed',
          `Answerable questions rejected (of ${s.n})`,
          'Hit rate',
          'Evidence recall',
          `General out-of-syllabus rejected (of ${s.oos.general})`,
          `Near-syllabus rejected (of ${s.oos.near})`,
        ]}
        rows={s.similarity.steps.map((t) => [
          <span className="font-bold text-ink">
            {t.threshold ? t.threshold.toFixed(2) : '0 (none)'}
            {t.threshold === 0 && <span className="chip ms-2 border-primary/30 bg-primary-soft text-primary-ink">current (R3)</span>}
            {t.threshold === 0.55 && <span className="chip ms-2">Tanya Bulan chat</span>}
          </span>,
          pct(t.chunks_removed),
          t.answerable_rejected,
          num(t.hit_rate),
          num(t.evidence_recall ?? null),
          t.general_rejected,
          t.near_rejected,
        ])}
      />
    </Section>
  )
}

/** Settings study of the selected RAG type (eval/rag_settings.py): a thesis table Setting | Options | Evidence | Selection. */
function RagSettingsView({ s }: { s: RagSettings | null }) {
  if (!s) return <p className="card font-bold text-ink-3">⏳ Not run yet. Run: eval\rag_settings.py</p>
  const oosAll = s.oos.general + s.oos.near
  return (
    <div className="flex flex-col gap-5">
      <Section
        title={`Settings of the selected RAG type (${s.rag})`}
        note={`One setting changed at a time, all others at the current value · ${s.n} answerable + ${oosAll} out-of-syllabus questions · answer model ${s.generator}, judge ${s.judge} · ${s.date.slice(0, 10)}`}
      >
        <Table
          wrap
          head={['Setting', 'Options tested', 'Evidence', 'Selection']}
          rows={s.settings.map((x) => [<b className="text-ink">{x.setting}</b>, x.tested, x.evidence, <b className="text-ink">{x.selection}</b>])}
        />
      </Section>

      <Section title="How the evidence was measured">
        <ul className="flex list-disc flex-col gap-1.5 ps-5 text-sm font-bold text-ink-2">
          <li>
            Gold evidence: the judge marked once which textbook lines state each statement of the reference answer ({s.gold.statements_in_textbook} of{' '}
            {s.gold.statements} statements are in the textbook). It read the question's own topic note plus every section any setting retrieved
            (about {s.gold.pool_sections_mean} sections per question), so every setting is scored on the same evidence.
          </li>
          {GOLD_METRICS.map((m) => (
            <li key={m.key}>
              <b className="text-ink">{m.label}</b>: {m.hint}.
            </li>
          ))}
          <li>
            Faithfulness, factual correctness and declined answers come from the same answer model and judge as the RAG-type table, for the
            settings that change what the model reads.
          </li>
          <li>Small numbers under a value: change from the current option over the same questions; "clear" when its 95% bootstrap interval leaves out 0.</li>
          {s.gold.questions_without_evidence.length > 0 && (
            <li>
              {s.gold.questions_without_evidence.length} of {s.n} questions have no supporting line in the notes, so retrieval metrics use {s.n_reachable}.
            </li>
          )}
        </ul>
      </Section>

      {s.settings.map((x) =>
        x.key === 'min_sim' ? <SimilarityDetail key={x.key} s={s} /> : <SettingDetail key={x.key} x={x} nAll={s.n} oosAll={oosAll} />,
      )}

      <Section
        title="Check: the RAG types on the same gold evidence"
        note="The RAG-type table uses the judge's context recall. Scoring R1–R3 with the gold evidence as well shows whether both measures agree."
      >
        <Table
          head={['RAG type', ...GOLD_METRICS.map((m) => m.label), 'Judge context recall', 'Mean |difference|', 'Pearson r']}
          rows={Object.entries(s.rag_types).map(([rag, t]) => [
            RAG_NAMES[rag] ?? rag,
            ...GOLD_METRICS.map((m) => num(t.metrics[m.key])),
            num(t.judge_recall),
            num(t.agreement.mean_abs_diff),
            num(t.agreement.pearson, 2),
          ])}
        />
      </Section>
    </div>
  )
}

function Experiments({ d }: { d: EvalSummary }) {
  const steps = STEP_ORDER.filter((s) => d.runs.some((r) => r.step === s))
  if (!steps.length) return <p className="card font-bold text-ink-3">⏳ No experiments yet. Run: eval\experiments.py plan</p>
  return (
    <div className="flex flex-col gap-5">
      {steps.map((s) => {
        const runs = d.runs.filter((r) => r.step === s)
        return (
          <Section key={s} title={STEP_TITLES[s] ?? s} note={<DataBadge labels={runs[0].labels} />}>
            <BarChart
              label={`QWK ${STEP_TITLES[s]}`}
              target={0.7}
              fmt={(v) => v.toFixed(2)}
              rows={runs.map((r) => ({
                key: r.file,
                label: runLabel(r),
                value: r.overall.qwk_band ?? null,
                detail: `exact ${pct(r.overall.item_exact)}, ${usd(r.cost_per_100, 3)} per 100 answers`,
              }))}
            />
            <details className="mt-4">
              <summary className="cursor-pointer font-black text-ink">Show table</summary>
              <div className="mt-3">
                <Table
                  head={['Configuration', 'n', 'QWK', 'Exact', 'Within 1', 'MAE', 'Success', 'CoV', '$/100']}
                  rows={runs.map((r) => [
                    runLabel(r),
                    `${r.n}${r.repeats > 1 ? `×${r.repeats}` : ''}`,
                    num(r.overall.qwk_band),
                    pct(r.overall.item_exact),
                    pct(r.overall.within_1),
                    num(r.overall.mae_marks, 2),
                    pct(r.success_rate),
                    r.cov_pct === null ? '–' : `${r.cov_pct.toFixed(1)}%`,
                    usd(r.cost_per_100, 3),
                  ])}
                />
              </div>
            </details>
          </Section>
        )
      })}
    </div>
  )
}

function Grounding({ d }: { d: EvalSummary }) {
  const runs = d.runs.filter((r) => r.grounding)
  if (!runs.length) return <p className="card font-bold text-ink-3">⏳ Not yet. Run: eval\grounding.py run &lt;experiment&gt;</p>
  return (
    <div className="flex flex-col gap-5">
      <Section title="Faithfulness (feedback facts supported by official material)" note="The judge is from a different provider than the model under test.">
        <BarChart
          label="Faithfulness"
          target={0.85}
          fmt={(v) => v.toFixed(2)}
          rows={runs.map((r) => ({ key: r.file, label: runLabel(r), value: r.grounding!.faithfulness, detail: `judge ${r.grounding!.judge}` }))}
        />
      </Section>
      <Section title="All grounding measures">
        <Table
          head={['Configuration', 'n', 'Faithfulness', 'Context recall', 'Context precision', 'Unsupported claims / answer', 'Judge']}
          rows={runs.map((r) => [
            runLabel(r),
            r.grounding!.n,
            num(r.grounding!.faithfulness, 2),
            num(r.grounding!.context_recall, 2),
            num(r.grounding!.context_precision, 2),
            num(r.grounding!.unsupported_per_answer, 2),
            r.grounding!.judge,
          ])}
        />
      </Section>
      {runs.some((r) => r.unsupported_examples.length) && (
        <Section title="Examples of unsupported claims (error analysis)">
          <ul className="flex flex-col gap-2">
            {runs.flatMap((r) =>
              r.unsupported_examples.map((u, i) => (
                <li key={`${r.file}-${i}`} className="rounded-xl bg-danger-soft px-3 py-2 text-sm font-bold text-danger-ink">
                  {u} <span className="text-ink-3">· {runLabel(r)}</span>
                </li>
              )),
            )}
          </ul>
        </Section>
      )}
    </div>
  )
}

function Users({ d }: { d: EvalSummary }) {
  const ab = d.ab
  return (
    <div className="flex flex-col gap-5">
      <Section title="Blind A/B comparison (memory off vs on)" note="scripts/ab_form.py make → borang Google → from-form">
        {ab ? (
          <div className="flex flex-col gap-4">
            <ul className="grid gap-3 sm:grid-cols-3">
              <TargetTile title="Memory win-rate" t={d.targets.win_rate} fmt={(v) => pct(v)} hint={`${ab.memory_wins} wins, ${ab.memory_losses} losses, ${ab.ties} ties`} />
              <TargetTile title="Likert (memory on)" t={d.targets.likert} fmt={(v) => num(v, 2)} hint={`${ab.teachers} teachers, ${ab.comparisons} comparisons`} />
              <li className="flex flex-col gap-1 rounded-2xl border border-line bg-surface-2 p-4">
                <span className="text-sm font-extrabold text-ink-3">Likert (memory off)</span>
                <span className="text-3xl font-black text-ink tabular-nums">{num(ab.likert_mean.off, 2)}</span>
              </li>
            </ul>
            <Table
              head={['Aspect', 'Memory on', 'Memory off']}
              rows={Object.keys(ab.likert.on ?? {}).map((k) => [k, num(ab.likert.on[k], 2), num(ab.likert.off?.[k], 2)])}
            />
          </div>
        ) : (
          <p className="font-bold text-ink-3">⏳ No teacher responses yet.</p>
        )}
      </Section>
      <Section title="Usability (SUS)" note="docs/SUS_soal_selidik.md → scripts/sus_score.py">
        {d.sus ? (
          <Table head={['Group', 'n', 'Mean SUS']} rows={Object.entries(d.sus.groups).map(([g, v]) => [g, v.n, v.mean.toFixed(1)])} />
        ) : (
          <p className="font-bold text-ink-3">⏳ No SUS responses yet.</p>
        )}
      </Section>
    </div>
  )
}

function Cost({ d }: { d: EvalSummary }) {
  const runs = d.runs
  return (
    <div className="flex flex-col gap-5">
      <Section title="API spending" note="Logged in storage/llm_calls.jsonl; repeated calls come from the cache (free).">
        <p className="text-3xl font-black text-ink tabular-nums">
          {usd(d.spend.spent, 3)} <span className="text-lg text-ink-3">of the {usd(d.spend.budget, 2)} limit</span>
        </p>
        <div className="mt-3 h-3 overflow-hidden rounded-full bg-surface-3" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((d.spend.spent / d.spend.budget) * 100)} aria-label="API spending">
          <div className="h-full rounded-full bg-accent" style={{ width: `${Math.min(100, (d.spend.spent / d.spend.budget) * 100)}%` }} />
        </div>
      </Section>
      {runs.length > 0 && (
        <>
          <Section title="Cost per 100 answers">
            <BarChart
              label="Cost per 100 answers"
              max={Math.max(...runs.map((r) => r.cost_per_100 || 0), 0.001)}
              fmt={(v) => `$${v.toFixed(3)}`}
              rows={runs.map((r) => ({ key: r.file, label: runLabel(r), value: r.cost_per_100, detail: `${r.calls_per_answer} calls per answer` }))}
            />
          </Section>
          <Section title="Time, tokens and success rate">
            <Table
              head={['Configuration', 'Mean ms', 'p95 ms', 'Tokens/answer', 'Calls/answer', 'Success', 'Total cost']}
              rows={runs.map((r) => [runLabel(r), r.latency_ms.mean, r.latency_ms.p95, r.tokens_per_answer, r.calls_per_answer, pct(r.success_rate), usd(r.cost_total)])}
            />
          </Section>
          <Section title="Models used">
            <Table head={['Key', 'Model', 'Full name', 'Provider']} rows={d.models.map((m) => [m.key, m.label, m.local ? 'local (4-bit)' : m.id, m.provider])} />
          </Section>
        </>
      )}
    </div>
  )
}

/** Paste the link + key printed by notebooks/qwen_colab_server.ipynb; the backend tests the link before saving it. */
function QwenColab() {
  const { data, error, loading, reload } = useAsync(() => api.qwenEndpoint(), [])
  const [url, setUrl] = useState('')
  const [key, setKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.saveQwenEndpoint(url.trim(), key.trim())
      setMsg({ ok: true, text: `Saved and connected: ${r.status.model ?? 'Qwen'} on ${r.status.gpu ?? 'Colab GPU'}.` })
      setKey('')
      reload()
    } catch (err) {
      setMsg({ ok: false, text: (err as Error).message })
    } finally {
      setBusy(false)
    }
  }
  const remove = async () => {
    setBusy(true)
    try {
      await api.clearQwenEndpoint()
      setMsg({ ok: true, text: 'Link removed.' })
      reload()
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  const st = data.status
  return (
    <div className="flex flex-col gap-5">
      <Section title="Where Qwen runs now">
        {data.url ? (
          <div className="flex flex-col gap-2">
            <p className="font-bold text-ink-2 break-all">
              Google Colab: <code>{data.url}</code> {data.has_key ? '(key saved)' : '(no key)'}
            </p>
            {st?.ok ? (
              <p className="chip w-fit border-primary/30 bg-primary-soft text-primary-ink">✅ Connected · {st.model} · {st.gpu}</p>
            ) : (
              <p className="chip w-fit border-danger/30 bg-danger-soft text-danger-ink">❌ Not answering: {st?.error}. Is the Colab notebook still running?</p>
            )}
          </div>
        ) : (
          <p className="font-bold text-ink-2">
            No Colab link saved.{' '}
            {data.local_llm
              ? 'Qwen runs on this laptop.'
              : 'Qwen is switched off on this laptop (KAFA_LOCAL_LLM=false): the experiment model "qwen" cannot run and Tanya Bulan answers from the textbook only, until you paste a link.'}
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={reload} className="btn-secondary min-h-11 text-sm">🔄 Check again</button>
          {data.url && (
            <button type="button" onClick={remove} disabled={busy} className="btn-secondary min-h-11 text-sm">🗑️ Remove link</button>
          )}
        </div>
      </Section>

      <Section title="Paste the Colab link" note="Shown at the end of cell 6 in notebooks/qwen_colab_server.ipynb. A new Colab session gives a new link: paste it again.">
        <form onSubmit={save} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="eyebrow">Link</span>
            <input className="field" required type="url" value={url} onChange={(e) => setUrl(e.target.value)}
              placeholder="https://xxxx-xx-xx.ngrok-free.app" autoComplete="off" spellCheck={false} />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="eyebrow">Key</span>
            <input className="field" type="password" value={key} onChange={(e) => setKey(e.target.value)}
              placeholder="the KEY printed by the notebook" autoComplete="off" spellCheck={false} />
          </label>
          {msg && (
            <p role="status" className={`rounded-2xl px-4 py-2.5 font-bold ${msg.ok ? 'bg-primary-soft text-primary-ink' : 'bg-danger-soft text-danger-ink'}`}>
              {msg.ok ? '✅ ' : '⚠️ '}
              {msg.text}
            </p>
          )}
          <button type="submit" disabled={busy || !url.trim()} className="btn-primary w-fit">
            {busy ? '⏳ Testing…' : '🔗 Save & test'}
          </button>
        </form>
      </Section>

      <Section title="How to start Qwen on Google Colab">
        <ol className="ms-5 flex list-decimal flex-col gap-1.5 font-bold text-ink-2">
          <li>Open <code>notebooks/qwen_colab_server.ipynb</code> in Google Colab (File → Upload notebook).</li>
          <li>Runtime → Change runtime type → <b>T4 GPU</b>.</li>
          <li>Add your ngrok token as a Colab secret named <code>NGROK_AUTHTOKEN</code> (free at dashboard.ngrok.com).</li>
          <li>Runtime → <b>Run all</b>, wait 3–5 minutes.</li>
          <li>Copy the <b>LINK</b> and <b>KEY</b> from cell 6 into the form above and click <b>Save &amp; test</b>.</li>
          <li>Keep the Colab tab open while you run experiments or use Tanya Bulan.</li>
        </ol>
      </Section>
    </div>
  )
}

export default function EvaluationPage() {
  const { data, error, loading, reload } = useAsync(() => api.evalSummary(), [])
  const [tab, setTab] = useState<Tab>('System setup')
  if (loading && !data) return <Spinner />
  if (error || !data) return <ErrorBox message={error ?? ''} onRetry={reload} />
  return (
    <section aria-labelledby="eval-title" className="flex flex-col gap-5" dir="ltr" lang="en">
      <div className="flex flex-wrap items-center gap-3">
        <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary-soft text-primary-ink">
          <ChartColumn className="h-6 w-6" />
        </span>
        <div className="min-w-0">
          <h1 id="eval-title" className="text-2xl font-extrabold text-ink sm:text-3xl">
            System Evaluation
          </h1>
          <p className="text-sm text-ink-3">How well the AI marker agrees with teachers, what it costs, and which settings the live system uses.</p>
        </div>
        <DataBadge labels={data.labels} />
        <button type="button" onClick={reload} className="btn-secondary ms-auto min-h-10 rounded-full px-4 text-sm">
          <RotateCcw aria-hidden="true" className="h-4 w-4" /> Reload
        </button>
      </div>
      <div role="tablist" aria-label="Evaluation sections" className="flex flex-wrap gap-1 rounded-2xl border border-line bg-surface p-1 shadow-sm">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`min-h-10 cursor-pointer rounded-xl px-3.5 text-sm font-bold transition ${
              tab === t ? 'bg-brand text-on-brand shadow-sm' : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" aria-label={tab}>
        {tab === 'System setup' && <SystemSetup d={data} onResults={reload} />}
        {tab === 'Summary' && <Summary d={data} />}
        {tab === 'RAG Evaluation' && <RagTab r={data.rag_eval} s={data.rag_settings} />}
        {tab === 'E1 Accuracy' && <Accuracy d={data} />}
        {tab === 'Experiments' && <Experiments d={data} />}
        {tab === 'E2 Grounding' && <Grounding d={data} />}
        {tab === 'E3 Users' && <Users d={data} />}
        {tab === 'Cost & Performance' && <Cost d={data} />}
        {tab === 'Qwen on Colab' && <QwenColab />}
      </div>
    </section>
  )
}
