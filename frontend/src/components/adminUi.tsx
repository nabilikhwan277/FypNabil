import { CircleCheck, CircleX, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Job } from '../api/types'

// Building blocks of the admin pages (English): a titled card, a table and job progress.

export function Section({ title, children, note }: { title: string; children: ReactNode; note?: ReactNode }) {
  return (
    <section className="card">
      <h2 className="text-lg font-extrabold text-ink">{title}</h2>
      {note && <p className="mt-1 text-sm text-ink-3">{note}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

/** `wrap`: cells hold sentences (a text table), so they wrap instead of staying on one line. */
export function Table({ head, rows, wrap = false }: { head: string[]; rows: ReactNode[][]; wrap?: boolean }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {head.map((h) => (
              <th
                key={h}
                className={`bg-surface-2 px-3 py-2.5 text-start text-xs font-bold tracking-wide text-ink-3 uppercase ${wrap ? '' : 'whitespace-nowrap'}`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-line transition hover:bg-surface-2/60">
              {r.map((c, j) => (
                <td key={j} className={`px-3 py-2.5 align-top text-ink-2 ${j && !wrap ? 'tabular-nums whitespace-nowrap' : ''}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Progress of a background job (an evaluation run, reading a book). */
export function JobProgress({ job }: { job: Job }) {
  const share = job.total ? job.done / job.total : 0
  const Icon = job.status === 'running' ? LoaderCircle : job.status === 'done' ? CircleCheck : CircleX
  return (
    <div className="flex flex-col gap-1.5" role="status" aria-live="polite">
      <div className="flex justify-between gap-3 text-sm font-semibold text-ink-2">
        <span className="flex items-center gap-2">
          <Icon
            aria-hidden="true"
            className={`h-4.5 w-4.5 shrink-0 ${job.status === 'running' ? 'animate-spin text-primary-ink' : job.status === 'done' ? 'text-primary' : 'text-danger'}`}
          />
          {job.status === 'running' ? job.title : job.status === 'done' ? `${job.title}: finished` : `${job.title}: failed`}
        </span>
        {job.total > 0 && (
          <span className="tabular-nums">
            {job.done} / {job.total}
          </span>
        )}
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-surface-3">
        <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${Math.round(share * 100)}%` }} />
      </div>
      {job.message && <p className="text-xs text-ink-3">{job.message}</p>}
      {job.error && <p className="text-sm font-semibold text-danger-ink">{job.error}</p>}
    </div>
  )
}
