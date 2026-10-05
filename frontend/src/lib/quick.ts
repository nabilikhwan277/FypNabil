// Helpers that turn some textbook question formats into tap-to-answer controls.
// They only use the question text (never the rubric), so they do not leak answers.
import type { Question } from '../api/types'
import type { Script } from '../i18n/strings'

export type QuickKind = 'truefalse' | 'blanks' | null

/** Word choices listed in brackets, e.g. "(sebelum, tertutup, lima)". Prefers the script on screen. */
export function blankOptions(q: Question, script: Script): string[] {
  const texts = script === 'jawi' ? [q.question_jawi, q.question_rumi] : [q.question_rumi, q.question_jawi]
  for (const text of texts) {
    const m = text?.match(/\(([^()]*[,،][^()]*)\)/)
    if (!m) continue
    const words = m[1]
      .split(/[,،]/)
      .map((w) => w.trim())
      .filter(Boolean)
    if (words.length > 1) return [...new Set(words)]
  }
  return []
}

export function quickKind(q: Question): QuickKind {
  if (/betul atau salah/i.test(q.question_rumi)) return 'truefalse'
  if (/tempat kosong/i.test(q.question_rumi) && blankOptions(q, 'rumi').length > 1) return 'blanks'
  return null
}

/** Number of blanks ("____") in the question. */
export function blankCount(q: Question): number {
  return Math.max(1, (q.question_rumi.match(/_{2,}/g) ?? []).length)
}

/** Blanks lettered (a), (b), (c)? */
export const blankLettered = (q: Question) => /\(a\)/i.test(q.question_rumi)

/** "(a) w1 (b) w2" when the blanks are lettered, otherwise "w1; w2". */
export function composeBlanks(q: Question, words: string[]): string {
  if (blankLettered(q)) return words.map((w, i) => `(${String.fromCharCode(97 + i)}) ${w}`).join(' ')
  return words.join('; ')
}

/** Jawi spelling task ("Tulis ... dalam tulisan Jawi", "Jawikan ..."). */
export const isJawiSpelling = (q: Question) => q.subject === 'jawi' && /tulisan jawi|jawikan/i.test(q.question_rumi)
