import type { ElementType, ReactNode } from 'react'
import { useScript } from '../i18n/ScriptContext'

const ARABIC = /[\u0600-\u06FF\u0750-\u077F]/
const ARABIC_ALL = /[\u0600-\u06FF\u0750-\u077F]/g
const LATIN_ALL = /[A-Za-z\u00C0-\u024F]/g

// eslint-disable-next-line react-refresh/only-export-components
export function isArabic(text: string): boolean {
  return ARABIC.test(text)
}

/**
 * Direction of a text by its majority script, so a Rumi sentence quoting one
 * Jawi letter stays left-to-right and a Jawi sentence with "XP" stays right-to-left.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function textDir(text: string): 'rtl' | 'ltr' {
  const arabic = text.match(ARABIC_ALL)?.length ?? 0
  const latin = text.match(LATIN_ALL)?.length ?? 0
  return arabic > latin ? 'rtl' : 'ltr'
}

interface Props {
  rumi: string
  jawi?: string
  as?: ElementType
  className?: string
  id?: string
  children?: ReactNode
}

/**
 * Show the Rumi or Jawi version of a text according to the chosen script.
 * Falls back to Rumi when no Jawi is available. Jawi text gets RTL + Naskh font
 * and the right `lang`, so screen readers pronounce it correctly.
 */
export default function Bi({ rumi, jawi, as: Tag = 'span', className = '', id, children }: Props) {
  const { script } = useScript()
  const text = script === 'jawi' && jawi ? jawi : rumi
  const rtl = textDir(text) === 'rtl'
  return (
    <Tag
      id={id}
      className={`${rtl ? 'jawi' : ''} ${className}`.trim()}
      dir={rtl ? 'rtl' : 'ltr'}
      lang={rtl ? 'ms-Arab' : 'ms'}
    >
      {text}
      {children}
    </Tag>
  )
}
