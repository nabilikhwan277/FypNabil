import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Health } from '../api/types'
import T from './T'

/**
 * Small pill showing backend / AI readiness (dot + text, not colour alone).
 * Polls while the models warm up, and retries while the server is offline.
 * `compact` shows only the dot when everything is fine (problems always show text).
 */
export default function ApiStatus({ compact = false }: { compact?: boolean }) {
  const [health, setHealth] = useState<Health | null | 'offline'>(null)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const poll = () =>
      api
        .health()
        .then((h) => {
          if (!alive) return
          setHealth(h)
          if (h.warm_up === 'loading') timer = setTimeout(poll, 3000)
        })
        .catch(() => {
          if (!alive) return
          setHealth('offline')
          timer = setTimeout(poll, 5000)
        })
    poll()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  if (health === null) return null
  const state = health === 'offline' ? 'offline' : health.warm_up === 'loading' ? 'warming' : 'online'
  const style = {
    online: 'bg-primary-soft text-primary-ink',
    warming: 'bg-accent-soft text-accent-ink',
    offline: 'bg-danger-soft text-danger-ink',
  }[state]
  const dot = { online: 'bg-primary', warming: 'animate-pulse bg-accent', offline: 'bg-danger' }[state]
  const key = ({ online: 'serverOnline', warming: 'serverWarming', offline: 'serverOffline' } as const)[state]
  return (
    <p role="status" className={`inline-flex min-h-9 items-center gap-2 rounded-full px-3 py-1 text-sm font-extrabold ${style}`}>
      <span aria-hidden="true" className={`h-2.5 w-2.5 shrink-0 rounded-full ${dot}`} />
      <T k={key} className={compact && state === 'online' ? 'sr-only' : ''} />
    </p>
  )
}
