import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useScript } from '../i18n/ScriptContext'
import { STRINGS } from '../i18n/strings'
import { useProgress } from '../session/ProgressContext'
import { useStudent } from '../session/StudentContext'
import ApiStatus from './ApiStatus'
import ChatBox from './ChatBox'
import Logo from './Logo'
import ScriptToggle from './ScriptToggle'
import SoundToggle from './SoundToggle'
import T from './T'

// Active tab: white on emerald-700 (5.5:1) because nav text is normal size.
const navCls = ({ isActive }: { isActive: boolean }) =>
  `inline-flex min-h-12 items-center gap-2 rounded-2xl border-2 border-b-4 px-4 py-2 font-black transition hover:-translate-y-0.5 ${
    isActive ? 'border-emerald-900 bg-emerald-700 text-white' : 'border-slate-200 bg-white text-ink hover:border-sky-300'
  }`

const tabCls = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-14 w-full cursor-pointer flex-col items-center justify-center gap-0.5 rounded-2xl px-2 py-1 text-xs font-black transition ${
    isActive ? 'bg-emerald-100 text-emerald-900 ring-2 ring-emerald-300' : 'text-slate-700 hover:bg-slate-100'
  }`

// Decorative twinkling stars in the background (static for reduced motion).
const SKY = [
  { top: '7%', left: '3%', size: 18, delay: '0s', color: 'text-amber-300' },
  { top: '20%', left: '94%', size: 14, delay: '1.1s', color: 'text-sky-400' },
  { top: '46%', left: '1.5%', size: 12, delay: '2s', color: 'text-violet-300' },
  { top: '64%', left: '96%', size: 20, delay: '0.6s', color: 'text-amber-300' },
  { top: '83%', left: '5%', size: 16, delay: '1.6s', color: 'text-sky-400' },
  { top: '11%', left: '72%', size: 10, delay: '2.4s', color: 'text-violet-300' },
  { top: '93%', left: '82%', size: 12, delay: '0.3s', color: 'text-amber-300' },
  { top: '35%', left: '90%', size: 10, delay: '1.9s', color: 'text-emerald-300' },
]

function SkyDecor() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {SKY.map((s, i) => (
        <span
          key={i}
          className={`absolute animate-twinkle ${s.color}`}
          style={{ top: s.top, left: s.left, fontSize: s.size, animationDelay: s.delay }}
        >
          ✦
        </span>
      ))}
    </div>
  )
}

/** XP and streak chips; the XP number pops when it changes. */
function StatChips() {
  const { progress } = useProgress()
  const { t } = useScript()
  if (!progress) return null
  return (
    <ul className="flex items-center gap-2">
      <li className="chip min-h-10 text-base">
        <span aria-hidden="true">💎</span>
        <span key={progress.xp} className="animate-pop tabular-nums">
          {progress.xp}
        </span>
        <span className="text-xs">XP</span>
      </li>
      <li className="chip min-h-10 text-base">
        <span aria-hidden="true">🔥</span>
        <span className="tabular-nums">{progress.streak_days}</span>
        <span className="sr-only">{t('streak')}</span>
      </li>
    </ul>
  )
}

export default function Layout() {
  const { student, signOut } = useStudent()
  const { t } = useScript()
  const nav = useNavigate()
  const { pathname } = useLocation()

  // Start each page at the top (BrowserRouter does not restore scroll).
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  const logout = () => {
    signOut()
    nav('/login')
  }

  return (
    <div className="relative min-h-screen">
      <SkyDecor />
      <div
        className={`relative z-10 mx-auto flex min-h-screen max-w-5xl flex-col gap-5 px-4 pt-4 sm:px-6 sm:pt-6 sm:pb-10 ${
          student ? 'pb-28' : 'pb-8'
        }`}
      >
        <a
          href="#main"
          className="sr-only rounded-xl bg-white px-4 py-2 font-bold shadow focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50"
        >
          <T k="skipToContent" />
        </a>

        <header className="flex flex-wrap items-center justify-between gap-3">
          <NavLink to="/" className="flex items-center gap-3 rounded-2xl pe-2">
            <Logo size={52} />
            {/* Brand name: English in both scripts. */}
            <span className="flex flex-col leading-tight" lang="en">
              <span className="text-lg font-black text-emerald-800 sm:text-2xl">{STRINGS.appLine1.rumi}</span>{' '}
              <span className="text-sm font-extrabold text-sky-800 sm:text-base">{STRINGS.appLine2.rumi}</span>
            </span>
          </NavLink>
          <div className="flex flex-wrap items-center gap-2">
            {student && <StatChips />}
            <ApiStatus />
            <SoundToggle />
            <ScriptToggle />
          </div>
        </header>

        {student && (
          <nav aria-label={t('mainMenu')} className="hidden flex-wrap items-center gap-2 sm:flex">
            <NavLink to="/" end className={navCls}>
              <span aria-hidden="true">🗺️</span>
              <T k="navMap" />
            </NavLink>
            <NavLink to="/kemajuan" className={navCls}>
              <span aria-hidden="true">🏆</span>
              <T k="navProgress" />
            </NavLink>
            <div className="ms-auto flex items-center gap-2 rounded-2xl bg-white py-1.5 ps-2 pe-1.5 shadow-sm ring-2 ring-white">
              <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-full bg-sky-100 text-2xl">
                {student.avatar}
              </span>
              <span className="font-black">{student.name}</span>
              <button
                type="button"
                onClick={logout}
                className="min-h-10 cursor-pointer rounded-xl px-3 text-sm font-bold text-slate-700 hover:bg-rose-50 hover:text-rose-800"
              >
                <T k="logout" />
              </button>
            </div>
          </nav>
        )}

        <main id="main" tabIndex={-1} className="flex-1 outline-none">
          <Outlet />
        </main>
      </div>

      {/* AI Chat Assistant — visible on every page when logged in */}
      {student && <ChatBox />}

      {student && (
        <nav
          aria-label={t('mainMenu')}
          className="fixed inset-x-0 bottom-0 z-30 border-t-2 border-sky-100 bg-white/95 px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] shadow-[0_-6px_20px_rgb(15_23_42/0.08)] backdrop-blur sm:hidden"
        >
          <ul className="mx-auto grid max-w-md grid-cols-3 gap-2">
            <li>
              <NavLink to="/" end className={tabCls}>
                <span aria-hidden="true" className="text-2xl">
                  🗺️
                </span>
                <T k="navMap" />
              </NavLink>
            </li>
            <li>
              <NavLink to="/kemajuan" className={tabCls}>
                <span aria-hidden="true" className="text-2xl">
                  🏆
                </span>
                <T k="navProgress" />
              </NavLink>
            </li>
            <li>
              <button type="button" onClick={logout} className={tabCls({ isActive: false })}>
                <span aria-hidden="true" className="text-2xl">
                  {student.avatar}
                </span>
                <T k="logout" />
              </button>
            </li>
          </ul>
        </nav>
      )}
    </div>
  )
}
