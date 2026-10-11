// Validated with the dataviz palette validator (see docs/METHODOLOGY.md §Visual encoding).
// Categorical slots in FIXED order — colour follows the entity, never its rank.
export const SERIES = {
  s1: '#2a78d6', // blue   — selected area / primary series
  s2: '#eb6834', // orange — comparison (province)
  s3: '#1baf7a', // aqua   — third series (contrast relief: always labelled)
  s4: '#eda100', // yellow — only in 4-part stacks (adjacent pairs validated)
}

export const INK = { primary: '#0f1b2d', secondary: '#4a4f58', muted: '#7b7f86', grid: '#ebe7de', axis: '#cfc9bb' }

// Single-hue sequential ramp (teal), light -> dark = less -> more deprived.
export const SEQ = ['#d7ece8', '#9fd1c8', '#5faea3', '#2b867d', '#0d5755']
export const NO_DATA = '#e9e6df'

// FinScope Access Strand, in the order the report stacks them.
export const STRAND = [
  { key: 'fs_banked', label: 'Banked', color: SERIES.s1 },
  { key: 'fs_other_formal', label: 'Other formal (non-bank)', color: SERIES.s2 },
  { key: 'fs_informal_only', label: 'Informal only', color: SERIES.s3 },
  { key: 'fs_excluded', label: 'Excluded', color: SERIES.s4 },
] as const

// Diverging blue <-> red with neutral grey midpoint (correlations).
const DIV = ['#104281', '#2a78d6', '#86b6ef', '#cde2fb', '#f0efec', '#fbd5d4', '#f08f8e', '#e34948', '#9b2726']
export function diverging(v: number): string {
  const t = Math.max(-1, Math.min(1, v))
  const idx = Math.round(((t + 1) / 2) * (DIV.length - 1))
  return DIV[DIV.length - 1 - idx]
}
export const DIVERGING = DIV

export function quantileBreaks(values: number[], k = 5): number[] {
  const v = [...values].sort((a, b) => a - b)
  if (v.length === 0) return []
  const out: number[] = []
  for (let i = 1; i < k; i++) {
    const pos = (v.length - 1) * (i / k)
    const lo = Math.floor(pos)
    const hi = Math.ceil(pos)
    out.push(v[lo] + (v[hi] - v[lo]) * (pos - lo))
  }
  return out
}

export function classOf(v: number, breaks: number[]): number {
  let i = 0
  while (i < breaks.length && v > breaks[i]) i++
  return i
}
