export type Status = 'official' | 'official_transcribed' | 'calculated' | 'illustrative' | 'experimental'

export interface SourceRef {
  id: string
  title: string
  short: string
  url: string
  landing_page?: string
  publisher?: string
}

export interface Metric {
  indicator_id: string
  name: string
  short_name: string
  unit: string
  universe?: string
  definition: string
  polarity: 'higher_worse' | 'higher_better' | 'neutral'
  decimals: number
  theme: string
  level: string
  geo_id: string
  geo_name: string
  breakdown: string
  value: number | null
  se: number | null
  ci_low: number | null
  ci_high: number | null
  cv: number | null
  deff: number | null
  period: string
  status: Status
  table_ref: string
  flags: string[]
  note?: string | null
  source: SourceRef
  indicator_notes?: string | null
}

export interface Derived {
  value: number
  unit: string
  status: Status
  period: string
  formula: string
  source: SourceRef
  definition?: string
  [k: string]: unknown
}

export interface IndicatorMeta {
  id: string
  name: string
  short_name: string
  theme: string
  unit: string
  universe: string
  definition: string
  source_id: string
  table_ref: string
  polarity: 'higher_worse' | 'higher_better' | 'neutral'
  period: string
  notes: string | null
  status: Status
  decimals: number
  levels: string[]
}

export interface Comparison {
  available: boolean
  label: string
  diff?: number
  p_value?: number
  z?: number
}

export interface MapRow extends Metric {
  rank?: number
  rank_low?: number
  rank_high?: number
  vs_national: Comparison
}

export interface MapLayer {
  indicator: IndicatorMeta
  level: string
  national: Metric | null
  rows: MapRow[]
  summary: { n: number; min: number; max: number; median: number; range_ratio: number | null }
  rank_note: string
}

export interface Feature {
  type: 'Feature'
  properties: { geo_id: string; name: string; level: string; province_id?: string; province?: string }
  geometry: GeoJSON.Geometry
}
export interface FeatureCollection {
  type: 'FeatureCollection'
  features: Feature[]
  attribution: string
}
