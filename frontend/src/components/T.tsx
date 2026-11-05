import type { ElementType } from 'react'
import { STRINGS, type StringKey } from '../i18n/strings'
import Bi from './Bi'

/** A UI string from STRINGS in the current script. */
export default function T({
  k,
  as,
  className,
  style,
  id,
}: {
  k: StringKey
  as?: ElementType
  className?: string
  style?: React.CSSProperties
  id?: string
}) {
  return <Bi rumi={STRINGS[k].rumi} jawi={STRINGS[k].jawi} as={as} className={className} style={style} id={id} />
}
