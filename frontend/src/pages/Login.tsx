import { motion } from 'framer-motion'
import { useEffect, useId, useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { MascotSay } from '../components/Mascot'
import T from '../components/T'
import { ErrorBox } from '../components/ui'
import { useScript } from '../i18n/ScriptContext'
import { useStudent } from '../session/StudentContext'
import { useSound } from '../sound/SoundContext'

const FALLBACK_AVATARS = ['🐱', '🐰', '🦊', '🐼', '🐯', '🐨', '🦁', '🐧', '🦉', '🐢']

export default function Login() {
  const { student, signIn } = useStudent()
  const { t } = useScript()
  const { play } = useSound()
  const nav = useNavigate()
  const loc = useLocation()
  const [name, setName] = useState('')
  const [kelas, setKelas] = useState('')
  const [avatars, setAvatars] = useState(FALLBACK_AVATARS)
  const [avatar, setAvatar] = useState(FALLBACK_AVATARS[0])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nameId = useId()
  const kelasId = useId()
  const hintId = useId()

  useEffect(() => {
    api.avatars().then(setAvatars).catch(() => {})
  }, [])

  if (student) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
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
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mx-auto flex max-w-xl flex-col gap-4">
      <MascotSay mood="wave" size={120}>
        <T k="loginBubble" as="h2" className="text-xl leading-snug font-black sm:text-2xl" />
      </MascotSay>
      <T k="tagline" as="p" className="text-center font-bold text-sky-900" />

      <form onSubmit={submit} className="card flex flex-col gap-5 p-6 sm:p-8">
        <div className="flex items-end gap-4">
          <motion.span
            key={avatar}
            aria-hidden="true"
            initial={{ scale: 0.5, rotate: -20 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 14 }}
            className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-sky-100 text-5xl shadow-md ring-4 ring-white"
          >
            {avatar}
          </motion.span>
          <div className="min-w-0 flex-1">
            <label htmlFor={nameId} className="mb-1 block text-lg font-black">
              <T k="name" />
            </label>
            <input
              id={nameId}
              className="field"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={40}
              required
              autoComplete="given-name"
            />
          </div>
        </div>

        <div>
          <label htmlFor={kelasId} className="mb-1 block text-lg font-black">
            <T k="kelas" />
          </label>
          <input
            id={kelasId}
            className="field"
            value={kelas}
            onChange={(e) => setKelas(e.target.value)}
            maxLength={30}
            placeholder={t('kelasHint')}
            aria-describedby={hintId}
          />
        </div>

        <fieldset>
          <legend className="mb-2 text-lg font-black">
            <T k="chooseAvatar" />
          </legend>
          <div className="grid grid-cols-5 gap-2 sm:gap-3">
            {avatars.map((a) => {
              const on = a === avatar
              return (
                <label
                  key={a}
                  className={`relative flex aspect-square cursor-pointer items-center justify-center rounded-2xl border-2 border-b-4 text-4xl transition select-none hover:-translate-y-0.5 has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-blue-600 sm:text-5xl ${
                    on ? 'scale-105 border-emerald-600 bg-emerald-50' : 'border-slate-200 bg-white hover:border-sky-300'
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
                      className="absolute -end-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-emerald-700 text-sm font-black text-white shadow"
                    >
                      ✔
                    </span>
                  )}
                </label>
              )
            })}
          </div>
        </fieldset>

        {error && <ErrorBox message={error} />}
        <button type="submit" className="btn-primary w-full text-2xl" disabled={busy || !name.trim()}>
          <T k="start" /> <span aria-hidden="true">🚀</span>
        </button>
        <T k="loginNote" as="p" className="text-center text-sm text-slate-600" />
        <span id={hintId} className="sr-only">
          {t('kelasHint')}
        </span>
      </form>
    </motion.div>
  )
}
