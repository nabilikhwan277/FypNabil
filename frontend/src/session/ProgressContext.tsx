import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { Progress } from '../api/types'
import { useStudent } from './StudentContext'

interface ProgressState {
  /** Latest XP / streak / badges for the signed-in pupil (null until loaded). */
  progress: Progress | null
  /** Fetch progress again (e.g. after an answer). Resolves to the new value, or null on error. */
  refresh: () => Promise<Progress | null>
}

const ProgressContext = createContext<ProgressState | null>(null)

/** Shares the pupil's progress so the header chips, home page and practice stay in sync. */
export function ProgressProvider({ children }: { children: ReactNode }) {
  const { student } = useStudent()
  const sid = student?.id ?? null
  const [data, setData] = useState<Progress | null>(null)

  const refresh = useCallback(async () => {
    if (sid === null) return null
    try {
      const p = await api.progress(sid)
      setData(p)
      return p
    } catch {
      return null
    }
  }, [sid])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // Never show another pupil's numbers after switching accounts.
  const progress = data && data.student.id === sid ? data : null
  const value = useMemo(() => ({ progress, refresh }), [progress, refresh])
  return <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProgress(): ProgressState {
  const ctx = useContext(ProgressContext)
  if (!ctx) throw new Error('useProgress must be used inside <ProgressProvider>')
  return ctx
}
