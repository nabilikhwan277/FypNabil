// The admin's sign-in token, kept in this browser only (12 hours, see backend/app/admin_auth.py).
import type { AdminSession } from './types'

const KEY = 'kafa.admin'
export const ADMIN_EXPIRED = 'kafa:admin-expired'

export function loadAdmin(): AdminSession | null {
  try {
    const raw = localStorage.getItem(KEY)
    const s = raw ? (JSON.parse(raw) as AdminSession) : null
    return s && s.expires * 1000 > Date.now() ? s : null
  } catch {
    return null
  }
}

export function saveAdmin(s: AdminSession | null): void {
  try {
    if (s) localStorage.setItem(KEY, JSON.stringify(s))
    else localStorage.removeItem(KEY)
  } catch {
    // storage blocked: the session lasts until the page is closed
  }
}
