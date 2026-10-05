import type { ComponentPropsWithoutRef, ElementType } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Notes mix Rumi and Jawi line by line. dir="auto" lets the browser pick the
// direction of each block from its first strong character.
const auto =
  (Tag: ElementType, className = '') =>
  // eslint-disable-next-line @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any
  ({ node, ...rest }: any) => <Tag dir="auto" className={className} {...rest} />


const components: Components = {
  h1: auto('h2', 'mt-2 text-2xl font-black'),
  h2: auto('h3', 'mt-6 mb-2 text-xl font-black text-emerald-800'),
  h3: auto('h4', 'mt-4 mb-1 text-lg font-black'),
  p: auto('p', 'my-2 leading-relaxed'),
  li: auto('li', 'my-1 leading-relaxed'),
  ul: auto('ul', 'ms-6 list-disc'),
  ol: auto('ol', 'ms-6 list-decimal'),
  td: auto('td', 'border border-slate-200 px-3 py-2 align-top'),
  th: auto('th', 'border border-slate-200 bg-slate-100 px-3 py-2 text-start'),
  blockquote: auto('blockquote', 'my-3 border-s-4 border-amber-300 bg-amber-50 px-4 py-2 text-slate-700'),
  table: (props: ComponentPropsWithoutRef<'table'>) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
}

/**
 * Notes pair each Rumi line with a Jawi line ("**Rumi:** ...\n**Jawi:** ...").
 * Markdown would merge them into one mixed-direction paragraph, so split them:
 * - paragraph pairs -> two paragraphs, labels dropped (each gets its own direction)
 * - list items "**Rumi:** a | **Jawi:** b" -> hard line break inside the item
 */
// eslint-disable-next-line react-refresh/only-export-components
export function splitBilingual(md: string): string {
  return md
    .replace(/^(\s*[-*]|\s*\d+\.)\s+\*\*Rumi:\*\*\s*(.+?)\s*\|\s*\*\*Jawi:\*\*\s*/gm, '$1 $2\\\n   ')
    .replace(/^\*\*Rumi:\*\*\s*/gm, '')
    .replace(/\n\*\*Jawi:\*\*\s*/g, '\n\n')
}

/** Render a topic note (markdown). Content is our own curated notes; raw HTML is not rendered. */
export default function NoteView({ markdown }: { markdown: string }) {
  return (
    <article className="note-body max-w-none text-[1.05rem]">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {splitBilingual(markdown)}
      </Markdown>
    </article>
  )
}
