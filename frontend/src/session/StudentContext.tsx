import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import type { Student } from '../api/types'

interface StudentState {
  student: Student | null
  signIn: (s: Student) => void
  signOut: () => void
}

const StudentContext = createContext<StudentState | null>(null)
const KEY = 'kafa.student'

function load(): Student | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Student) : null
  } catch {
    return null
  }
}

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<Student | null>(load)
  const signIn = useCallback((s: Student) => {
    localStorage.setItem(KEY, JSON.stringify(s))
    setStudent(s)
  }, [])
  const signOut = useCallback(() => {
    localStorage.removeItem(KEY)
    setStudent(null)
  }, [])
  return <StudentContext.Provider value={{ student, signIn, signOut }}>{children}</StudentContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useStudent(): StudentState {
  const ctx = useContext(StudentContext)
  if (!ctx) throw new Error('useStudent must be used inside <StudentProvider>')
  return ctx
}

/** Route guard: send to /login when no student is signed in. */
export function RequireStudent({ children }: { children: ReactNode }) {
  const { student } = useStudent()
  const loc = useLocation()
  if (!student) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  return <>{children}</>
}
