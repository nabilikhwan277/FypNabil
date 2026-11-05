import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { ADMIN_EXPIRED, loadAdmin, saveAdmin } from '../api/adminToken'
import type { AdminSession } from '../api/types'

interface AdminState {
  session: AdminSession | null
  signIn: (s: AdminSession) => void
  signOut: () => void
}

const AdminContext = createContext<AdminState | null>(null)

/** The admin sign-in (separate from the pupil's). An expired token signs out automatically. */
export function AdminProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AdminSession | null>(loadAdmin)
  const signIn = useCallback((s: AdminSession) => {
    saveAdmin(s)
    setSession(s)
  }, [])
  const signOut = useCallback(() => {
    saveAdmin(null)
    setSession(null)
  }, [])
  useEffect(() => {
    window.addEventListener(ADMIN_EXPIRED, signOut)
    return () => window.removeEventListener(ADMIN_EXPIRED, signOut)
  }, [signOut])
  return <AdminContext.Provider value={{ session, signIn, signOut }}>{children}</AdminContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAdmin(): AdminState {
  const ctx = useContext(AdminContext)
  if (!ctx) throw new Error('useAdmin must be used inside <AdminProvider>')
  return ctx
}

/** Route guard: send to the Admin tab of the sign-in page when the admin is not signed in. */
export function RequireAdmin({ children }: { children: ReactNode }) {
  const { session } = useAdmin()
  const loc = useLocation()
  if (!session) return <Navigate to="/login" replace state={{ from: loc.pathname, role: 'admin' }} />
  return <>{children}</>
}
