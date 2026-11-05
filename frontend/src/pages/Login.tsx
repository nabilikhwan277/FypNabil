import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Backpack, GraduationCap, Hourglass, LogIn, ShieldCheck, TriangleAlert, type LucideIcon } from 'lucide-react'
import { useEffect, useId, useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { Brand } from '../components/Logo'
import Mascot from '../components/Mascot'
import MosqueScene from '../components/MosqueScene'
import ScriptToggle from '../components/ScriptToggle'
import SubjectIcon from '../components/SubjectIcon'
import { SUBJECT_ORDER } from '../components/subjects'
import T from '../components/T'
import ThemeToggle from '../components/ThemeToggle'
import type { StringKey } from '../i18n/strings'
import { useScript } from '../i18n/ScriptContext'
import { useAdmin } from '../session/AdminContext'
import { useStudent } from '../session/StudentContext'
import { useSound } from '../sound/SoundContext'

const FALLBACK_AVATARS = ['🐱', '🐰', '🦊', '🐼', '🐯', '🐨', '🦁', '🐧', '🦉', '🐢']
const SUBJECT_NAME: Record<string, StringKey> = { fiqh: 'ibadahDesc', jawi: 'jawiDesc', tajwid: 'tajwidDesc' }

type Role = 'murid' | 'guru' | 'admin'

// Teacher sign-in is not built yet; its tab shows what is coming. Admin signs in with the admin password.
const ROLES: { id: Role; label: StringKey; icon: LucideIcon }[] = [
  { id: 'murid', label: 'roleStudent', icon: Backpack },
  { id: 'guru', label: 'roleTeacher', icon: GraduationCap },
  { id: 'admin', label: 'roleAdmin', icon: ShieldCheck },
]

export default function Login() {
  const { student, signIn } = useStudent()
  const { t } = useScript()
  const { play } = useSound()
  const nav = useNavigate()
  const loc = useLocation()

  const { session: admin, signIn: adminSignIn } = useAdmin()
  const asked = loc.state as { from?: string; role?: Role } | null
  const [role, setRole] = useState<Role>(asked?.role ?? 'murid')
  const [password, setPassword] = useState('')
  const passwordId = useId()
  const [name, setName] = useState('')
  const [kelas, setKelas] = useState('')
  const [avatars, setAvatars] = useState(FALLBACK_AVATARS)
  const [avatar, setAvatar] = useState(FALLBACK_AVATARS[0])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nameId = useId()
  const kelasId = useId()

  useEffect(() => {
    api.avatars().then(setAvatars).catch(() => {})
  }, [])
  if (student && asked?.role !== 'admin') return <Navigate to="/" replace />

  const submitAdmin = async (e: FormEvent) => {
    e.preventDefault()
    if (!password) return
    setBusy(true)
    setError(null)
    try {
      adminSignIn(await api.adminLogin(password))
      nav(asked?.from?.startsWith('/admin') ? asked.from : '/admin', { replace: true })
    } catch (err) {
      const status = (err as { status?: number }).status
      setError(status === 401 ? t('adminWrong') : status === 503 ? t('adminOff') : (err as Error).message)
    } finally {
      setBusy(false)
      setPassword('')
    }
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (role !== 'murid' || !name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const s = await api.login(name.trim(), kelas.trim(), avatar)
      play('correct')
      signIn(s)
      const from = (loc.state as { from?: string } | null)?.from
      nav(from && from !== '/login' ? from : '/', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Welcome panel */}
      <section className="on-brand relative flex flex-col justify-between gap-8 overflow-hidden bg-linear-to-br from-brand-2 to-brand p-6 text-on-brand sm:p-10 lg:w-[44%] lg:p-12">
        <MosqueScene className="pointer-events-none absolute inset-x-0 bottom-0 w-full text-white/[0.07]" />
        <span aria-hidden="true" className="pointer-events-none absolute end-12 top-1/3 animate-twinkle text-xl text-gold">
          ✦
        </span>

        <Link to="/landing" className="relative self-start rounded-xl">
          <Brand size={48} tone="light" />
        </Link>

        <div className="relative flex items-end gap-4">
          <Mascot mood="wave" size={120} className="shrink-0 drop-shadow-xl max-sm:w-24" />
          <div className="relative mb-4 rounded-2xl bg-surface px-5 py-4 text-lg font-semibold text-ink shadow-lg">
            <span aria-hidden="true" className="absolute bottom-6 -start-2 h-4 w-4 rotate-45 bg-surface" />
            <T k="loginBubble" as="p" className="relative" />
          </div>
        </div>

        <ul className="relative hidden flex-col gap-2 lg:flex">
          {SUBJECT_ORDER.map((id) => (
            <li key={id} className="flex items-center gap-3 rounded-xl border border-brand-line bg-white/10 px-4 py-2.5 font-semibold backdrop-blur-sm">
              <SubjectIcon id={id} size="sm" />
              <T k={SUBJECT_NAME[id]} />
            </li>
          ))}
        </ul>
      </section>

      {/* Form */}
      <section className="flex flex-1 flex-col items-center justify-center px-4 py-8 sm:px-8">
        <div className="mb-6 flex w-full max-w-md justify-end gap-2">
          <ScriptToggle />
          <ThemeToggle />
        </div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
          <T k="loginTitle" as="h1" className="text-3xl font-extrabold text-ink" />
          <T k="tagline" as="p" className="mt-1 text-ink-2" />

          {/* Role tabs */}
          <div role="group" className="mt-6 grid grid-cols-3 gap-1 rounded-2xl border border-line bg-surface-2 p-1.5">
            {ROLES.map((r) => (
              <button
                key={r.id}
                type="button"
                aria-pressed={role === r.id}
                onClick={() => {
                  setRole(r.id)
                  setError(null)
                }}
                className={`flex min-h-12 cursor-pointer items-center justify-center gap-1.5 rounded-xl font-bold transition ${
                  role === r.id ? 'bg-brand text-on-brand shadow-sm' : 'text-ink-3 hover:text-ink'
                }`}
              >
                <r.icon aria-hidden="true" className="h-4.5 w-4.5" />
                <T k={r.label} />
              </button>
            ))}
          </div>

          <div className="card mt-4">
            <AnimatePresence mode="wait">
              {role === 'murid' ? (
                <motion.form key="murid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onSubmit={submit} className="flex flex-col gap-5">
                  <div className="flex items-end gap-3">
                    <motion.span
                      key={avatar}
                      aria-hidden="true"
                      initial={{ scale: 0.6, rotate: -15 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: 'spring', stiffness: 280, damping: 16 }}
                      className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border-2 border-primary bg-primary-soft text-4xl"
                    >
                      {avatar}
                    </motion.span>
                    <div className="min-w-0 flex-1">
                      <label htmlFor={nameId} className="eyebrow mb-1.5 block">
                        <T k="name" />
                      </label>
                      <input
                        id={nameId}
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder={t('namePlaceholder')}
                        required
                        maxLength={40}
                        autoComplete="given-name"
                        dir="auto"
                        className="field"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor={kelasId} className="eyebrow mb-1.5 block">
                      <T k="kelas" />
                    </label>
                    <input
                      id={kelasId}
                      value={kelas}
                      onChange={(e) => setKelas(e.target.value)}
                      placeholder={t('kelasHint')}
                      maxLength={30}
                      dir="auto"
                      className="field"
                    />
                  </div>

                  <fieldset>
                    <legend className="eyebrow mb-2">
                      <T k="chooseAvatar" />
                    </legend>
                    <div className="grid grid-cols-5 gap-2">
                      {avatars.map((a) => {
                        const on = a === avatar
                        return (
                          <label
                            key={a}
                            className={`relative flex aspect-square cursor-pointer items-center justify-center rounded-2xl border-2 text-3xl transition has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-primary ${
                              on ? 'scale-105 border-primary bg-primary-soft shadow-sm' : 'border-line bg-surface-2 hover:border-line-strong'
                            }`}
                          >
                            <input
                              type="radio"
                              name="avatar"
                              value={a}
                              checked={on}
                              onChange={() => {
                                setAvatar(a)
                                play('tap')
                              }}
                              className="sr-only"
                            />
                            <span aria-hidden="true">{a}</span>
                            <span className="sr-only">Avatar {a}</span>
                            {on && (
                              <span
                                aria-hidden="true"
                                className="absolute -end-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[11px] font-black text-on-primary"
                              >
                                ✓
                              </span>
                            )}
                          </label>
                        )
                      })}
                    </div>
                  </fieldset>

                  {error && (
                    <p role="alert" className="flex items-start gap-2 rounded-xl bg-danger-soft px-4 py-2.5 font-semibold text-danger-ink">
                      <TriangleAlert aria-hidden="true" className="mt-0.5 h-4.5 w-4.5 shrink-0" />
                      {error}
                    </p>
                  )}

                  <button type="submit" disabled={busy || !name.trim()} className="btn-primary min-h-13 w-full text-lg">
                    {busy ? (
                      <>
                        <Hourglass aria-hidden="true" className="h-5 w-5" /> <T k="checking" />
                      </>
                    ) : (
                      <>
                        <T k="start" /> <ArrowRight aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" />
                      </>
                    )}
                  </button>
                  <T k="loginNote" as="p" className="text-center text-sm text-ink-3" />
                </motion.form>
              ) : role === 'admin' ? (
                <motion.form key="admin" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onSubmit={submitAdmin} className="flex flex-col gap-5">
                  <div className="flex items-center gap-3">
                    <span aria-hidden="true" className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-info-soft text-info-ink">
                      <ShieldCheck className="h-7 w-7" />
                    </span>
                    <T k="adminNote" as="p" className="text-ink-2" />
                  </div>
                  {admin ? (
                    <button type="button" onClick={() => nav('/admin')} className="btn-primary w-full text-lg">
                      <T k="adminContinue" /> <ArrowRight aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" />
                    </button>
                  ) : (
                    <>
                      <div>
                        <label htmlFor={passwordId} className="eyebrow mb-1.5 block">
                          <T k="adminPassword" />
                        </label>
                        <input
                          id={passwordId}
                          type="password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                          maxLength={200}
                          autoComplete="current-password"
                          className="field"
                        />
                      </div>
                      {error && (
                        <p role="alert" className="flex items-start gap-2 rounded-xl bg-danger-soft px-4 py-2.5 font-semibold text-danger-ink">
                          <TriangleAlert aria-hidden="true" className="mt-0.5 h-4.5 w-4.5 shrink-0" />
                          {error}
                        </p>
                      )}
                      <button type="submit" disabled={busy || !password} className="btn-primary w-full text-lg">
                        {busy ? (
                          <>
                            <Hourglass aria-hidden="true" className="h-5 w-5" /> <T k="checking" />
                          </>
                        ) : (
                          <>
                            <LogIn aria-hidden="true" className="h-5 w-5 rtl:-scale-x-100" /> <T k="adminSignIn" />
                          </>
                        )}
                      </button>
                    </>
                  )}
                </motion.form>
              ) : (
                <motion.div key={role} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-3 py-6 text-center">
                  <span aria-hidden="true" className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gold-soft text-gold-ink">
                    <GraduationCap className="h-10 w-10" />
                  </span>
                  <p className="text-xl font-extrabold text-ink">
                    <T k="roleTeacher" /> · <T k="comingSoon" />
                  </p>
                  <T k="comingSoonDesc" as="p" className="text-ink-2" />
                  <button type="button" onClick={() => setRole('murid')} className="btn-secondary mt-2">
                    <Backpack aria-hidden="true" className="h-4.5 w-4.5" /> <T k="roleStudent" />
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <p className="mt-6 text-center text-sm font-bold text-ink-3">
            <Link to="/landing" className="underline underline-offset-4 hover:text-primary-ink">
              <T k="aboutApp" />
            </Link>
          </p>
        </motion.div>
      </section>
    </div>
  )
}
