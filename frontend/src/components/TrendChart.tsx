/**
 * One-series line chart of scores (0–100%) with gaps for days without answers.
 * Hover a point for its value; the hidden table gives screen readers the same numbers.
 */
export default function TrendChart({ points, label }: { points: { label: string; value: number | null }[]; label: string }) {
  const W = 320
  const H = 150
  const L = 34
  const R = 16
  const TOP = 16
  const B = 24
  const x = (i: number) => L + (i * (W - L - R)) / Math.max(1, points.length - 1)
  const y = (v: number) => TOP + (1 - v / 100) * (H - TOP - B)

  const segments: string[] = []
  let d = ''
  points.forEach((p, i) => {
    if (p.value === null) {
      if (d) segments.push(d)
      d = ''
    } else d += `${d ? 'L' : 'M'}${x(i).toFixed(1)} ${y(p.value).toFixed(1)}`
  })
  if (d) segments.push(d)
  const last = points.map((p) => p.value !== null).lastIndexOf(true)
  const lastY = last >= 0 ? y(points[last].value!) : 0

  return (
    <figure className="m-0" dir="ltr">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-hidden="true">
        {[0, 50, 100].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeWidth={1} />
            <text x={L - 6} y={y(v) + 3.5} textAnchor="end" fontSize="10" fill="var(--ink-3)">
              {v}%
            </text>
          </g>
        ))}
        {points.map((p, i) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor="middle" fontSize="10" fill="var(--ink-3)">
            {p.label}
          </text>
        ))}
        {segments.map((seg, i) => (
          <path key={i} d={seg} fill="none" stroke="var(--primary)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
        ))}
        {points.map((p, i) =>
          p.value === null ? null : (
            <g key={i}>
              <circle cx={x(i)} cy={y(p.value)} r={4.5} fill="var(--primary)" stroke="var(--surface)" strokeWidth={2} />
              <circle cx={x(i)} cy={y(p.value)} r={12} fill="transparent" className="cursor-default">
                <title>{`${p.label}: ${Math.round(p.value)}%`}</title>
              </circle>
            </g>
          ),
        )}
        {last >= 0 && (
          <g transform={`translate(${Math.min(x(last), W - R - 18)} ${lastY - 24 < 0 ? lastY + 10 : lastY - 24})`}>
            <rect x={-18} width={36} height={16} rx={8} fill="var(--primary)" />
            <text y={11.5} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--on-primary)">
              {Math.round(points[last].value!)}%
            </text>
          </g>
        )}
      </svg>
      <table className="sr-only">
        <caption>{label}</caption>
        <tbody>
          {points.map((p, i) => (
            <tr key={i}>
              <th scope="row">{p.label}</th>
              <td>{p.value === null ? '–' : `${Math.round(p.value)}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}
