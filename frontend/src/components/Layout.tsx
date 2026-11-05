import { AnimatePresence, motion } from 'framer-motion'
import {
  ChartColumn,
  Flame,
  Gem,
  House,
  LogOut,
  Menu,
  MessageCircle,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { SubjectId } from '../api/types'
import { useChat } from '../chat/ChatContext'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { useResearcherMode } from '../hooks/useResearcherMode'
import { useScript } from '../i18n/ScriptContext'
import type { StringKey } from '../i18n/strings'
import { useProgress } from '../session/ProgressContext'
import { useStudent } from '../session/StudentContext'
import ApiStatus from './ApiStatus'
import Bi from './Bi'
import ChatBox from './ChatBox'
import Logo, { Brand } from './Logo'
import MosqueScene from './MosqueScene'
import ScriptToggle from './ScriptToggle'
import SoundToggle from './SoundToggle'
import SubjectIcon from './SubjectIcon'
import { SUBJECT_ORDER } from './subjects'
import T from './T'
import ThemeToggle from './ThemeToggle'

const RAIL_KEY = 'kafa.sidebar'

function readRail(): boolean {
  try {
    return localStorage.getItem(RAIL_KEY) === 'rail'
  } catch {
    return false
  }
}

/** Which subject the current page belongs to (subject, topic or practice page). */
function useCurrentSubject(): SubjectId | null {
  const { pathname } = useLocation()
  const { progress } = useProgress()
  const subject = pathname.match(/^\/subjek\/([^/]+)/)?.[1]
  if (subject) return subject as SubjectId
  const topicId = pathname.match(/^\/(?:topik|latihan)\/([^/]+)/)?.[1]
  if (!topicId || !progress) return null
  return progress.subjects.find((s) => s.topics.some((t) => t.id === topicId))?.id ?? null
}

const itemBase = 'group flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-xl px-3 text-[0.95rem] transition'
const itemIdle = 'font-semibold text-on-brand-2 hover:bg-white/10 hover:text-on-brand'
const itemActive = 'bg-nav-active font-bold text-on-nav-active shadow-sm'

function NavItem({
  to,
  end,
  icon,
  label,
  rail,
  active,
  onNavigate,
  extra,
}: {
  to: string
  end?: boolean
  icon: ReactNode
  label: StringKey | { rumi: string; jawi: string }
  rail: boolean
  /** Highlight even when the URL is a child page (e.g. a topic of this subject). */
  active?: boolean
  onNavigate?: () => void
  extra?: ReactNode
}) {
  const { t, script } = useScript()
  const text = typeof label === 'string' ? t(label) : script === 'jawi' ? label.jawi : label.rumi
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      title={rail ? text : undefined}
      className={({ isActive }) => `${itemBase} ${isActive || active ? itemActive : itemIdle} ${rail ? 'justify-center px-0' : ''}`}
    >
      <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center">
        {icon}
      </span>
      {rail ? (
        <span className="sr-only">{text}</span>
      ) : (
        <>
          {typeof label === 'string' ? (
            <T k={label} className="min-w-0 flex-1 truncate" />
          ) : (
            <Bi rumi={label.rumi} jawi={label.jawi} className="min-w-0 flex-1 truncate" />
          )}
          {extra}
        </>
      )}
    </NavLink>
  )
}

