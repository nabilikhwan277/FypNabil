/** Decorative mosque skyline (domes, minarets, crescent). Colour comes from `currentColor`; set opacity on the parent. */
export default function MosqueScene({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 120" className={className} aria-hidden="true" fill="currentColor" preserveAspectRatio="xMidYMax meet">
      <g opacity="0.55">
        <path d="M60 96 C60 83 71 77 80 68 C89 77 100 83 100 96 Z" />
        <rect x="58" y="94" width="44" height="18" />
        <rect x="262" y="58" width="9" height="54" />
        <path d="M260 60 L266.5 46 L273 60 Z" />
      </g>
      <path d="M282 14 a11 11 0 1 0 8 19 a9 9 0 1 1 -8 -19 z" />
      <rect x="121" y="40" width="12" height="72" />
      <path d="M118 42 L127 24 L136 42 Z" />
      <rect x="117" y="56" width="20" height="4" rx="1" />
      <path d="M150 72 C150 50 174 42 190 24 C206 42 230 50 230 72 Z" />
      <rect x="188.8" y="12" width="2.4" height="13" />
      <path fillRule="evenodd" d="M152 70 H228 V112 H152 Z M178 112 V94 C178 88 182 84 190 82 C198 84 202 88 202 94 V112 Z" />
      <rect x="240" y="48" width="10" height="64" />
      <path d="M237 50 L245 34 L253 50 Z" />
      <path d="M0 120 V108 C50 100 100 104 160 110 C220 104 270 100 320 106 V120 Z" />
    </svg>
  )
}
