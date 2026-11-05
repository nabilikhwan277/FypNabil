import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../../api/client'
import type { AdminConfig, EvalEstimate, EvalRun, EvalSummary, LiveConfig } from '../../api/types'
import { JobProgress, Section, Table } from '../../components/adminUi'
import { num, pct, usd } from '../../components/format'
import ConfirmDialog from '../../components/ConfirmDialog'
import { ErrorBox, Spinner } from '../../components/ui'
import { useAsync } from '../../hooks/useAsync'
import { useJob } from '../../hooks/useJob'

// Admin → Evaluation → System setup: pick the marking system (System, LLM, RAG type, ReAct type, memory),
// see its evaluation results, run an evaluation of it, and make it the one pupils get.

interface Choice {
  system: string
  model: string
  rag: string
  react: string
  memory: boolean
}

const SYSTEM_SHORT: Record<string, string> = {
  b2: 'B2 Rules + bge-m3',
  b1: 'B1 Zero-shot',
  b3: 'B3 RAG + rubric',
  b4: 'B4 RAG + verifier',
  proposed: 'Proposed',
}

function configName(c: Choice): string {
  if (c.system === 'b2') return 'b2'
  if (c.system === 'b1') return `b1:${c.model}`
  if (c.system === 'b3' || c.system === 'b4') return `${c.system}:${c.model}:${c.rag}`
  return `proposed:${c.model}:${c.rag}:${c.react}:${c.memory ? 'on' : 'off'}`
}

function fromLive(l: LiveConfig): Choice {
  return { system: l.system, model: l.model || 'luna', rag: l.rag || 'R3', react: l.react || 'A2', memory: l.memory ?? true }
}

function runLabel(r: Pick<EvalRun, 'system' | 'model_label' | 'rag' | 'react' | 'memory'>): string {
  if (r.system === 'b2') return SYSTEM_SHORT.b2
  const parts = [SYSTEM_SHORT[r.system] ?? r.system, r.model_label]
  if (r.rag) parts.push(r.rag)
  if (r.react) parts.push(r.react)
  if (r.system === 'proposed') parts.push(r.memory ? 'memory on' : 'memory off')
  return parts.join(' · ')
}

const dataLabel = (r: EvalRun) => (r.data === 'silver' ? 'Silver (AI-written)' : r.labels === 'teacher' ? 'Teacher (final)' : r.labels.replace('teacher:', 'Teacher · '))

/** Newest run per (config, data set): reruns from the admin page replace older rows. */
function latestRuns(runs: EvalRun[]): EvalRun[] {
  const best = new Map<string, EvalRun>()
  for (const r of runs) {
    if (!r.complete || r.repeats > 1) continue
    const key = `${r.config}|${r.data}|${r.labels}`
    const old = best.get(key)
    if (!old || r.date > old.date) best.set(key, r)
  }
  return [...best.values()]
}

function Choices({
  legend,
  value,
  options,
  onChange,
  disabled = false,
  note,
}: {
  legend: string
  value: string
  options: { key: string; label: string; ok?: boolean; reason?: string; where?: string }[]
  onChange: (v: string) => void
  disabled?: boolean
  note?: ReactNode
}) {
  return (
    <fieldset disabled={disabled} className={`flex flex-col gap-2 ${disabled ? 'opacity-50' : ''}`}>
      <legend className="eyebrow mb-2">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o.key}
            type="button"
            aria-pressed={value === o.key}
            onClick={() => onChange(o.key)}
            title={o.ok === false ? o.reason : o.where ? `Runs on ${o.where}` : undefined}
            className={`min-h-11 cursor-pointer rounded-xl border-2 px-3 text-start text-sm font-black transition disabled:cursor-not-allowed ${
              value === o.key ? 'border-primary bg-primary-soft text-primary-ink' : 'border-line bg-surface text-ink-2 hover:border-line-strong'
            }`}
          >
            {o.label}
            {o.ok === false && <span className="ms-1.5 text-xs font-bold text-danger-ink">· not available</span>}
          </button>
        ))}
      </div>
      {note && <p className="text-xs font-bold text-ink-3">{note}</p>}
    </fieldset>
  )
}

export default function SystemSetup({ d, onResults }: { d: EvalSummary; onResults: () => void }) {
  const cfg = useAsync(() => api.adminConfig(), [])
  if (cfg.loading && !cfg.data) return <Spinner />
  if (cfg.error || !cfg.data) return <ErrorBox message={cfg.error ?? ''} onRetry={cfg.reload} />
  return <Setup d={d} c={cfg.data} onResults={onResults} reloadConfig={cfg.reload} />
}

