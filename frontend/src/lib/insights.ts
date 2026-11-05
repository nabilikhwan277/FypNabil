import type { Progress, Subject, Topic } from '../api/types'

/** Mastery that counts a topic as done: the same 70% bar that unlocks the next Tahap. */
export const MASTERED = 0.7

export type TopicState = 'new' | 'learning' | 'mastered'

export function topicState(t: { attempts: number; mastery: number }): TopicState {
  if (!t.attempts) return 'new'
  return t.mastery >= MASTERED ? 'mastered' : 'learning'
}

export interface SubjectTopic extends Topic {
  subject_rumi: string
  subject_jawi: string
}

/** Every practice topic (with questions) in subject and textbook order. */
export function practiceTopics(subjects: Subject[]): SubjectTopic[] {
  return subjects.flatMap((s) =>
    s.babs.flatMap((b) => b.topics.filter((t) => t.has_questions).map((t) => ({ ...t, subject_rumi: s.name_rumi, subject_jawi: s.name_jawi }))),
  )
}

/** Tried topics still below the mastery bar, weakest first. */
export function weakTopics<T extends { attempts: number; mastery: number }>(topics: T[], n = 3): T[] {
  return topics
    .filter((t) => topicState(t) === 'learning')
    .sort((a, b) => a.mastery - b.mastery)
    .slice(0, n)
}

/** What to study next: the weakest tried topics first, then new topics in textbook order. */
export function recommendations<T extends { id: string; attempts: number; mastery: number }>(topics: T[], n: number, skip?: string): T[] {
  const pool = topics.filter((t) => t.id !== skip)
  return [...weakTopics(pool, n), ...pool.filter((t) => !t.attempts)].slice(0, n)
}

const TIME = new Intl.DateTimeFormat('ms-MY', { hour: 'numeric', minute: '2-digit' })
const DATE = new Intl.DateTimeFormat('ms-MY', { day: 'numeric', month: 'short' })
export const WEEKDAY = new Intl.DateTimeFormat('ms-MY', { weekday: 'short' })

/** "Hari ini, 9:24 PG", "Semalam, 7:40 PTG" or "28 Okt, 3:18 PTG" (dates stay in Rumi in both scripts). */
export function whenLabel(iso: string, words: { today: string; yesterday: string }, now = new Date()): string {
  const d = new Date(iso)
  const days = Math.round((new Date(now.toDateString()).getTime() - new Date(d.toDateString()).getTime()) / 86_400_000)
  return `${days === 0 ? words.today : days === 1 ? words.yesterday : DATE.format(d)}, ${TIME.format(d)}`
}

/** Average score per day for the 7 days ending today (null when there was no answer that day). */
export function lastSevenDays(recent: Progress['recent'], now = new Date()): { day: Date; value: number | null }[] {
  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6 + i)
    const scores = recent.filter((r) => new Date(r.created_at).toDateString() === day.toDateString()).map((r) => r.percent)
    return { day, value: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null }
  })
}
