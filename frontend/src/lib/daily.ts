import type { Progress } from '../api/types'

/** Questions a pupil is asked to answer each day (the home page "Misi hari ini"). */
export const DAILY_GOAL = 5

/**
 * Answers given today, in the pupil's local time. The progress API returns the
 * last 30 attempts, which is enough to tell whether today's goal of 5 is met.
 */
export function answeredToday(recent: Progress['recent'], now = new Date()): number {
  const today = now.toDateString()
  return recent.filter((r) => new Date(r.created_at).toDateString() === today).length
}
