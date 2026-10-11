import clsx from 'clsx'
import { useState, type ReactNode, type MouseEvent as RMouseEvent } from 'react'
import { INK, SERIES } from '../lib/colors'
import { fmt } from '../lib/format'

/* --------------------------------------------------------------- hover tooltip */
export function useHoverTip() {
  const [el, setEl] = useState<HTMLDivElement | null>(null)
  const [tip, setTip] = useState<{ x: number; y: number; w: number; content: ReactNode } | null>(null)
  const show = (e: RMouseEvent | React.FocusEvent, content: ReactNode) => {
    const box = el?.getBoundingClientRect()
    if (!box) return
    if ('clientX' in e) setTip({ x: e.clientX - box.left, y: e.clientY - box.top, w: box.width, content })
    else {
      const t = (e.target as HTMLElement).getBoundingClientRect()
      setTip({ x: t.left - box.left + t.width / 2, y: t.top - box.top, w: box.width, content })
    }
  }
  const hide = () => setTip(null)
  const node = tip ? (
    <div role="tooltip" className="pointer-events-none absolute z-40 min-w-36 max-w-64 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-xl bg-ink-900 px-3 py-2 text-xs leading-relaxed text-white shadow-[var(--shadow-lift)]"
      style={{ left: Math.max(70, Math.min(tip.x, tip.w - 70)), top: tip.y }}>
      {tip.content}
    </div>
  ) : null
  return { attach: setEl, show, hide, node }
}

/* --------------------------------------------------------------- legend */
export function Legend({ items }: { items: { label: string; color?: string; shape?: 'dot' | 'diamond' | 'tick' | 'square' }[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-text-2" aria-label="Legend">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <Marker shape={i.shape ?? 'square'} color={i.color ?? INK.primary} />
          {i.label}
        </li>
      ))}
    </ul>
  )
}

function Marker({ shape, color }: { shape: string; color: string }) {
  if (shape === 'tick') return <span className="inline-block h-3 w-0.5 rounded" style={{ background: color }} aria-hidden />
  if (shape === 'diamond') return <span className="inline-block h-2.5 w-2.5 rotate-45 rounded-[2px]" style={{ background: color }} aria-hidden />
  if (shape === 'dot') return <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} aria-hidden />
  return <span className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ background: color }} aria-hidden />
}

/* --------------------------------------------------------------- horizontal bar list */
export interface BarDatum { key: string; label: ReactNode; value: number | null; sub?: ReactNode; tip?: ReactNode; highlight?: boolean }

export function BarList({ data, max, unit = '%', decimals = 1, reference, referenceLabel = 'National', color = '#1d8477', onSelect, labelWidth = 'w-40' }: {
  data: BarDatum[]; max?: number; unit?: string; decimals?: number; reference?: number | null; referenceLabel?: string
  color?: string; onSelect?: (key: string) => void; labelWidth?: string
}) {
  const hv = useHoverTip()
  const m = max ?? Math.max(...data.map((d) => d.value ?? 0), reference ?? 0) * 1.08
  return (
    <div ref={hv.attach} className="relative">
      <ul className="space-y-1.5">
        {data.map((d) => {
          const w = d.value === null ? 0 : (d.value / m) * 100
          const Inner = onSelect ? 'button' : 'div'
          return (
            <li key={d.key}>
              <Inner {...(onSelect ? { type: 'button' as const, onClick: () => onSelect(d.key) } : {})}
                className={clsx('group flex w-full items-center gap-3 rounded-lg px-1 py-0.5 text-left', onSelect && 'hover:bg-paper')}
                onMouseMove={(e: RMouseEvent) => d.tip && hv.show(e, d.tip)} onMouseLeave={hv.hide}>
                <span className={clsx('shrink-0 truncate text-[12.5px]', labelWidth, d.highlight ? 'font-semibold text-ink-900' : 'text-text-2')}>{d.label}</span>
                <span className="relative h-5 flex-1">
                  <span className="absolute inset-y-[3px] left-0 rounded-r-[4px] transition-[width] duration-500"
                    style={{ width: `${w}%`, background: color, opacity: d.highlight === false ? 0.45 : 1 }} />
                  {reference != null && (
                    <span className="absolute inset-y-0 w-0.5 rounded bg-ink-900" style={{ left: `${(reference / m) * 100}%` }}
                      title={`${referenceLabel}: ${fmt(reference, unit, decimals)}`} />
                  )}
                </span>
                <span className="tabular w-16 shrink-0 text-right text-[12.5px] font-semibold text-ink-900">
                  {d.value === null ? <span className="font-normal text-muted">n/a</span> : fmt(d.value, unit, decimals)}
                </span>
              </Inner>
            </li>
          )
        })}
      </ul>
      {reference != null && (
        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted"><span className="inline-block h-3 w-0.5 rounded bg-ink-900" aria-hidden />{referenceLabel} {fmt(reference, unit, decimals)}</p>
      )}
      {hv.node}
    </div>
  )
}

/* --------------------------------------------------------------- dot plot (area vs province vs national) */
export interface DotRow { key: string; label: string; area: number | null; province?: number | null; national?: number | null; tip?: ReactNode }

