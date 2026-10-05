import { useScript } from '../i18n/ScriptContext'
import { useSound } from '../sound/SoundContext'

/** Turn sound effects on or off. State is conveyed by aria-pressed, not the icon alone. */
export default function SoundToggle() {
  const { enabled, toggle } = useSound()
  const { t } = useScript()
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={enabled}
      title={t(enabled ? 'soundOn' : 'soundOff')}
      className="inline-flex h-12 w-12 cursor-pointer items-center justify-center rounded-2xl border-2 border-b-4 border-slate-200 bg-white text-2xl shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 active:translate-y-0.5 active:border-b-2"
    >
      <span aria-hidden="true">{enabled ? '🔊' : '🔇'}</span>
      <span className="sr-only">{t('sound')}</span>
    </button>
  )
}
