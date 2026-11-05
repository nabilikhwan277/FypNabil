import type { SubjectId } from '../api/types'
import { SUBJECT_STYLE } from './subjects'

const BOX = {
  sm: 'h-8 w-8 rounded-lg text-base',
  md: 'h-11 w-11 rounded-xl text-xl',
  lg: 'h-14 w-14 rounded-2xl text-3xl',
} as const
const JAWI_TEXT = { sm: 'text-[0.6rem]', md: 'text-sm', lg: 'text-lg' } as const

/** Subject tile: 🕌 Ibadah, the word جاوي for Jawi, 📖 Tajwid. Decorative: the subject name is always written next to it. */
export default function SubjectIcon({ id, size = 'md', className = '' }: { id: SubjectId; size?: keyof typeof BOX; className?: string }) {
  const st = SUBJECT_STYLE[id]
  return (
    <span aria-hidden="true" className={`flex shrink-0 items-center justify-center ${BOX[size]} ${st.soft} ${className}`}>
      {id === 'jawi' ? <span className={`font-jawi font-bold leading-none ${st.text} ${JAWI_TEXT[size]}`}>جاوي</span> : st.emoji}
    </span>
  )
}