export function DotPlot({ rows, areaLabel, provinceLabel, max = 100, unit = '%' }: {
  rows: DotRow[]; areaLabel: string; provinceLabel?: string; max?: number; unit?: string
}) {
  const hv = useHoverTip()
  const x = (v: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`
  return (
    <div ref={hv.attach} className="relative">
      <div className="mb-3">
        <Legend items={[{ label: areaLabel, color: SERIES.s1, shape: 'dot' },
          ...(provinceLabel ? [{ label: provinceLabel, color: SERIES.s2, shape: 'diamond' as const }] : []),
          { label: 'Rwanda', color: INK.primary, shape: 'tick' as const }]} />
      </div>
      <ul className="space-y-2">
        {rows.map((r) => (
          <li key={r.key} className="grid grid-cols-[minmax(8rem,13rem)_1fr_3.5rem] items-center gap-3"
            onMouseMove={(e) => hv.show(e, r.tip ?? <>{r.label}: {fmt(r.area, unit)}</>)} onMouseLeave={hv.hide}>
            <span className="truncate text-[12.5px] text-text-2">{r.label}</span>
            <span className="relative h-6">
              <span className="absolute inset-x-0 top-1/2 h-px bg-line" aria-hidden />
              {[25, 50, 75].map((g) => <span key={g} className="absolute top-1.5 bottom-1.5 w-px bg-line/70" style={{ left: `${g}%` }} aria-hidden />)}
              {r.national != null && <span className="absolute top-0.5 bottom-0.5 w-[3px] -translate-x-1/2 rounded bg-ink-900" style={{ left: x(r.national) }} aria-hidden />}
              {r.province != null && <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rotate-45 rounded-[2px] ring-2 ring-white" style={{ left: x(r.province), background: SERIES.s2 }} aria-hidden />}
              {r.area != null && <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white" style={{ left: x(r.area), background: SERIES.s1 }} aria-hidden />}
            </span>
            <span className="tabular text-right text-[12.5px] font-semibold text-ink-900">{fmt(r.area, unit)}</span>
          </li>
        ))}
      </ul>
      <div className="mt-1 grid grid-cols-[minmax(8rem,13rem)_1fr_3.5rem] gap-3 text-[10px] text-muted" aria-hidden>
        <span />
        <span className="flex justify-between"><span>0</span><span>{max / 2}</span><span>{max}{unit === '%' ? '%' : ''}</span></span>
      </div>
      {hv.node}
    </div>
  )
}

/* --------------------------------------------------------------- 100% stacked row */
export function StackRow({ label, segments, onHover, sub }: {
  label: ReactNode; sub?: ReactNode
  segments: { key: string; label: string; value: number | null; color: string }[]
  onHover?: (e: RMouseEvent, seg: { label: string; value: number | null }) => void
}) {
  const total = segments.reduce((s, x) => s + (x.value ?? 0), 0) || 100
  return (
    <div className="grid grid-cols-[minmax(6rem,9rem)_1fr] items-center gap-3">
      <div className="truncate text-[12.5px] text-text-2">{label}{sub}</div>
      <div className="flex h-6 w-full gap-[2px] overflow-hidden rounded-[6px]">
        {segments.map((s) => s.value ? (
          <div key={s.key} className="flex items-center justify-center text-[10.5px] font-semibold text-white"
            style={{ width: `${(s.value / total) * 100}%`, background: s.color, color: s.color === SERIES.s4 || s.color === SERIES.s3 ? INK.primary : '#fff' }}
            onMouseMove={(e) => onHover?.(e, s)}>
            {(s.value / total) * 100 >= 7 ? Math.round(s.value) : ''}
          </div>
        ) : null)}
      </div>
    </div>
  )
}

/* --------------------------------------------------------------- CI forest row */
export function CIRow({ label, value, lo, hi, reference, max = 100, highlight, unit = '%', right }: {
  label?: ReactNode; value: number | null; lo: number | null; hi: number | null; reference?: number | null
  max?: number; highlight?: boolean; unit?: string; right?: ReactNode
}) {
  const x = (v: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`
  return (
    <div className={clsx('grid items-center gap-3', label != null ? 'grid-cols-[minmax(6rem,9rem)_1fr_auto]' : 'grid-cols-[1fr_auto]')}>
      {label != null && <span className={clsx('truncate text-[12.5px]', highlight ? 'font-semibold text-ink-900' : 'text-text-2')}>{label}</span>}
      <span className="relative h-5">
        {reference != null && <span className="absolute inset-y-0 w-px bg-ink-900/60" style={{ left: x(reference) }} aria-hidden />}
        {lo != null && hi != null && (
          <span className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full" style={{ left: x(lo), width: `calc(${x(Math.min(hi, max))} - ${x(lo)})`, background: highlight ? SERIES.s1 : '#9fb7d6' }} aria-hidden />
        )}
        {value != null && <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white" style={{ left: x(value), background: highlight ? SERIES.s1 : '#5b84b8' }} aria-hidden />}
      </span>
      <span className="tabular text-right text-[12px] text-ink-900">{right ?? fmt(value, unit)}</span>
    </div>
  )
}

/* --------------------------------------------------------------- number with big type */
export function BigNumber({ value, unit, className }: { value: string; unit?: string; className?: string }) {
  return (
    <span className={clsx('tabular font-semibold tracking-tight text-ink-900', className)}>
      {value}{unit && <span className="ml-1 text-base font-medium text-muted">{unit}</span>}
    </span>
  )
}
