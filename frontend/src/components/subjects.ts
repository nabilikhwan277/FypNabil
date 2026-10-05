import type { SubjectId } from '../api/types'
import type { StringKey } from '../i18n/strings'

// Visual identity per subject. Colours always come with an emoji and a label,
// never carrying meaning alone.
// Contrast rule: on `hero` / `solid` only large bold white text (>= 20px bold,
// the 600-level colours give >= 3:1); small text goes in a white chip.
export interface SubjectStyle {
  emoji: string
  desc: StringKey
  /** Bright gradient for banners. */
  hero: string
  /** Solid fill for path nodes and ribbons. */
  solid: string
  /** Darker bottom edge for the chunky 3D look. */
  edge: string
  /** Pale background. */
  soft: string
  ring: string
  /** Dark text colour for white / pale backgrounds. */
  text: string
  /** Progress bar fill. */
  bar: string
  /** SVG ring colours. */
  hex: string
  track: string
}

export const SUBJECT_STYLE: Record<SubjectId, SubjectStyle> = {
  fiqh: {
    emoji: '🕌',
    desc: 'ibadahDesc',
    hero: 'bg-linear-to-br from-emerald-600 to-teal-700',
    solid: 'bg-emerald-600',
    edge: 'border-emerald-800',
    soft: 'bg-emerald-50',
    ring: 'ring-emerald-300',
    text: 'text-emerald-800',
    bar: 'bg-emerald-500',
    hex: '#10b981',
    track: '#d1fae5',
  },
  jawi: {
    emoji: '✍️',
    desc: 'jawiDesc',
    hero: 'bg-linear-to-br from-violet-600 to-purple-700',
    solid: 'bg-violet-600',
    edge: 'border-violet-800',
    soft: 'bg-violet-50',
    ring: 'ring-violet-300',
    text: 'text-violet-800',
    bar: 'bg-violet-500',
    hex: '#8b5cf6',
    track: '#ede9fe',
  },
  tajwid: {
    emoji: '📖',
    desc: 'tajwidDesc',
    hero: 'bg-linear-to-br from-orange-600 to-amber-700',
    solid: 'bg-orange-600',
    edge: 'border-orange-800',
    soft: 'bg-orange-50',
    ring: 'ring-orange-300',
    text: 'text-orange-800',
    bar: 'bg-orange-500',
    hex: '#f97316',
    track: '#ffedd5',
  },
}
