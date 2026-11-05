import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

interface ChatState {
  open: boolean
  setOpen: (open: boolean) => void
  toggle: () => void
}

const ChatContext = createContext<ChatState | null>(null)

/** Open/closed state of the "Tanya Bulan" panel, so the sidebar, tabs and pages can open it. */
export function ChatProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const toggle = useCallback(() => setOpen((v) => !v), [])
  const value = useMemo(() => ({ open, setOpen, toggle }), [open, toggle])
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChat(): ChatState {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChat must be used inside <ChatProvider>')
  return ctx
}
