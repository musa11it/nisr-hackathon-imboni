import clsx from 'clsx'
import { AlertTriangle, ExternalLink, FlaskConical, Info, Inbox, Calculator, BadgeCheck, FileSearch, Lightbulb } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import type { SourceRef, Status } from '../lib/types'

/* ------------------------------------------------------------------ status */
const STATUS: Record<Status, { label: string; cls: string; icon: typeof Info; tip: string }> = {
  official: {
    label: 'Official', cls: 'border-brand-200 bg-brand-50 text-brand-700', icon: BadgeCheck,
    tip: 'Value printed in an official NISR Excel table, reproduced unchanged.',
  },
  official_transcribed: {
    label: 'Official · transcribed', cls: 'border-sky-200 bg-sky-50 text-sky-800', icon: FileSearch,
    tip: 'Official value transcribed from a published figure or PDF text (no Excel table exists). Rounded as printed.',
  },
  calculated: {
    label: 'Calculated', cls: 'border-violet-200 bg-violet-50 text-violet-800', icon: Calculator,
    tip: 'Derived by Imboni from official values. The formula is shown alongside.',
  },
  illustrative: {
    label: 'Illustrative', cls: 'border-amber-300 bg-amber-50 text-amber-900', icon: Lightbulb,
    tip: 'Depends on user or placeholder assumptions. Not an official statistic or forecast.',
  },
  experimental: {
    label: 'Experimental', cls: 'border-rose-200 bg-rose-50 text-rose-800', icon: FlaskConical,
    tip: 'Imboni research method, not an official measure. Formula and validation are published.',
  },
}

export function StatusBadge({ status, className }: { status: Status; className?: string }) {
  const s = STATUS[status] ?? STATUS.official
  const Icon = s.icon
  return (
    <span className={clsx('chip', s.cls, className)} title={s.tip}>
      <Icon size={11} aria-hidden /> {s.label}
    </span>
  )
}

/* ------------------------------------------------------------------ tooltip */
export function InfoTip({ children, label = 'More information', className, wide }: {
  children: ReactNode; label?: string; className?: string; wide?: boolean
}) {
  const [open, setOpen] = useState(false)
  const id = useId()
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    const onDoc = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onDoc)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onDoc) }
  }, [open])
  return (
    <span ref={ref} className={clsx('relative inline-flex align-middle', className)}
      onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={label} aria-describedby={open ? id : undefined} aria-expanded={open}
        onClick={() => setOpen((o) => !o)} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
        className="rounded-full p-0.5 text-muted hover:text-brand-600">
        <Info size={14} aria-hidden />
      </button>
      {open && (
        <span role="tooltip" id={id}
          className={clsx('absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 rounded-xl border border-line bg-ink-900 px-3 py-2.5 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-white/90 shadow-[var(--shadow-lift)]',
            wide ? 'w-80' : 'w-64')}>
          {children}
        </span>
      )}
    </span>
  )
}

/* ------------------------------------------------------------------ source */
export function SourceLink({ source, table, className }: { source: SourceRef; table?: string; className?: string }) {
  return (
    <a href={source.landing_page || source.url} target="_blank" rel="noreferrer"
      className={clsx('inline-flex items-center gap-1 text-[11px] text-muted hover:text-brand-600', className)}>
      <span className="truncate">{source.short}{table ? ` · ${table}` : ''}</span>
      <ExternalLink size={10} aria-hidden className="shrink-0" />
      <span className="sr-only">(opens official source in a new tab)</span>
    </a>
  )
}