/** Everything inside the green sidebar; also used by the mobile drawer. */
function SidebarContent({ rail, onNavigate, onCollapse }: { rail: boolean; onNavigate?: () => void; onCollapse?: () => void }) {
  const { student, signOut } = useStudent()
  const { progress } = useProgress()
  const { toggle: toggleChat, open: chatOpen } = useChat()
  const { t } = useScript()
  const nav = useNavigate()
  const current = useCurrentSubject()
  const researcher = useResearcherMode()
  if (!student) return null

  const logout = () => {
    onNavigate?.()
    signOut()
    nav('/login')
  }
  const sep = rail ? <span aria-hidden="true" className="mx-auto my-2 h-px w-10 bg-brand-line" /> : null

  return (
    <div className="flex h-full flex-col gap-6">
      <NavLink to="/" onClick={onNavigate} className={`flex items-center rounded-xl ${rail ? 'justify-center' : 'px-1 pt-1'}`}>
        {rail ? <Logo size={40} tone="light" /> : <Brand size={40} tone="light" />}
        {rail && <span className="sr-only">KafAI UPKK</span>}
      </NavLink>

      <nav aria-label={t('mainMenu')} className="flex flex-col gap-1">
        <NavItem to="/" end icon={<House className="h-5 w-5" />} label="navHome" rail={rail} onNavigate={onNavigate} />
        <NavItem to="/kemajuan" icon={<ChartColumn className="h-5 w-5" />} label="navProgress" rail={rail} onNavigate={onNavigate} />

        {!rail && <T k="navSubjects" as="p" className="mt-5 mb-1 px-3 text-xs font-bold tracking-wider text-on-brand-2 uppercase" />}
        {sep}
        {SUBJECT_ORDER.map((id) => {
          const s = progress?.subjects.find((x) => x.id === id)
          const label = s ? { rumi: s.name_rumi, jawi: s.name_jawi } : { rumi: id, jawi: id }
          return (
            <NavItem
              key={id}
              to={`/subjek/${id}`}
              icon={<SubjectIcon id={id} size="sm" />}
              label={label}
              rail={rail}
              active={current === id}
              onNavigate={onNavigate}
              extra={s && <span className="text-xs font-bold tabular-nums opacity-80">{Math.round(s.mastery * 100)}%</span>}
            />
          )
        })}
        {sep}

        <button
          type="button"
          onClick={() => {
            onNavigate?.()
            toggleChat()
          }}
          aria-pressed={chatOpen}
          title={rail ? t('chatTitle') : undefined}
          className={`${itemBase} ${chatOpen ? itemActive : itemIdle} ${rail ? 'justify-center px-0' : 'mt-3'}`}
        >
          <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gold text-on-gold">
            <MessageCircle className="h-4.5 w-4.5" />
          </span>
          {rail ? <span className="sr-only">{t('chatTitle')}</span> : <T k="chatTitle" className="flex-1 text-start" />}
        </button>

        {researcher && (
          <NavItem to="/admin" icon={<ShieldCheck className="h-5 w-5" />} label="navAdmin" rail={rail} onNavigate={onNavigate} />
        )}
      </nav>

      <div className="mt-auto flex flex-col gap-3">
        {!rail && <MosqueScene className="w-full text-white/[0.09]" />}
        <div className={`flex items-center gap-2 ${rail ? 'flex-col' : ''}`}>
          <ScriptToggle compact variant="brand" />
          <ThemeToggle variant="brand" />
          <SoundToggle variant="brand" />
          <span className={rail ? '' : 'ms-auto'}>
            <ApiStatus compact />
          </span>
        </div>
        <div className={`flex items-center gap-1 border-t border-brand-line pt-3 ${rail ? 'flex-col' : ''}`}>
          <button
            type="button"
            onClick={logout}
            title={rail ? t('logout') : undefined}
            className={`${itemBase} ${itemIdle} ${rail ? 'justify-center px-0' : 'flex-1'}`}
          >
            <LogOut aria-hidden="true" className="h-5 w-5 shrink-0 rtl:-scale-x-100" />
            {rail ? <span className="sr-only">{t('logout')}</span> : <T k="logout" />}
          </button>
          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label={t(rail ? 'expandMenu' : 'collapseMenu')}
              title={t(rail ? 'expandMenu' : 'collapseMenu')}
              className="inline-flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-xl text-on-brand-2 transition hover:bg-white/10 hover:text-on-brand"
            >
              {rail ? (
                <PanelLeftOpen aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" />
              ) : (
                <PanelLeftClose aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/** Search the pupil's topics by title (Rumi or Jawi) and jump to the topic page. */
function TopicSearch() {
  const { progress } = useProgress()
  const { t } = useScript()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const topics = useMemo(
    () => progress?.subjects.flatMap((s) => s.topics.map((tp) => ({ ...tp, subject: s.id }))) ?? [],
    [progress],
  )
  const query = q.trim().toLowerCase()
  const hits = query
    ? topics.filter((tp) => tp.title_rumi.toLowerCase().includes(query) || tp.title_jawi.includes(q.trim())).slice(0, 6)
    : []
  const close = () => {
    setQ('')
    setOpen(false)
  }

  return (
    <div
      className="relative w-full max-w-md"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false)
      }}
    >
      <Search aria-hidden="true" className="pointer-events-none absolute start-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-ink-3" />
      <input
        type="search"
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && hits[0]) {
            close()
            nav(`/topik/${hits[0].id}`)
          }
          if (e.key === 'Escape') close()
        }}
        placeholder={t('searchTopics')}
        aria-label={t('searchLabel')}
        className="h-11 w-full rounded-full border border-line bg-surface ps-10 pe-4 text-sm text-ink shadow-sm outline-none transition placeholder:text-ink-3 focus:border-primary focus:ring-4 focus:ring-primary-soft"
      />
      {open && query && (
        <ul className="absolute inset-x-0 top-full z-40 mt-2 overflow-hidden rounded-2xl border border-line bg-surface p-1.5 shadow-lg">
          {hits.length ? (
            hits.map((tp) => (
              <li key={tp.id}>
                <Link to={`/topik/${tp.id}`} onClick={close} className="flex items-center gap-3 rounded-xl px-3 py-2 transition hover:bg-surface-2">
                  <SubjectIcon id={tp.subject} size="sm" />
                  <Bi rumi={tp.title_rumi} jawi={tp.title_jawi} className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" />
                  <span className="text-xs font-bold text-ink-3 tabular-nums">{Math.round(tp.mastery * 100)}%</span>
                </Link>
              </li>
            ))
          ) : (
            <li className="px-3 py-2 text-sm text-ink-3">
              <T k="searchNone" />
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

/** XP and streak chips (top bar). */
function StatChips({ compact = false }: { compact?: boolean }) {
  const { progress } = useProgress()
  const { t } = useScript()
  if (!progress) return null
  return (
    <>
      <span className="chip bg-surface" title={t('xp')}>
        <Gem aria-hidden="true" className="h-4 w-4 text-info-ink" />
        <span key={progress.xp} className="animate-pop tabular-nums">{progress.xp}</span> XP
      </span>
      {!compact && (
        <span className="chip bg-surface" title={t('streak')}>
          <Flame aria-hidden="true" className="h-4 w-4 text-accent" />
          <span className="tabular-nums">{progress.streak_days}</span> <T k="days" />
        </span>
      )}
    </>
  )
}

/** Slide-in menu for phones. Escape or the backdrop closes it; focus goes to the close button. */
function MobileDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t, script } = useScript()
  const closeBtn = useRef<HTMLButtonElement>(null)
  const from = script === 'jawi' ? '100%' : '-100%'

  useEffect(() => {
    if (!open) return
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const timer = setTimeout(() => closeBtn.current?.focus(), 50)
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => {
      clearTimeout(timer)
      document.body.style.overflow = overflow
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/40 md:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label={t('menu')}
            className="on-brand scroll-thin absolute inset-y-0 start-0 flex w-[min(86vw,300px)] flex-col overflow-y-auto bg-linear-to-b from-brand-2 to-brand p-4 shadow-lg"
            initial={{ x: from }}
            animate={{ x: 0 }}
            exit={{ x: from }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
          >
            <button
              ref={closeBtn}
              type="button"
              onClick={onClose}
              aria-label={t('closeMenu')}
              className="absolute end-3 top-3 inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-xl text-on-brand-2 hover:bg-white/10 hover:text-on-brand"
            >
              <X aria-hidden="true" className="h-5 w-5" />
            </button>
            <SidebarContent rail={false} onNavigate={onClose} />
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

const tabCls = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-14 w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl px-1 text-[0.7rem] font-bold transition ${
    isActive ? 'bg-primary-soft text-primary-ink' : 'text-ink-3 hover:bg-surface-2 hover:text-ink'
  }`

export default function Layout() {
  const { student } = useStudent()
  const { t } = useScript()
  const { toggle: toggleChat, open: chatOpen } = useChat()
  const { pathname } = useLocation()
  const wide = useMediaQuery('(min-width: 1280px)') // below this (tablets, small laptops) the sidebar is an icon rail, as in the mockups
  const [collapsed, setCollapsed] = useState(readRail)
  const [drawer, setDrawer] = useState(false)
  const closeDrawer = useCallback(() => setDrawer(false), [])

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  // Practice is a focus mode: the sidebar shrinks to icons and the top bar goes, so the question gets the space.
  const focus = pathname.startsWith('/latihan/')
  const rail = !wide || collapsed || focus
  const collapse = () =>
    setCollapsed((c) => {
      try {
        localStorage.setItem(RAIL_KEY, c ? 'full' : 'rail')
      } catch {
        // preference not saved
      }
      return !c
    })

  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only rounded-xl border-2 border-primary bg-surface px-4 py-2 font-bold text-primary-ink shadow focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-[60]"
      >
        <T k="skipToContent" />
      </a>

      {student && (
        <aside
          className={`on-brand scroll-thin fixed inset-y-0 start-0 z-30 hidden overflow-x-hidden overflow-y-auto bg-linear-to-b from-brand-2 to-brand p-4 transition-[width] duration-300 md:block ${
            rail ? 'w-[84px] px-3' : 'w-64'
          }`}
        >
          <SidebarContent rail={rail} onCollapse={wide && !focus ? collapse : undefined} />
        </aside>
      )}

      <div className={student ? `transition-[padding] duration-300 ${rail ? 'md:ps-[84px]' : 'md:ps-64'}` : ''}>
        {student && !focus && (
          <header className="sticky top-0 z-20 hidden h-16 items-center gap-4 border-b border-line bg-bg/85 px-6 backdrop-blur-md md:flex lg:px-10">
            <TopicSearch />
            <div className="ms-auto flex shrink-0 items-center gap-2">
              <StatChips compact={!wide} />
              <Link
                to="/kemajuan"
                title={student.name}
                className="ms-1 flex items-center gap-2.5 rounded-xl py-1 ps-1 pe-1 transition hover:bg-surface-2 lg:pe-3"
              >
                <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-full bg-gold-soft text-2xl">
                  {student.avatar}
                </span>
                <span className="sr-only leading-tight lg:not-sr-only">
                  <span className="block max-w-40 truncate text-sm font-bold text-ink">{student.name}</span>
                  {student.kelas && <span className="block text-xs text-ink-3">{student.kelas}</span>}
                </span>
              </Link>
            </div>
          </header>
        )}

        {student && (
          <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-line bg-surface/90 px-3 backdrop-blur-md md:hidden">
            <button type="button" onClick={() => setDrawer(true)} aria-label={t('openMenu')} aria-expanded={drawer} className="btn-ghost">
              <Menu aria-hidden="true" className="h-6 w-6" />
            </button>
            <NavLink to="/" className="min-w-0">
              <Brand size={30} tagline={false} />
            </NavLink>
            <span className="ms-auto flex items-center gap-2">
              <StatChips compact />
              <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-full bg-gold-soft text-xl">
                {student.avatar}
              </span>
            </span>
          </header>
        )}

        <main
          id="main"
          tabIndex={-1}
          className={`mx-auto w-full px-4 pt-5 outline-none sm:px-6 md:pt-7 lg:px-10 ${student ? 'pb-28 md:pb-12' : 'pb-10'} ${
            focus ? 'max-w-3xl' : 'max-w-6xl'
          }`}
        >
          <Outlet />
        </main>
      </div>

      {student && <MobileDrawer open={drawer} onClose={closeDrawer} />}

      {student && (
        <nav
          aria-label={t('mainMenu')}
          className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 px-2 pt-1.5 pb-[max(0.4rem,env(safe-area-inset-bottom))] backdrop-blur-md md:hidden"
        >
          <ul className="mx-auto grid max-w-md grid-cols-4 gap-1">
            <li>
              <NavLink to="/" end className={tabCls}>
                <House aria-hidden="true" className="h-5.5 w-5.5" />
                <T k="navHome" />
              </NavLink>
            </li>
            <li>
              <NavLink to="/kemajuan" className={tabCls}>
                <ChartColumn aria-hidden="true" className="h-5.5 w-5.5" />
                <T k="navProgressShort" />
              </NavLink>
            </li>
            <li>
              <button type="button" onClick={toggleChat} aria-pressed={chatOpen} className={tabCls({ isActive: chatOpen })}>
                <MessageCircle aria-hidden="true" className="h-5.5 w-5.5" />
                <T k="chatTitle" />
              </button>
            </li>
            <li>
              <button type="button" onClick={() => setDrawer(true)} aria-expanded={drawer} className={tabCls({ isActive: false })}>
                <Menu aria-hidden="true" className="h-5.5 w-5.5" />
                <T k="menu" />
              </button>
            </li>
          </ul>
        </nav>
      )}

      {student && <ChatBox />}
    </div>
  )
}
