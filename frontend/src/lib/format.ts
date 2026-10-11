export const nf = (d = 1) => new Intl.NumberFormat('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d })

export function fmt(v: number | null | undefined, unit = '%', d = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  if (unit.startsWith('index (0–1)')) return v.toFixed(3)
  if (unit === 'households' || unit === 'RWF') return Math.round(v).toLocaleString('en-GB')
  if (unit === '%') return `${nf(d).format(v)}%`
  return nf(d).format(v)
}

export const pct = (v: number | null | undefined, d = 1) => fmt(v, '%', d)

export function rwf(v: number | null | undefined, compact = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  if (compact) {
    const abs = Math.abs(v)
    if (abs >= 1e12) return `RWF ${(v / 1e12).toFixed(2)} tn`
    if (abs >= 1e9) return `RWF ${(v / 1e9).toFixed(2)} bn`
    if (abs >= 1e6) return `RWF ${(v / 1e6).toFixed(1)} m`
  }
  return `RWF ${Math.round(v).toLocaleString('en-GB')}`
}

export const int = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : Math.round(v).toLocaleString('en-GB')

export function pp(v: number | null | undefined, d = 1, signed = true): string {
  if (v === null || v === undefined) return '—'
  const s = signed && v > 0 ? '+' : v < 0 ? '−' : ''
  return `${s}${nf(d).format(Math.abs(v))} pp`
}

export const titleCase = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

/** Short label for the approximate z-test vs a reference estimate. */
export function sigText(label?: string): string {
  if (!label) return '—'
  if (label === 'higher than') return 'Significantly higher'
  if (label === 'lower than') return 'Significantly lower'
  if (label.startsWith('not statistically')) return 'No significant difference'
  return label
}

/** Two-decimal coefficient without a misleading "-0.00". */
export const r2 = (v: number) => (Math.abs(v) < 0.005 ? 0 : v).toFixed(2)
