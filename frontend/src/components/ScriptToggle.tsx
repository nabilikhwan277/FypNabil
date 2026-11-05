import { Languages } from 'lucide-react'
import { useScript } from '../i18n/ScriptContext'
import { toggleCls, type ToggleVariant } from './toggleStyle'

/**
 * Switch the whole UI between Rumi and Jawi. The label names the script you switch to.
 * `compact` drops the icon so it fits the icon rail. `brand` is the version for the green sidebar.
 */
export default function ScriptToggle({
  compact = false,
  variant = 'surface',
  className = '',
}: {
  compact?: boolean
  variant?: ToggleVariant
  className?: string
}) {
  const { script, toggle, t } = useScript()
  const toJawi = script === 'rumi'
  return (
    <button type="button" onClick={toggle} title={t('switchScript')} className={`${toggleCls[variant]} ${compact ? 'w-11' : 'px-3'} ${className}`}>
      {!compact && <Languages aria-hidden="true" className="h-4.5 w-4.5" />}
      <span className={toJawi ? 'jawi text-base leading-none font-bold' : 'text-sm font-bold'} lang={toJawi ? 'ms-Arab' : 'ms'}>
        {toJawi ? 'جاوي' : 'Rumi'}
      </span>
      <span className="sr-only"> ({t('switchScript')})</span>
    </button>
  )
}
