import { useEffect, useState } from 'react'
import { api } from '../api/client'

let cached: boolean | null = null

/** True when the backend runs in researcher mode (KAFA_RESEARCHER_MODE): shows the 🛡️ Admin link in the sidebar. */
export function useResearcherMode(): boolean {
  const [on, setOn] = useState<boolean>(cached ?? false)
  useEffect(() => {
    if (cached !== null) return
    let alive = true
    api
      .health()
      .then((h) => {
        cached = Boolean(h.researcher_mode)
        if (alive) setOn(cached)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])
  return on
}
