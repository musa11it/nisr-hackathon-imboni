import clsx from 'clsx'
import type { ReactNode } from 'react'
import { fmt } from '../lib/format'
import type { Derived, Metric } from '../lib/types'
import { InfoTip, SourceLink, StatusBadge } from './ui'

export function KpiCard({ m, label, unit, decimals, children, footnote, accent }: {
  m: Metric | Derived | null | undefined
  label: string
  unit?: string
  decimals?: number
  children?: ReactNode
  footnote?: ReactNode
  accent?: boolean
}) {
  if (!m) return null
  const metric = m as Metric
  const u = unit ?? metric.unit ?? '%'
  const d = decimals ?? (u.startsWith('index') ? 3 : 1)
  const valueText = u === 'percentage points' ? `${(m.value as number) > 0 ? '+' : (m.value as number) < 0 ? '−' : ''}${Math.abs(m.value as number).toFixed(d)}` : fmt(m.value as number, u, d)
  const definition = (m as Metric).definition ?? (m as Derived).definition
  const formula = (m as Derived).formula
  return (
    <article className={clsx('card flex flex-col p-5', accent && 'ring-1 ring-brand-200')}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-[13px] font-semibold leading-snug text-text-2">{label}</h3>
        <InfoTip label={`About ${label}`} wide>
          <span className="block font-semibold text-white">{(m as Metric).name ?? label}</span>
          {definition && <span className="mt-1 block">{definition}</span>}
          {formula && <span className="mt-1 block text-white/70">Formula: {formula}</span>}
          {metric.universe && <span className="mt-1 block text-white/70">Universe: {metric.universe}</span>}
          {metric.indicator_notes && <span className="mt-1 block text-amber-200">{metric.indicator_notes}</span>}
        </InfoTip>
      </div>
      <p className="tabular mt-3 text-[34px] font-semibold leading-none tracking-tight text-ink-900">
        {valueText}
        {u === 'percentage points' && <span className="ml-1 text-sm font-medium text-muted">pp</span>}
      </p>
      {metric.ci_low != null && metric.ci_high != null && (
        <p className="tabular mt-1.5 text-[11.5px] text-muted">95% CI {metric.ci_low.toFixed(1)}–{metric.ci_high.toFixed(1)}{u === '%' ? '%' : ''}</p>
      )}
      {children && <div className="mt-2 text-[12px] leading-relaxed text-text-2">{children}</div>}
      <div className="mt-auto space-y-2 pt-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={m.status} />
          <span className="chip border-line bg-paper text-text-2">{m.period}</span>
        </div>
        <SourceLink source={m.source} table={metric.table_ref} />
        {footnote && <p className="text-[11px] leading-relaxed text-muted">{footnote}</p>}
      </div>
    </article>
  )
}
