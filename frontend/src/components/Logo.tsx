import T from './T'

type Tone = 'color' | 'light'

/** App mark: an open book under a gold dome. `light` is for the deep green sidebar and hero cards. */
export default function Logo({ size = 48, tone = 'color' }: { size?: number; tone?: Tone }) {
  const page = tone === 'light' ? '#fbf3df' : 'var(--primary)'
  return (
    <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden="true" className="shrink-0">
      <path
        d="M12 25 C12 17 17 13.5 21 10.5 C22.6 9.3 23.6 7.6 24 5 C24.4 7.6 25.4 9.3 27 10.5 C31 13.5 36 17 36 25"
        fill="none"
        stroke="#f3b641"
        strokeWidth={3.2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="24" cy="3.4" r="1.7" fill="#f3b641" />
      <path d="M4 24.5 C10.5 23.2 17 24.4 23 28 L23 43.5 C17 40.2 10.5 39.2 4 40.5 Z" fill={page} />
      <path d="M44 24.5 C37.5 23.2 31 24.4 25 28 L25 43.5 C31 40.2 37.5 39.2 44 40.5 Z" fill={page} />
    </svg>
  )
}

/** Mark + "KafAI" wordmark + UPKK badge, with the tagline underneath. The name is a brand: Latin script in both modes. */
export function Brand({ size = 40, tone = 'color', tagline = true }: { size?: number; tone?: Tone; tagline?: boolean }) {
  const light = tone === 'light'
  return (
    <span className="flex min-w-0 items-center gap-2.5">
      <Logo size={size} tone={tone} />
      <span className="min-w-0 leading-none">
        <span className="flex items-center gap-1.5">
          <span className={`text-[1.4rem] font-extrabold tracking-tight ${light ? 'text-white' : 'text-ink'}`}>
            Kaf<span className={light ? 'text-gold' : 'text-gold-ink'}>AI</span>
          </span>
          <span
            className={`rounded-md px-1.5 py-0.5 text-[0.62rem] font-extrabold tracking-wider ${
              light ? 'bg-gold text-on-gold' : 'bg-primary-soft text-primary-ink'
            }`}
          >
            UPKK
          </span>
        </span>
        {tagline && (
          <T k="brandTagline" className={`mt-1 block text-[0.7rem] leading-snug font-medium ${light ? 'text-on-brand-2' : 'text-ink-3'}`} />
        )}
      </span>
    </span>
  )
}
