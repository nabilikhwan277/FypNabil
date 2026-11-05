import type { RefObject } from 'react'
import { useScript } from '../i18n/ScriptContext'

// Jawi alphabet in the standard order, including the six Jawi-specific
// letters (چ ڠ ڤ ݢ ۏ ڽ), plus common extra forms used in the textbooks.
const ROWS: string[][] = [
  ['ا', 'ب', 'ت', 'ث', 'ج', 'چ', 'ح', 'خ', 'د', 'ذ'],
  ['ر', 'ز', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ', 'ع', 'غ'],
  ['ڠ', 'ف', 'ڤ', 'ق', 'ك', 'ݢ', 'ل', 'م', 'ن', 'و'],
  ['ۏ', 'ه', 'ء', 'ي', 'ڽ', 'ى', 'ة', 'أ', 'إ', '٢'],
]
const SPECIAL = new Set(['چ', 'ڠ', 'ڤ', 'ݢ', 'ۏ', 'ڽ'])

interface Props {
  target: RefObject<HTMLTextAreaElement | null>
  value: string
  onChange: (v: string) => void
}

/** On-screen Jawi keyboard. Inserts at the caret of the target textarea. */
export default function JawiKeyboard({ target, value, onChange }: Props) {
  const { script } = useScript()

  const insert = (text: string) => {
    const el = target.current
    const start = el?.selectionStart ?? value.length
    const end = el?.selectionEnd ?? value.length
    const next = value.slice(0, start) + text + value.slice(end)
    onChange(next)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.setSelectionRange(start + text.length, start + text.length)
    })
  }

  const backspace = () => {
    const el = target.current
    const start = el?.selectionStart ?? value.length
    const end = el?.selectionEnd ?? value.length
    if (start === 0 && end === 0) return
    const from = start === end ? Array.from(value.slice(0, start)).slice(0, -1).join('').length : start
    onChange(value.slice(0, from) + value.slice(end))
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.setSelectionRange(from, from)
    })
  }

  // Chunky keys with the primary colour on hover/press; Jawi-only letters are tinted.
  const key =
    'flex h-12 min-w-0 cursor-pointer items-center justify-center rounded-xl border-2 border-b-4 border-line-strong bg-surface text-2xl text-ink transition select-none hover:border-primary hover:text-primary-ink active:translate-y-0.5 active:border-b-2'

  return (
    <div
      role="group"
      aria-label={script === 'jawi' ? 'ڤاڤن ککونچي جاوي' : 'Papan kekunci Jawi'}
      className="rounded-2xl border border-line bg-surface-2 p-3"
    >
      <div dir="rtl" className="flex flex-col gap-2">
        {ROWS.map((row, i) => (
          <div key={i} className="grid grid-cols-10 gap-1.5">
            {row.map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() => insert(ch)}
                aria-label={`Huruf ${ch}`}
                className={`${key} font-jawi ${SPECIAL.has(ch) ? 'border-primary/50 bg-primary-soft text-primary-ink' : ''}`}
              >
                {ch}
              </button>
            ))}
          </div>
        ))}
        <div className="grid grid-cols-10 gap-1.5">
          <button type="button" onClick={backspace} aria-label="Padam" className={`${key} col-span-2 bg-danger-soft text-danger-ink hover:border-danger hover:text-danger-ink`}>
            ⌫
          </button>
          <button type="button" onClick={() => insert(' ')} aria-label="Jarak" className={`${key} col-span-6 text-base`}>
            ␣
          </button>
          <button type="button" onClick={() => insert('،')} aria-label="Koma" className={key}>
            ،
          </button>
          <button type="button" onClick={() => insert('؟')} aria-label="Tanda soal" className={key}>
            ؟
          </button>
        </div>
      </div>
    </div>
  )
}