function Setup({ d, c, onResults, reloadConfig }: { d: EvalSummary; c: AdminConfig; onResults: () => void; reloadConfig: () => void }) {
  const [choice, setChoice] = useState<Choice>(() => fromLive(c.live))
  // default: the answer set most results use, so a new run can be compared with them
  const [dataset, setDataset] = useState(() => {
    const count = (x: AdminConfig['datasets'][number]) =>
      d.runs.filter((r) => r.data === x.data && (x.data === 'silver' || r.labels === (x.labels === 'final' ? 'teacher' : `teacher:${x.labels}`))).length
    const best = c.datasets.reduce((bi, x, i) => (count(x) > count(c.datasets[bi]) ? i : bi), 0)
    return best
  })
  const [estimate, setEstimate] = useState<EvalEstimate | null>(null)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [confirmLive, setConfirmLive] = useState(false)
  const [busy, setBusy] = useState(false)
  const { job, setJob, running } = useJob('evaluation', (j) => {
    if (j.status === 'done') onResults()
  })

  const name = configName(choice)
  const uses = { llm: choice.system !== 'b2', rag: ['b3', 'b4', 'proposed'].includes(choice.system), react: choice.system === 'proposed' }
  const model = c.options.models.find((m) => m.key === choice.model)
  const available = !uses.llm || Boolean(model?.ok)
  const ds = c.datasets[dataset]
  const runs = useMemo(() => latestRuns(d.runs), [d.runs])
  const mine = runs.filter((r) => r.config === name).sort((a, b) => (a.data === b.data ? 0 : a.data === 'teacher' ? -1 : 1))
  const ragEval = uses.rag ? d.rag_eval?.rags.find((r) => r.rag === choice.rag) : undefined
  const ranked = [...runs]
    .filter((r) => r.data === (runs.some((x) => x.data === 'teacher') ? 'teacher' : 'silver'))
    .sort((a, b) => (b.overall.qwk_band ?? -1) - (a.overall.qwk_band ?? -1))

  useEffect(() => {
    if (!ds) return
    let alive = true
    setEstimate(null)
    api
      .evalEstimate(name, ds.data, ds.labels)
      .then((e) => alive && setEstimate(e))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [name, ds])

  const set = (patch: Partial<Choice>) => {
    setMessage(null)
    setChoice((x) => ({ ...x, ...patch }))
  }

  const runEvaluation = async () => {
    if (!ds) return
    setMessage(null)
    try {
      setJob(await api.startEvaluation(name, ds.data, ds.labels))
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message })
    }
  }

  const applyLive = async () => {
    setBusy(true)
    try {
      const live = await api.setLiveConfig(name)
      setMessage({ ok: true, text: `Pupils are now marked by: ${live.config}` })
      reloadConfig()
    } catch (e) {
      setMessage({ ok: false, text: (e as Error).message })
    } finally {
      setBusy(false)
      setConfirmLive(false)
    }
  }

  const isLive = name === c.live.config
  return (
    <div className="flex flex-col gap-5">
      <Section
        title="Marking system pupils get now"
        note={c.set_at ? `Chosen on this page on ${c.set_at.slice(0, 16).replace('T', ' ')} UTC` : 'From KAFA_SCORER in .env (not changed on this page yet)'}
      >
        <div className="flex flex-wrap gap-2">
          <span className="chip border-primary/30 bg-primary-soft text-primary-ink">{c.live.system_label}</span>
          {c.live.model_label && <span className="chip">LLM: {c.live.model_label}</span>}
          {c.live.rag_label && <span className="chip">RAG: {c.live.rag_label}</span>}
          {c.live.react_label && <span className="chip">ReAct: {c.live.react_label}</span>}
          {c.live.memory !== null && <span className="chip">Memory {c.live.memory ? 'on' : 'off'}</span>}
        </div>
        <p className="mt-3 text-sm font-bold text-ink-3">
          If the chosen model does not answer (no internet, budget used up, Colab off), the answer is marked by B2 so pupils are never
          blocked.
        </p>
      </Section>

      <Section title="Choose a configuration" note={<>Configuration name: <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-ink">{name}</code></>}>
        <div className="flex flex-col gap-5">
          <Choices legend="System" value={choice.system} options={c.options.systems} onChange={(v) => set({ system: v })} />
          <Choices
            legend="LLM (language model)"
            value={choice.model}
            options={c.options.models}
            onChange={(v) => set({ model: v })}
            disabled={!uses.llm}
            note={!uses.llm ? 'B2 marks with rules and bge-m3 similarity on this laptop: no language model.' : model && !model.ok ? model.reason : model?.where && `Runs on ${model.where}.`}
          />
          <Choices
            legend="RAG type"
            value={choice.rag}
            options={c.options.rags}
            onChange={(v) => set({ rag: v })}
            disabled={!uses.rag}
            note={!uses.rag ? 'B1 and B2 do not search the textbook.' : 'R3 was selected in the RAG evaluation (RAG Evaluation tab).'}
          />
          <Choices
            legend="ReAct type"
            value={choice.react}
            options={c.options.reacts}
            onChange={(v) => set({ react: v })}
            disabled={!uses.react}
            note={!uses.react ? 'Only the proposed system reasons in ReAct steps.' : undefined}
          />
          <Choices
            legend="Memory of the pupil's past mistakes"
            value={choice.memory ? 'on' : 'off'}
            options={[
              { key: 'on', label: 'On' },
              { key: 'off', label: 'Off' },
            ]}
            onChange={(v) => set({ memory: v === 'on' })}
            disabled={!uses.react}
          />
        </div>
      </Section>

      <Section title="Results of this configuration" note={runLabel({ system: choice.system, model_label: model?.label ?? '', rag: uses.rag ? choice.rag : '', react: uses.react ? choice.react : '', memory: choice.memory })}>
        {mine.length ? (
          <Table
            head={['Data set', 'Answers', 'QWK', 'Exact', 'Within 1 mark', 'MAE', 'Faithfulness (E2)', 'Success', 'API spend / 100', 'Time / answer', 'Date']}
            rows={mine.map((r) => [
              dataLabel(r),
              r.n,
              <b className="text-ink">{num(r.overall.qwk_band)}</b>,
              pct(r.overall.item_exact),
              pct(r.overall.within_1),
              num(r.overall.mae_marks, 2),
              num(r.grounding?.faithfulness ?? null),
              pct(r.success_rate),
              usd(r.cost_per_100, 3),
              `${(r.latency_ms.mean / 1000).toFixed(1)} s`,
              r.date.slice(0, 10),
            ])}
          />
        ) : (
          <p className="rounded-2xl bg-surface-2 p-4 font-bold text-ink-2">Not evaluated yet. Run an evaluation below to see how well it marks.</p>
        )}
        {ragEval && (
          <p className="mt-3 text-sm font-bold text-ink-2">
            {choice.rag} in the RAG evaluation: context recall {num(ragEval.summary.context_recall)}, faithfulness {num(ragEval.summary.faithfulness)},
            factual correctness {num(ragEval.summary.factual_correctness)}.
          </p>
        )}
        {c.syllabus_changed_at && (
          <p className="mt-2 text-sm font-bold text-ink-3">
            The syllabus changed on {c.syllabus_changed_at.slice(0, 10)} (Books & syllabus); results older than that used the old books.
          </p>
        )}

        <div className="mt-5 flex flex-col gap-4 rounded-2xl border border-line p-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex min-w-60 flex-1 flex-col gap-1.5">
              <span className="eyebrow">Evaluate on</span>
              <select value={dataset} onChange={(e) => setDataset(Number(e.target.value))} className="field">
                {c.datasets.map((x, i) => (
                  <option key={`${x.data}-${x.labels}`} value={i}>
                    {x.label} ({x.answers} answers)
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={runEvaluation} disabled={running || !available || !ds} className="btn-primary">
              ▶ Run evaluation{estimate ? ` (about ${usd(estimate.cost, 3)})` : ''}
            </button>
            <button type="button" onClick={() => setConfirmLive(true)} disabled={isLive || !available || busy} className="btn-secondary">
              {isLive ? '✅ Pupils get this now' : '🎒 Use for pupils'}
            </button>
          </div>
          {estimate && <p className="text-xs font-bold text-ink-3">{estimate.note}. API spending stops at the budget in .env.</p>}
          {!available && <p className="text-sm font-bold text-danger-ink">{model?.reason}</p>}
          {job && <JobProgress job={job} />}
          {message && (
            <p role="status" className={`rounded-2xl px-4 py-2.5 font-bold ${message.ok ? 'bg-primary-soft text-primary-ink' : 'bg-danger-soft text-danger-ink'}`}>
              {message.text}
            </p>
          )}
        </div>
      </Section>

      <Section title="All evaluated configurations" note={`Best first by QWK with the teachers' marks${ranked[0]?.data === 'silver' ? ' (silver set: no teacher runs yet)' : ''}. API spend is what the run cost; answers repeated from the cache are free, so a rerun shows $0. Select one to see it above.`}>
        <Table
          head={['Configuration', 'Data set', 'QWK', 'Exact', 'Within 1 mark', 'API spend / 100', '']}
          rows={ranked.map((r) => [
            <span className="font-bold text-ink">
              {runLabel(r)}
              {r.config === c.live.config && <span className="chip ms-2 border-primary/30 bg-primary-soft text-primary-ink">pupils get this</span>}
            </span>,
            dataLabel(r),
            <b className="text-ink">{num(r.overall.qwk_band)}</b>,
            pct(r.overall.item_exact),
            pct(r.overall.within_1),
            usd(r.cost_per_100, 3),
            <button
              type="button"
              className="btn-ghost text-sm"
              onClick={() => {
                set({ system: r.system, model: r.model || choice.model, rag: r.rag || choice.rag, react: r.react || choice.react, memory: r.memory })
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
            >
              Select
            </button>,
          ])}
        />
      </Section>

      <ConfirmDialog
        open={confirmLive}
        title="Use this marking system for pupils?"
        confirm="Yes, use it"
        busy={busy}
        onConfirm={applyLive}
        onClose={() => setConfirmLive(false)}
      >
        <p>
          From the next answer, pupils are marked by <b>{name}</b>.
        </p>
        {uses.llm && <p>Every answer then calls {model?.label} through the API, which costs money (see Cost & Performance).</p>}
        {!mine.length && <p className="text-danger-ink">This configuration has not been evaluated yet.</p>}
      </ConfirmDialog>
    </div>
  )
}
