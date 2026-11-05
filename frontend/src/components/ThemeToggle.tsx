import { Moon, Sun } from 'lucide-react'
import { useScript } from '../i18n/ScriptContext'
import { useTheme } from '../theme/ThemeContext'
import { toggleCls, type ToggleVariant } from './toggleStyle'

/** Light / dark mode. aria-pressed tells screen readers whether dark mode is on. */
export default function ThemeToggle({ variant = 'surface', className = '' }: { variant?: ToggleVariant; className?: string }) {
  const { theme, toggle } = useTheme()
  const { t } = useScript()
  const dark = theme === 'dark'
  const Icon = dark ? Moon : Sun
  return (
    <button type="button" onClick={toggle} aria-pressed={dark} title={t(dark ? 'themeLight' : 'themeDark')} className={`${toggleCls[variant]} ${className}`}>
      <Icon aria-hidden="true" className="h-5 w-5" />
      <span className="sr-only">{t('themeDark')}</span>
    </button>
  )
}
