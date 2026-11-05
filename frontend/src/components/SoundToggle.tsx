import { Volume2, VolumeX } from 'lucide-react'
import { useScript } from '../i18n/ScriptContext'
import { useSound } from '../sound/SoundContext'
import { toggleCls, type ToggleVariant } from './toggleStyle'

/** Turn sound effects on or off. State is conveyed by aria-pressed, not the icon alone. */
export default function SoundToggle({ variant = 'surface', className = '' }: { variant?: ToggleVariant; className?: string }) {
  const { enabled, toggle } = useSound()
  const { t } = useScript()
  const Icon = enabled ? Volume2 : VolumeX
  return (
    <button type="button" onClick={toggle} aria-pressed={enabled} title={t(enabled ? 'soundOn' : 'soundOff')} className={`${toggleCls[variant]} ${className}`}>
      <Icon aria-hidden="true" className="h-5 w-5" />
      <span className="sr-only">{t('sound')}</span>
    </button>
  )
}
