// Shared look of the small setting buttons (script, theme, sound) on a light surface or on the green sidebar.
export type ToggleVariant = 'surface' | 'brand'

export const toggleCls: Record<ToggleVariant, string> = {
  surface:
    'inline-flex h-11 min-w-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-line bg-surface text-ink-2 transition hover:border-primary hover:text-primary-ink',
  brand:
    'inline-flex h-11 min-w-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-brand-line bg-white/5 text-on-brand transition hover:bg-white/15',
}
