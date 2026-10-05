// Pupil ranks from total XP (10 XP per star + 2 for trying, see backend memory/db.py).
// Early ranks come quickly so a new pupil levels up in the first session.

export interface RankDef {
  /** XP needed to reach this rank. */
  min: number
  emoji: string
  rumi: string
  jawi: string
}

export const RANKS: readonly RankDef[] = [
  { min: 0, emoji: '🌱', rumi: 'Pelajar Baharu', jawi: 'ڤلاجر بهارو' },
  { min: 50, emoji: '📚', rumi: 'Pelajar Rajin', jawi: 'ڤلاجر راجين' },
  { min: 150, emoji: '⭐', rumi: 'Bintang Kecil', jawi: 'بينتڠ كچيل' },
  { min: 300, emoji: '🌟', rumi: 'Bintang KAFA', jawi: 'بينتڠ كافا' },
  { min: 500, emoji: '🎓', rumi: 'Pakar Muda', jawi: 'ڤاكر مودا' },
  { min: 800, emoji: '🏆', rumi: 'Juara UPKK', jawi: 'جوارا UPKK' },
]

export interface RankInfo extends RankDef {
  /** 1-based position in RANKS. */
  number: number
  next: RankDef | null
  /** XP earned since reaching this rank. */
  into: number
  /** XP between this rank and the next (0 at the top rank). */
  span: number
  /** XP still needed for the next rank (0 at the top rank). */
  toNext: number
  /** Progress towards the next rank, 0..1 (1 at the top rank). */
  fraction: number
}

export function rankFor(xp: number): RankInfo {
  const value = Math.max(0, Math.floor(Number.isFinite(xp) ? xp : 0))
  let i = 0
  while (i + 1 < RANKS.length && value >= RANKS[i + 1].min) i++
  const rank = RANKS[i]
  const next = RANKS[i + 1] ?? null
  const into = value - rank.min
  const span = next ? next.min - rank.min : 0
  return {
    ...rank,
    number: i + 1,
    next,
    into,
    span,
    toNext: next ? next.min - value : 0,
    fraction: next ? into / span : 1,
  }
}
