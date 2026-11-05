import { Backpack, ChartColumn, Library, LogOut, ShieldCheck, type LucideIcon } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAdmin } from '../session/AdminContext'
import { Brand } from './Logo'
import MosqueScene from './MosqueScene'
import ThemeToggle from './ThemeToggle'

// The admin area (teachers / researcher): evaluation and system setup, books & syllabus.
// English, like the evaluation page; the pupil pages stay in Malay (Rumi / Jawi).

const NAV: { to: string; icon: LucideIcon; label: string }[] = [
  { to: '/admin/penilaian', icon: ChartColumn, label: 'Evaluation & system setup' },
  { to: '/admin/buku', icon: Library, label: 'Books & syllabus' },
]

const sideItem = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center gap-3 rounded-xl px-3 text-[0.95rem] transition ${
    isActive ? 'bg-nav-active font-bold text-on-nav-active shadow-sm' : 'font-semibold text-on-brand-2 hover:bg-white/10 hover:text-on-brand'
  }`

const tabItem = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-3 text-sm font-bold transition ${
    isActive ? 'bg-brand text-on-brand' : 'text-ink-2 hover:bg-surface-2'
  }`

export default function AdminLayout() {
  const { signOut } = useAdmin()
  const nav = useNavigate()
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  const logout = () => {
    signOut()
    nav('/login', { replace: true, state: { role: 'admin' } })
  }

  return (
    <div className="min-h-screen" dir="ltr" lang="en">
      <a
        href="#admin-main"
        className="sr-only rounded-xl border-2 border-primary bg-surface px-4 py-2 font-bold text-primary-ink shadow focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-[60]"
      >
        Skip to content
      </a>

      <aside className="on-brand scroll-thin fixed inset-y-0 start-0 z-30 hidden w-64 flex-col gap-6 overflow-y-auto bg-linear-to-b from-brand-2 to-brand p-4 md:flex">
        <NavLink to="/admin" className="rounded-xl px-1 pt-1">
          <Brand size={40} tone="light" tagline={false} />
        </NavLink>
        <p className="-mt-3 inline-flex w-fit items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-bold tracking-wide text-on-brand uppercase">
          <ShieldCheck aria-hidden="true" className="h-3.5 w-3.5 text-gold" /> Admin
        </p>
        <nav aria-label="Admin" className="flex flex-col gap-1">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={sideItem}>
              <n.icon aria-hidden="true" className="h-5 w-5 shrink-0" />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-3">
          <MosqueScene className="w-full text-white/[0.09]" />
          <NavLink to="/" className={sideItem({ isActive: false })} title="Open the pupils' app">
            <Backpack aria-hidden="true" className="h-5 w-5 shrink-0" /> Pupil app
          </NavLink>
          <div className="flex items-center gap-2 border-t border-brand-line pt-3">
            <button
              type="button"
              onClick={logout}
              className="flex min-h-11 flex-1 cursor-pointer items-center gap-3 rounded-xl px-3 font-semibold text-on-brand-2 transition hover:bg-white/10 hover:text-on-brand"
            >
              <LogOut aria-hidden="true" className="h-5 w-5" /> Sign out
            </button>
            <ThemeToggle variant="brand" />
          </div>
        </div>
      </aside>

      <div className="md:ps-64">
        {/* Phones and small tablets: brand bar + the two sections as tabs */}
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur-md md:hidden">
          <div className="flex items-center gap-2 px-4 py-2.5">
            <NavLink to="/admin" className="rounded-xl">
              <Brand size={32} tagline={false} />
            </NavLink>
            <span className="chip py-0.5 text-xs">Admin</span>
            <div className="ms-auto flex items-center gap-1">
              <ThemeToggle />
              <NavLink to="/" className="btn-ghost" title="Open the pupils' app">
                <Backpack aria-hidden="true" className="h-5 w-5" />
                <span className="sr-only">Pupil app</span>
              </NavLink>
              <button type="button" onClick={logout} className="btn-ghost" title="Sign out">
                <LogOut aria-hidden="true" className="h-5 w-5" />
                <span className="sr-only">Sign out</span>
              </button>
            </div>
          </div>
          <nav aria-label="Admin" className="flex gap-1 px-4 pb-2.5">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={tabItem}>
                <n.icon aria-hidden="true" className="h-4.5 w-4.5" />
                {n.label}
              </NavLink>
            ))}
          </nav>
        </header>

        <main id="admin-main" tabIndex={-1} className="mx-auto w-full max-w-6xl px-4 pt-6 pb-16 outline-none sm:px-6 md:pt-8 lg:px-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
