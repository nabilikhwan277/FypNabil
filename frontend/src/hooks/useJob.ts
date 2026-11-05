import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Job } from '../api/types'

/**
 * Follows the latest background job of one kind (an evaluation run, reading a book): picks up a job that
 * is already running when the page opens, polls it every 1.5 s and calls onDone once when it finishes.
 */
export function useJob(kind: Job['kind'], onDone?: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null)
  const done = useRef(onDone)
  useEffect(() => {
    done.current = onDone
  })

  useEffect(() => {
    let alive = true
    api
      .latestJob(kind)
      .then((j) => alive && j?.status === 'running' && setJob(j))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [kind])

  const running = job?.status === 'running'
  const id = job?.id
  useEffect(() => {
    if (!running || id === undefined) return
    const timer = setInterval(() => {
      api
        .job(id)
        .then((j) => {
          setJob(j)
          if (j.status !== 'running') done.current?.(j)
        })
        .catch(() => {})
    }, 1500)
    return () => clearInterval(timer)
  }, [running, id])

  return { job, setJob, running }
}
