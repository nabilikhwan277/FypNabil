import type { SubjectId } from '../api/types'
import type { StringKey } from '../i18n/strings'

// Visual identity per subject. Colours always come with an emoji and a label,
// never carrying meaning alone. All colours are theme tokens (index.css), so
// they work in light and dark mode.
// Contrast rule: on `hero` only large bold white text (>= 20px bold); small
// text goes in a chip.
export interface SubjectStyle {
  emoji: string
  desc: StringKey
  /** Gradient for banners (same in both themes, white text). */
  hero: string
  /** Solid fill (number badges, ribbons). */
  solid: string
  /** Pale tinted background. */
  soft: string
  /** Text colour on surface / soft backgrounds. */
  text: string
  /** Border colour. */
  border: string
  /** Progress bar fill. */
  bar: string
  /** CSS colour for SVG rings. */
  hex: string
}

export const SUBJECT_STYLE: Record<SubjectId, SubjectStyle> = {
  fiqh: {
    emoji: '🕌',
    desc: 'ibadahDesc',
    hero: 'bg-linear-to-br from-emerald-600 to-teal-700',
    solid: 'bg-fiqh',
    soft: 'bg-fiqh-soft',
    text: 'text-fiqh-ink',
    border: 'border-fiqh',
    bar: 'bg-fiqh',
    hex: 'var(--fiqh)',
  },
  jawi: {
    emoji: '✍️',
    desc: 'jawiDesc',
    hero: 'bg-linear-to-br from-amber-600 to-amber-800',
    solid: 'bg-jawi',
    soft: 'bg-jawi-soft',
    text: 'text-jawi-ink',
    border: 'border-jawi',
    bar: 'bg-jawi',
    hex: 'var(--jawi)',
  },
  tajwid: {
    emoji: '📖',
    desc: 'tajwidDesc',
    hero: 'bg-linear-to-br from-violet-600 to-purple-700',
    solid: 'bg-tajwid',
    soft: 'bg-tajwid-soft',
    text: 'text-tajwid-ink',
    border: 'border-tajwid',
    bar: 'bg-tajwid',
    hex: 'var(--tajwid)',
  },
}

export const SUBJECT_ORDER: SubjectId[] = ['fiqh', 'jawi', 'tajwid']
