// Number formats of the admin pages ('–' = no value yet).
export const pct = (v: number | null | undefined, d = 0) => (v === null || v === undefined ? '–' : `${(v * 100).toFixed(d)}%`)
export const num = (v: number | null | undefined, d = 3) => (v === null || v === undefined ? '–' : v.toFixed(d))
export const usd = (v: number | null | undefined, d = 4) => (v === null || v === undefined ? '–' : `$${v.toFixed(d)}`)
