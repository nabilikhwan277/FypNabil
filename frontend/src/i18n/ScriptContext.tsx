import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { STRINGS, type Script, type StringKey } from './strings'

interface ScriptState {
  script: Script
  toggle: () => void
  t: (key: StringKey) => string
}

const ScriptContext = createContext<ScriptState | null>(null)
const STORAGE_KEY = 'kafa.script'

export function ScriptProvider({ children }: { children: ReactNode }) {
  const [script, setScript] = useState<Script>(
    () => (localStorage.getItem(STORAGE_KEY) as Script | null) ?? 'rumi',
  )

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, script)
    // Screen readers and the browser need the right language and direction.
    document.documentElement.lang = script === 'jawi' ? 'ms-Arab' : 'ms'
    document.documentElement.dir = script === 'jawi' ? 'rtl' : 'ltr'
  }, [script])

  const toggle = useCallback(() => setScript((s) => (s === 'rumi' ? 'jawi' : 'rumi')), [])
  const t = useCallback((key: StringKey) => STRINGS[key][script], [script])

  return <ScriptContext.Provider value={{ script, toggle, t }}>{children}</ScriptContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useScript(): ScriptState {
  const ctx = useContext(ScriptContext)
  if (!ctx) throw new Error('useScript must be used inside <ScriptProvider>')
  return ctx
}
