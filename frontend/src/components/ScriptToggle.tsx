import { useScript } from '../i18n/ScriptContext'

/** Switch the whole UI between Rumi and Jawi. The label names the script you switch to. */
export default function ScriptToggle() {
  const { script, toggle, t } = useScript()
  const toJawi = script === 'rumi'
  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-2xl border-2 border-b-4 border-sky-200 bg-white px-4 font-black text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-sky-400 active:translate-y-0.5 active:border-b-2"
    >
      <span aria-hidden="true" className="text-lg">
        🔤
      </span>
      <span className={toJawi ? 'jawi text-xl leading-none' : 'text-base'} lang={toJawi ? 'ms-Arab' : 'ms'}>
        {toJawi ? 'جاوي' : 'Rumi'}
      </span>
      <span className="sr-only"> ({t('switchScript')})</span>
    </button>
  )
}
