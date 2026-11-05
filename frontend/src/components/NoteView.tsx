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
  h1: auto('h2', 'mt-2 text-2xl font-extrabold text-ink'),
  h2: auto('h3', 'mt-7 mb-3 flex items-center gap-2 border-b border-line pb-1.5 text-lg font-extrabold text-primary-ink'),
  h3: auto('h4', 'mt-5 mb-1 font-bold text-ink'),
  p: auto('p', 'my-2.5 leading-relaxed text-ink-2'),
  li: auto('li', 'my-1.5 leading-relaxed text-ink-2 marker:text-gold'),
  ul: auto('ul', 'ms-6 list-disc'),
  ol: auto('ol', 'ms-6 list-decimal'),
  strong: auto('strong', 'font-bold text-ink'),
  td: auto('td', 'border border-line px-3 py-2 align-top text-ink-2'),
  th: auto('th', 'border border-line bg-surface-2 px-3 py-2 text-start font-bold text-ink'),
  blockquote: auto('blockquote', 'my-4 rounded-e-xl border-s-4 border-gold bg-gold-soft px-4 py-2 text-ink'),
  code: auto('code', 'rounded bg-surface-2 px-1.5 py-0.5 text-[0.95em] text-primary-ink'),
  table: (props: ComponentPropsWithoutRef<'table'>) => (
    <div className="my-4 overflow-x-auto rounded-xl border border-line">
      <table className="w-full border-collapse text-base" {...props} />
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
