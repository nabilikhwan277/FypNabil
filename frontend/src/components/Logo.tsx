import { useId } from 'react'

/** App mark: a crescent moon and star on an emerald tile. */
export default function Logo({ size = 48 }: { size?: number }) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  return (
    <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden="true" className="shrink-0 drop-shadow">
      <defs>
        <linearGradient id={`bg-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#10b981" />
          <stop offset="100%" stopColor="#047857" />
        </linearGradient>
        <mask id={`cut-${id}`}>
          <rect width="48" height="48" fill="#fff" />
          <circle cx="30" cy="19" r="11" fill="#000" />
        </mask>
      </defs>
      <rect x="1" y="1" width="46" height="46" rx="14" fill={`url(#bg-${id})`} />
      <circle cx="22" cy="25" r="14" fill="#fef3c7" mask={`url(#cut-${id})`} />
      <polygon
        points="33,14 34.8,18.3 39.4,18.6 35.9,21.6 37,26 33,23.6 29,26 30.1,21.6 26.6,18.6 31.2,18.3"
        fill="#fbbf24"
      />
    </svg>
  )
}
