import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Health } from '../api/types'
import T from './T'

/**
 * Small pill showing backend / AI readiness (dot + text, not colour alone).
 * Polls while the models warm up, and retries while the server is offline.
 */
export default function ApiStatus() {
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
    online: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    warming: 'bg-amber-50 text-amber-900 ring-amber-200',
    offline: 'bg-rose-50 text-rose-800 ring-rose-200',
  }[state]
  const dot = { online: 'bg-emerald-500', warming: 'animate-pulse bg-amber-500', offline: 'bg-rose-500' }[state]
  const key = ({ online: 'serverOnline', warming: 'serverWarming', offline: 'serverOffline' } as const)[state]
  return (
    <p role="status" className={`inline-flex min-h-10 items-center gap-2 rounded-full px-3 py-1 text-sm font-bold ring-2 ${style}`}>
      <span aria-hidden="true" className={`h-3 w-3 shrink-0 rounded-full ${dot}`} />
      {/* On small screens the "ready" text is for screen readers only; problems always show. */}
      <T k={key} className={state === 'online' ? 'sr-only sm:not-sr-only' : ''} />
    </p>
  )
}