/* ------------------------------------------------------------------ layout */
export function PageHeader({ eyebrow, title, children, actions }: {
  eyebrow: string; title: ReactNode; children?: ReactNode; actions?: ReactNode
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-3xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="h-display mt-2 text-3xl font-semibold text-ink-900 sm:text-4xl">{title}</h1>
        {children && <div className="mt-3 text-[15px] leading-relaxed text-text-2">{children}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2 no-print">{actions}</div>}
    </div>
  )
}

export function Card({ children, className, as: As = 'section' }: { children: ReactNode; className?: string; as?: 'section' | 'div' | 'article' }) {
  return <As className={clsx('card card-pad', className)}>{children}</As>
}

export function CardTitle({ title, subtitle, right, info }: { title: ReactNode; subtitle?: ReactNode; right?: ReactNode; info?: ReactNode }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="flex items-center gap-1.5 text-[15px] font-semibold text-ink-900">
          {title}
          {info && <InfoTip wide>{info}</InfoTip>}
        </h2>
        {subtitle && <p className="mt-0.5 text-xs leading-relaxed text-muted">{subtitle}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  )
}

export function Callout({ tone = 'info', title, children, className }: {
  tone?: 'info' | 'warn' | 'note'; title?: ReactNode; children: ReactNode; className?: string
}) {
  const styles = {
    info: 'border-brand-200 bg-brand-50/70 text-brand-800',
    warn: 'border-amber-300 bg-amber-50 text-amber-900',
    note: 'border-line bg-paper text-text-2',
  }[tone]
  const Icon = tone === 'warn' ? AlertTriangle : Info
  return (
    <div className={clsx('flex gap-3 rounded-2xl border px-4 py-3 text-[13px] leading-relaxed', styles, className)}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden />
      <div>{title && <p className="mb-0.5 font-semibold">{title}</p>}{children}</div>
    </div>
  )
}

/* ------------------------------------------------------------------ states */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton', className)} aria-hidden />
}

export function LoadingBlock({ rows = 3, label = 'Loading data' }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className={clsx('h-24', i % 2 ? 'w-full' : 'w-11/12')} />)}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: { message: string } | null; onRetry?: () => void }) {
  return (
    <div role="alert" className="card card-pad flex flex-col items-start gap-3 border-rose-200 bg-rose-50/50">
      <div className="flex items-center gap-2 font-semibold text-rose-800"><AlertTriangle size={16} /> Something went wrong</div>
      <p className="text-sm text-rose-900/80">{error?.message ?? 'Unknown error'}</p>
      {onRetry && <button className="btn-ghost btn-sm" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-line-strong px-6 py-10 text-center">
      <Inbox size={22} className="text-muted" aria-hidden />
      <p className="font-semibold text-ink-900">{title}</p>
      {children && <div className="max-w-md text-sm text-text-2">{children}</div>}
    </div>
  )
}

/* ------------------------------------------------------------------ controls */
export function Segmented<T extends string>({ value, onChange, options, label, size = 'md' }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; label: string; size?: 'sm' | 'md'
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-full border border-line-strong bg-white p-0.5">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={clsx('rounded-full font-semibold transition-colors', size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3.5 py-1.5 text-xs',
            value === o.value ? 'bg-ink-900 text-white' : 'text-text-2 hover:text-ink-900')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Field({ label, children, hint, htmlFor }: { label: string; children: ReactNode; hint?: ReactNode; htmlFor?: string }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-xs font-semibold text-text-2">{label}</label>
      {children}
      {hint && <p className="text-[11px] leading-relaxed text-muted">{hint}</p>}
    </div>
  )
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string; icon?: typeof Info }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div role="tablist" aria-label="Sections" className="flex gap-1 overflow-x-auto border-b border-line no-print">
      {tabs.map((t) => {
        const Icon = t.icon
        return (
          <button key={t.id} role="tab" type="button" aria-selected={value === t.id} onClick={() => onChange(t.id)}
            className={clsx('-mb-px flex items-center gap-2 whitespace-nowrap border-b-2 px-3.5 py-2.5 text-sm font-semibold transition-colors',
              value === t.id ? 'border-brand-600 text-ink-900' : 'border-transparent text-muted hover:text-ink-900')}>
            {Icon && <Icon size={15} aria-hidden />} {t.label}
          </button>
        )
      })}
    </div>
  )
}

export function Flag({ flag }: { flag: string }) {
  const map: Record<string, string> = {
    cv_gt_15_use_with_caution: 'CV > 15%: use with caution',
    cv_gt_30_unreliable: 'CV > 30%: unreliable',
    ci_upper_above_100_normal_approx: 'CI upper bound > 100% (normal approximation)',
    se_zero_no_sampling_variation: 'SE = 0 in source',
    unlabelled_segment_in_source_figure: 'Unlabelled in source figure — kept missing',
    merged_pdf_labels_resolved_visually: 'PDF labels merged — verified visually',
    urban_rural_2012_definition: '2012 urban/rural definition',
    suppressed_or_no_observations_in_source: "'-' in source (no observations)",
  }
  const text = map[flag]
  if (!text) return null
  return <span className="chip border-amber-200 bg-amber-50 text-amber-900">{text}</span>
}
