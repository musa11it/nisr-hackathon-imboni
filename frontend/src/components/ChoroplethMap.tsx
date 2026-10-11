import clsx from 'clsx'
import { geoMercator, geoPath } from 'd3-geo'
import { useMemo, type ReactNode } from 'react'
import { classOf, NO_DATA, SEQ } from '../lib/colors'
import { fmt } from '../lib/format'
import type { FeatureCollection } from '../lib/types'
import { useHoverTip } from './charts'

const W = 640
const H = 560

export interface MapProps {
  geo: FeatureCollection
  values: Record<string, number | null | undefined>
  breaks: number[]
  /** true when higher values mean more deprivation (darker = worse) */
  higherIsDarker: boolean
  unit?: string
  decimals?: number
  selected?: string | null
  onSelect?: (geoId: string) => void
  tooltip?: (geoId: string, name: string) => ReactNode
  outline?: FeatureCollection | null
  title: string
}

export function ChoroplethMap({ geo, values, breaks, higherIsDarker, unit = '%', decimals = 1, selected, onSelect, tooltip, outline, title }: MapProps) {
  const hv = useHoverTip()
  const { paths, outlinePaths } = useMemo(() => {
    const proj = geoMercator().fitExtent([[12, 12], [W - 12, H - 12]], geo as any)
    const path = geoPath(proj)
    return {
      paths: geo.features.map((f) => ({ id: f.properties.geo_id, name: f.properties.name, d: path(f as any) ?? '', c: path.centroid(f as any) })),
      outlinePaths: outline ? outline.features.map((f) => ({ id: f.properties.geo_id, d: path(f as any) ?? '' })) : [],
    }
  }, [geo, outline])

  const fill = (v: number | null | undefined) => {
    if (v === null || v === undefined) return 'url(#nodata)'
    const k = classOf(v, breaks)
    return SEQ[higherIsDarker ? k : SEQ.length - 1 - k]
  }

  return (
    <div ref={hv.attach} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} role="group" aria-label={title} className="h-auto w-full select-none">
        <defs>
          <pattern id="nodata" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="7" height="7" fill={NO_DATA} />
            <line x1="0" y1="0" x2="0" y2="7" stroke="#c9c3b5" strokeWidth="2" />
          </pattern>
        </defs>
        {paths.map((p) => {
          const v = values[p.id]
          const isSel = selected === p.id
          const label = `${p.name}: ${v == null ? 'no data' : fmt(v, unit, decimals)}`
          return (
            <path key={p.id} d={p.d} fill={fill(v)} stroke={isSel ? '#0b1a2b' : '#ffffff'} strokeWidth={isSel ? 2.4 : 1}
              strokeLinejoin="round" tabIndex={0} role="button" aria-label={label} aria-pressed={isSel}
              className={clsx('cursor-pointer outline-none transition-[filter] duration-150 hover:brightness-95 focus-visible:brightness-90')}
              onMouseMove={(e) => hv.show(e, tooltip ? tooltip(p.id, p.name) : label)} onMouseLeave={hv.hide}
              onFocus={(e) => hv.show(e, tooltip ? tooltip(p.id, p.name) : label)} onBlur={hv.hide}
              onClick={() => onSelect?.(p.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(p.id) } }} />
          )
        })}
        {outlinePaths.map((p) => (
          <path key={`o-${p.id}`} d={p.d} fill="none" stroke="#0b1a2b" strokeOpacity={0.55} strokeWidth={1.4} pointerEvents="none" />
        ))}
        {selected && paths.filter((p) => p.id === selected).map((p) => (
          <path key="sel" d={p.d} fill="none" stroke="#0b1a2b" strokeWidth={2.6} pointerEvents="none" />
        ))}
      </svg>
      {hv.node}
    </div>
  )
}

export function MapLegend({ breaks, min, max, higherIsDarker, unit = '%', decimals = 1, caption }: {
  breaks: number[]; min: number; max: number; higherIsDarker: boolean; unit?: string; decimals?: number; caption: string
}) {
  const edges = [min, ...breaks, max]
  const colors = higherIsDarker ? SEQ : [...SEQ].reverse()
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold text-text-2">{caption}</p>
      <div className="flex items-stretch gap-[2px]">
        {colors.map((c, i) => (
          <div key={i} className="flex-1">
            <div className="h-2.5 rounded-[3px]" style={{ background: c }} />
            <div className="tabular mt-1 text-[10px] text-muted">{fmt(edges[i], unit, decimals)}</div>
          </div>
        ))}
        <div className="tabular self-end pb-0 text-[10px] text-muted">{fmt(edges[edges.length - 1], unit, decimals)}</div>
      </div>
      <div className="flex items-center gap-1.5 text-[10px] text-muted">
        <svg width="14" height="10" aria-hidden><rect width="14" height="10" fill={NO_DATA} /><path d="M0 10 L10 0 M4 10 L14 0" stroke="#c9c3b5" strokeWidth="2" /></svg>
        No published value
      </div>
    </div>
  )
}
