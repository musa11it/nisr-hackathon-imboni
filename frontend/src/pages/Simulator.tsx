import clsx from 'clsx'
import { AlertTriangle, Bath, Download, Droplets, FileText, Flame, GitCompareArrows, GraduationCap, HeartPulse, Home, Landmark, RotateCcw, Save, Scale, Sparkles, Trash2, Zap } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Callout, Card, CardTitle, EmptyState, ErrorState, Field, InfoTip, LoadingBlock, PageHeader, StatusBadge } from '../components/ui'
import { ApiError, apiFetch, downloadPost, useApi } from '../lib/api'
import { int, pct, rwf } from '../lib/format'
import type { FeatureCollection } from '../lib/types'

interface CatItem { id: string; label: string; icon: string; need_label: string; default_unit_cost: number; default_share: number; proxy_note: string | null }
interface Need { rate_pct: number | null; eligible_households: number | null; level_used: string | null; geo_used?: string; fallback: boolean }
interface Ctx { name: string; households: number; household_size: number; needs: Record<string, Need> }
interface Line {
  id: string; label: string; share_pct: number; amount_rwf: number; unit_cost_rwf: number; capacity_households: number
  eligible_households: number | null; need_rate_pct: number | null; need_label: string; need_basis: Need
  households_reached: number; people_reached_est: number | null; coverage_of_need_pct: number | null
  amount_used_rwf: number; amount_idle_rwf: number; budget_exceeds_need: boolean; proxy_note: string | null
  unit_cost_is_default: boolean; sensitivity: { multiplier: number; unit_cost_rwf: number; households_reached: number; coverage_pct: number | null }[]
}
interface Result {
  name: string; context: Ctx; lines: Line[]
  summary: { total_budget_rwf: number; allocated_rwf: number; unallocated_rwf: number; allocated_pct: number; reconciles: boolean; household_interventions: number; people_reached_est_sum: number; idle_rwf: number; max_unique_households_bound: number }
  labels: Record<string, string>
}
interface Saved { id: number; name: string; created_at: string; summary: Result['summary'] & { geography: string }; inputs: Payload }
interface Payload { name: string; total_budget_rwf: number; geography: { level: string; geo_id: string }; interventions: { id: string; share_pct: number; unit_cost_rwf: number }[] }
type LineState = Record<string, { enabled: boolean; share: number; cost: number }>

const ICONS: Record<string, typeof Home> = { home: Home, flame: Flame, droplets: Droplets, zap: Zap, bath: Bath, 'heart-pulse': HeartPulse, landmark: Landmark, 'graduation-cap': GraduationCap }
const PRESETS = [1e9, 5e9, 10e9, 50e9]
const TOKENS_KEY = 'imboni.scenarioTokens'

// Deletion tokens for scenarios saved from this browser (returned once by the API, never shown).
function readTokens(): Record<string, string> {
  try { return JSON.parse(localStorage.getItem(TOKENS_KEY) ?? '{}') } catch { return {} }
}
function writeTokens(t: Record<string, string>) {
  try { localStorage.setItem(TOKENS_KEY, JSON.stringify(t)) } catch { /* storage unavailable: delete stays disabled */ }
}

function defaults(cat: CatItem[]): LineState {
  return Object.fromEntries(cat.map((c) => [c.id, { enabled: c.default_share > 0, share: c.default_share, cost: c.default_unit_cost }]))
}

export default function Simulator() {
  const [params] = useSearchParams()
  const cat = useApi<CatItem[]>('/api/simulator/catalogue')
  const districts = useApi<FeatureCollection>('/api/geo/district')
  const provinces = useApi<FeatureCollection>('/api/geo/province')

  const [name, setName] = useState('My scenario')
  const [budget, setBudget] = useState(10_000_000_000)
  const [geo, setGeo] = useState({ level: params.get('level') || 'national', geo_id: params.get('geo') || 'rwanda' })
  const [lines, setLines] = useState<LineState>({})
  const [result, setResult] = useState<Result | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState<Saved[]>([])
  const [savedError, setSavedError] = useState<string | null>(null)
  const [compare, setCompare] = useState<number[]>([])
  const [toast, setToast] = useState<string | null>(null)
  const [tokens, setTokens] = useState<Record<string, string>>(readTokens)

  useEffect(() => { if (cat.data && Object.keys(lines).length === 0) setLines(defaults(cat.data)) }, [cat.data, lines])
  const ctx = useApi<Ctx>(`/api/simulator/context/${geo.level}/${geo.geo_id}`)

  const enabled = useMemo(() => (cat.data ?? []).filter((c) => lines[c.id]?.enabled), [cat.data, lines])
  const totalShare = enabled.reduce((s, c) => s + (lines[c.id]?.share || 0), 0)
  const errors: string[] = []
  if (!(budget > 0)) errors.push('Total budget must be greater than zero.')
  if (budget > 1e13) errors.push('Total budget exceeds the RWF 10 trillion ceiling.')
  if (totalShare > 100.0001) errors.push(`Allocations sum to ${totalShare.toFixed(2)}% — reduce them to 100% or less.`)
  if (enabled.length === 0) errors.push('Enable at least one intervention.')
  enabled.forEach((c) => {
    const l = lines[c.id]
    if (l.share < 0 || l.share > 100) errors.push(`${c.label}: share must be between 0 and 100%.`)
    if (!(l.cost >= 1)) errors.push(`${c.label}: unit cost must be at least RWF 1.`)
  })

  const payload: Payload = useMemo(() => ({
    name: name.trim() || 'Untitled scenario', total_budget_rwf: budget, geography: geo,
    interventions: enabled.map((c) => ({ id: c.id, share_pct: lines[c.id].share, unit_cost_rwf: lines[c.id].cost })),
  }), [name, budget, geo, enabled, lines])

  useEffect(() => {
    if (errors.length || !cat.data) return
    const t = setTimeout(() => {
      setBusy(true)
      apiFetch<Result>('/api/simulator/run', { method: 'POST', body: JSON.stringify(payload) })
        .then((r) => { setResult(r); setRunError(null) })
        .catch((e: ApiError) => setRunError(e.message))
        .finally(() => setBusy(false))
    }, 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(payload), errors.length, cat.data])

  const loadSaved = useCallback(() => {
    apiFetch<Saved[]>('/api/scenarios').then((s) => { setSaved(s); setSavedError(null) }).catch((e: ApiError) => setSavedError(e.message))
  }, [])
  useEffect(loadSaved, [loadSaved])

  const flash = (m: string) => { setToast(m); setTimeout(() => setToast(null), 2600) }
  const update = (id: string, patch: Partial<LineState[string]>) => setLines((ls) => ({ ...ls, [id]: { ...ls[id], ...patch } }))

  const splitEven = () => {
    const n = enabled.length
    if (!n) return
    const base = Math.floor((100 / n) * 100) / 100
    setLines((ls) => {
      const next = { ...ls }
      enabled.forEach((c, i) => { next[c.id] = { ...next[c.id], share: i === n - 1 ? +(100 - base * (n - 1)).toFixed(2) : base } })
      return next
    })
  }
  const needSplit = async () => {
    try {
      const r = await apiFetch<{ shares: Record<string, number> }>(`/api/simulator/suggest/${geo.level}/${geo.geo_id}?ids=${enabled.map((c) => c.id).join(',')}`)
      setLines((ls) => { const n = { ...ls }; Object.entries(r.shares).forEach(([k, v]) => { n[k] = { ...n[k], share: v } }); return n })
      flash('Shares set in proportion to each intervention’s measured need rate.')
    } catch (e) { flash((e as Error).message) }
  }
  const save = async () => {
    try {
      const r = await apiFetch<{ id: number; delete_token: string }>('/api/scenarios', { method: 'POST', body: JSON.stringify(payload) })
      const next = { ...tokens, [r.id]: r.delete_token }
      setTokens(next); writeTokens(next)
      loadSaved(); flash('Scenario saved.')
    } catch (e) { flash((e as Error).message) }
  }
  const remove = async (id: number) => {
    try {
      await apiFetch(`/api/scenarios/${id}`, { method: 'DELETE', headers: { 'X-Scenario-Token': tokens[id] ?? '' } })
      const next = { ...tokens }; delete next[id]
      setTokens(next); writeTokens(next)
      setCompare((c) => c.filter((x) => x !== id)); loadSaved()
    } catch (e) { flash((e as Error).message) }
  }
  const load = (s: Saved) => {
    setName(s.inputs.name); setBudget(s.inputs.total_budget_rwf); setGeo(s.inputs.geography)
    setLines((ls) => {
      const n: LineState = Object.fromEntries(Object.entries(ls).map(([k, v]) => [k, { ...v, enabled: false }]))
      s.inputs.interventions.forEach((i) => { n[i.id] = { enabled: true, share: i.share_pct, cost: i.unit_cost_rwf } })
      return n
    })
    flash(`Loaded “${s.name}”.`)
  }
  const exportAs = async (format: 'csv' | 'pdf') => {
    try { await downloadPost(`/api/simulator/export?format=${format}`, payload, `imboni_scenario.${format}`) } catch (e) { flash((e as Error).message) }
  }

  if (cat.error) return <div className="mx-auto max-w-[1320px] px-4 py-10"><ErrorState error={cat.error} onRetry={cat.reload} /></div>
  if (!cat.data || Object.keys(lines).length === 0) return <div className="mx-auto max-w-[1320px] px-4 py-10"><LoadingBlock rows={4} /></div>

  const s = result?.summary
  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Intervention budget simulator" title="What could a budget reach?"
        actions={<>
          <button className="btn-ghost" onClick={() => exportAs('csv')} disabled={!!errors.length}><Download size={15} /> CSV</button>
          <button className="btn-ghost" onClick={() => exportAs('pdf')} disabled={!!errors.length}><FileText size={15} /> PDF</button>
          <button className="btn-primary" onClick={save} disabled={!!errors.length}><Save size={15} /> Save scenario</button>
        </>}>
        Allocate a hypothetical budget across interventions and see how many households it could pay for, measured against the official deprivation
        data for the area you target. <strong>This is budget arithmetic, not a forecast</strong>: it does not estimate changes in poverty or the MPI.
      </PageHeader>

      <Callout tone="warn" title="Illustrative scenario" className="mb-6">
        Default unit costs are placeholders chosen by the DataMinds team to make the tool usable — <strong>not costed programme estimates</strong>. Replace them
        with real programme costing. Households counts come from the 2022 Census; need rates from EICV7/FinScope as shown for each line.
      </Callout>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,440px)_1fr]">
        {/* -------------------------------------------------- controls */}
        <div className="space-y-6">
          <Card>
            <CardTitle title="Scenario" />
            <div className="space-y-4">
              <Field label="Scenario name" htmlFor="sc-name">
                <input id="sc-name" className="input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <Field label="Total budget (RWF)" htmlFor="sc-budget" hint={`${rwf(budget, true)} · whole Rwandan francs`}>
                <input id="sc-budget" className="input tabular" inputMode="numeric" value={budget ? budget.toLocaleString('en-GB') : ''}
                  onChange={(e) => { const v = Number(e.target.value.replace(/[^0-9]/g, '')); setBudget(Number.isFinite(v) ? v : 0) }}
                  aria-invalid={!(budget > 0)} />
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {PRESETS.map((p) => <button key={p} type="button" className={clsx('chip', budget === p ? 'border-ink-900 bg-ink-900 text-white' : 'border-line-strong bg-white text-text-2 hover:bg-paper')} onClick={() => setBudget(p)}>{rwf(p, true).replace('RWF ', '')}</button>)}
                </div>
              </Field>
              <Field label="Target geography" htmlFor="sc-geo" hint={ctx.data ? `${int(ctx.data.households)} private households · ${ctx.data.household_size} persons/household (Census 2022)` : 'Loading…'}>
                <select id="sc-geo" className="input" value={`${geo.level}/${geo.geo_id}`} onChange={(e) => { const [level, geo_id] = e.target.value.split('/'); setGeo({ level, geo_id }) }}>
                  <option value="national/rwanda">Rwanda (national)</option>
                  <optgroup label="Provinces">{provinces.data?.features.map((f) => <option key={f.properties.geo_id} value={`province/${f.properties.geo_id}`}>{f.properties.name}</option>)}</optgroup>
                  <optgroup label="Districts">{[...(districts.data?.features ?? [])].sort((a, b) => a.properties.name.localeCompare(b.properties.name)).map((f) => <option key={f.properties.geo_id} value={`district/${f.properties.geo_id}`}>{f.properties.name}</option>)}</optgroup>
                </select>
              </Field>
            </div>
          </Card>

          <Card>
            <CardTitle title="Allocation" subtitle="Shares of the total budget. Amounts always reconcile to the budget (whole RWF)."
              right={<button className="btn-ghost btn-sm" onClick={() => setLines(defaults(cat.data!))}><RotateCcw size={12} /> Reset</button>} />
            <div className="mb-4">
              <div className="flex items-center justify-between text-[12px]">
                <span className="font-semibold text-text-2">Allocated</span>
                <span className={clsx('tabular font-semibold', totalShare > 100.0001 ? 'text-[#d03b3b]' : 'text-ink-900')}>
                  {totalShare.toFixed(2)}% · remaining {Math.max(0, 100 - totalShare).toFixed(2)}%
                </span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-paper-2" role="progressbar" aria-valuenow={Math.round(totalShare)} aria-valuemin={0} aria-valuemax={100} aria-label="Share of budget allocated">
                <div className={clsx('h-full rounded-full transition-all', totalShare > 100.0001 ? 'bg-[#d03b3b]' : 'bg-brand-500')} style={{ width: `${Math.min(100, totalShare)}%` }} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-ghost btn-sm" onClick={splitEven}><Scale size={12} /> Split evenly</button>
                <button className="btn-ghost btn-sm" onClick={needSplit}><Sparkles size={12} /> Need-weighted split</button>
                <InfoTip>Need-weighted split sets each enabled line's share in proportion to its measured need rate in the target area (e.g. % of households without improved water). A transparent default — not an optimisation.</InfoTip>
              </div>
            </div>
            <ul className="space-y-3">
              {cat.data.map((c) => {
                const l = lines[c.id]
                const Icon = ICONS[c.icon] ?? Home
                const need = ctx.data?.needs[c.id]
                return (
                  <li key={c.id} className={clsx('rounded-2xl border p-3 transition-colors', l.enabled ? 'border-line-strong bg-white' : 'border-line bg-paper/60')}>
                    <div className="flex items-center gap-3">
                      <input type="checkbox" id={`en-${c.id}`} checked={l.enabled} onChange={(e) => update(c.id, { enabled: e.target.checked })} className="h-4 w-4 accent-[#0f6e64]" />
                      <Icon size={16} className={l.enabled ? 'text-brand-600' : 'text-muted'} aria-hidden />
                      <label htmlFor={`en-${c.id}`} className={clsx('flex-1 text-[13px] font-semibold', l.enabled ? 'text-ink-900' : 'text-muted')}>{c.label}</label>
                      {need?.rate_pct != null && <span className="tabular text-[11px] text-muted" title={c.need_label}>need {pct(need.rate_pct)}</span>}
                    </div>
                    {l.enabled && (
                      <div className="mt-3 grid grid-cols-[1fr_6rem] gap-x-3 gap-y-2 pl-7">
                        <input type="range" min={0} max={100} step={0.5} value={l.share} aria-label={`${c.label} share`} onChange={(e) => update(c.id, { share: Number(e.target.value) })} className="accent-[#0f6e64]" />
                        <div className="relative">
                          <input className="input tabular !py-1 pr-6 text-right" type="number" min={0} max={100} step={0.5} value={l.share} aria-label={`${c.label} share percent`}
                            onChange={(e) => update(c.id, { share: Math.max(0, Number(e.target.value)) })} />
                          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted">%</span>
                        </div>
                        <label className="self-center text-[11px] text-text-2" htmlFor={`cost-${c.id}`}>Unit cost per household (RWF)
                          {l.cost === c.default_unit_cost && <span className="ml-1.5 chip border-amber-300 bg-amber-50 text-amber-900">placeholder</span>}</label>
                        <input id={`cost-${c.id}`} className="input tabular !py-1 text-right" inputMode="numeric" value={l.cost.toLocaleString('en-GB')}
                          onChange={(e) => update(c.id, { cost: Number(e.target.value.replace(/[^0-9]/g, '')) || 0 })} />
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
            {errors.length > 0 && (
              <div role="alert" className="mt-4 space-y-1 rounded-xl border border-rose-200 bg-rose-50 p-3 text-[12.5px] text-rose-900">
                {errors.map((e) => <p key={e} className="flex gap-2"><AlertTriangle size={14} className="mt-0.5 shrink-0" />{e}</p>)}
              </div>
            )}
          </Card>
        </div>

        {/* -------------------------------------------------- results */}
        <div className="space-y-6" aria-live="polite">
          {runError && <ErrorState error={{ message: runError }} />}
          {!result && !runError && <LoadingBlock rows={3} label="Calculating scenario" />}
          {result && s && (
            <>
              <div className={clsx('grid gap-4 sm:grid-cols-2 lg:grid-cols-4 transition-opacity', busy && 'opacity-60')}>
                {[
                  ['Allocated', rwf(s.allocated_rwf, true), `${s.allocated_pct.toFixed(2)}% of ${rwf(s.total_budget_rwf, true)}`],
                  ['Unallocated (remaining)', rwf(s.unallocated_rwf, true), s.reconciles ? 'Budget reconciles exactly ✓' : 'Reconciliation failed'],
                  ['Household-interventions', int(s.household_interventions), `Unique households: between ${int(s.max_unique_households_bound)} and ${int(s.household_interventions)}`],
                  ['People in reached households', int(s.people_reached_est_sum), 'Estimate: households × Census household size; may double-count'],
                ].map(([l, v, d]) => (
                  <div key={l} className="card p-5">
                    <p className="text-[12px] font-semibold text-text-2">{l}</p>
                    <p className="tabular mt-2 whitespace-nowrap text-xl font-semibold text-ink-900 2xl:text-2xl">{v}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted">{d}</p>
                  </div>
                ))}
              </div>

              <Card>
                <CardTitle title={`Reach and coverage in ${result.context.name}`} subtitle="Coverage = households reached ÷ households estimated to lack the service. Reach is capped at measured need."
                  right={<StatusBadge status="illustrative" />} />
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-[13px]">
                    <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
                      <th className="py-2 pr-3">Intervention</th><th className="py-2 pr-3 text-right">Amount</th><th className="py-2 pr-3 text-right">Eligible HH</th>
                      <th className="py-2 pr-3 text-right">HH reached</th><th className="w-[24%] py-2 pr-3">Coverage of need</th><th className="py-2 text-right">Idle funds</th>
                    </tr></thead>
                    <tbody>
                      {result.lines.map((l) => (
                        <tr key={l.id} className="border-b border-line/70 align-top">
                          <td className="py-2.5 pr-3">
                            <p className="font-semibold text-ink-900">{l.label}</p>
                            <p className="mt-0.5 text-[11px] leading-snug text-muted">{l.share_pct}% · {rwf(l.unit_cost_rwf)}/household
                              {l.need_basis.fallback && <span className="ml-1 chip border-amber-200 bg-amber-50 text-amber-900">need measured at {l.need_basis.level_used}</span>}</p>
                          </td>
                          <td className="tabular py-2.5 pr-3 text-right">{rwf(l.amount_rwf, true)}</td>
                          <td className="tabular py-2.5 pr-3 text-right">{int(l.eligible_households)}<p className="text-[11px] text-muted">{pct(l.need_rate_pct)} need</p></td>
                          <td className="tabular py-2.5 pr-3 text-right font-semibold">{int(l.households_reached)}</td>
                          <td className="py-2.5 pr-3">
                            <div className="flex items-center gap-2">
                              <div className="h-2 flex-1 overflow-hidden rounded-full bg-paper-2"><div className="h-full rounded-full bg-brand-500" style={{ width: `${Math.min(100, l.coverage_of_need_pct ?? 0)}%` }} /></div>
                              <span className="tabular w-12 text-right text-[12px] font-semibold">{pct(l.coverage_of_need_pct)}</span>
                            </div>
                            {l.budget_exceeds_need && <p className="mt-1 text-[11px] text-amber-800">Budget exceeds measured need at this unit cost.</p>}
                          </td>
                          <td className="tabular py-2.5 text-right text-text-2">{rwf(l.amount_idle_rwf, true)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <details className="mt-4 text-[12px] text-text-2">
                  <summary className="cursor-pointer font-semibold text-ink-900">Need basis and assumptions for each line</summary>
                  <ul className="mt-2 space-y-2">
                    {result.lines.map((l) => (
                      <li key={l.id}><strong>{l.label}:</strong> {l.need_label}. Measured at {l.need_basis.geo_used} ({l.need_basis.level_used}){l.need_basis.fallback ? ' — not published for the selected area, so the nearest published level is applied' : ''}.{l.proxy_note ? ` ${l.proxy_note}` : ''}</li>
                    ))}
                  </ul>
                </details>
              </Card>

              <Card>
                <CardTitle title="Sensitivity to unit costs" subtitle="Households reached if every unit cost were multiplied by the factor shown (budget unchanged)." right={<StatusBadge status="illustrative" />} />
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[560px] text-[13px]">
                    <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted"><th className="py-2 pr-3 text-left">Intervention</th>
                      {result.lines[0]?.sensitivity.map((x) => <th key={x.multiplier} className={clsx('py-2 pr-3 text-right', x.multiplier === 1 && 'text-ink-900')}>cost ×{x.multiplier}</th>)}</tr></thead>
                    <tbody>{result.lines.map((l) => (
                      <tr key={l.id} className="border-b border-line/70">
                        <td className="py-2 pr-3 font-semibold text-ink-900">{l.label}</td>
                        {l.sensitivity.map((x) => <td key={x.multiplier} className={clsx('tabular py-2 pr-3 text-right', x.multiplier === 1 ? 'font-semibold text-ink-900' : 'text-text-2')}>{int(x.households_reached)}</td>)}
                      </tr>))}</tbody>
                  </table>
                </div>
              </Card>

              <Callout tone="note">
                <p><strong>Households reached vs people reached vs poverty reduction.</strong> {result.labels.reach_definition} People are estimated as households × the
                  Census mean household size. {result.labels.not_measured}</p>
              </Callout>
            </>
          )}

          <Card>
            <CardTitle title="Saved scenarios" subtitle="Stored in the Imboni database and visible to all users of this instance. Only the browser that saved a scenario can delete it. Tick up to three to compare."
              right={compare.length > 0 && <button className="btn-ghost btn-sm" onClick={() => setCompare([])}>Clear selection</button>} />
            {savedError ? <p className="text-sm text-rose-800">{savedError}</p> : saved.length === 0 ? (
              <EmptyState title="No saved scenarios yet">Adjust the allocation and press “Save scenario”.</EmptyState>
            ) : (
              <ul className="divide-y divide-line">
                {saved.map((sv) => (
                  <li key={sv.id} className="flex flex-wrap items-center gap-3 py-2.5">
                    <input type="checkbox" aria-label={`Compare ${sv.name}`} className="h-4 w-4 accent-[#0f6e64]" checked={compare.includes(sv.id)}
                      disabled={!compare.includes(sv.id) && compare.length >= 3}
                      onChange={(e) => setCompare((c) => e.target.checked ? [...c, sv.id] : c.filter((x) => x !== sv.id))} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-semibold text-ink-900">{sv.name}</p>
                      <p className="text-[11px] text-muted">{sv.summary.geography} · {rwf(sv.summary.total_budget_rwf, true)} · {new Date(sv.created_at).toLocaleString('en-GB')}</p>
                    </div>
                    <button className="btn-ghost btn-sm" onClick={() => load(sv)}>Load</button>
                    {tokens[sv.id] && <button className="btn-ghost btn-sm" aria-label={`Delete ${sv.name}`} onClick={() => remove(sv.id)}><Trash2 size={12} /></button>}
                  </li>
                ))}
              </ul>
            )}
            {compare.length >= 2 && (
              <div className="mt-5 overflow-x-auto border-t border-line pt-4">
                <p className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-ink-900"><GitCompareArrows size={15} /> Side-by-side comparison</p>
                <table className="w-full min-w-[520px] text-[13px]">
                  <thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-muted"><th className="py-2 pr-3">Metric</th>
                    {compare.map((id) => <th key={id} className="py-2 pr-3">{saved.find((x) => x.id === id)?.name}</th>)}</tr></thead>
                  <tbody>
                    {([['Geography', (x: Saved) => x.summary.geography], ['Total budget', (x: Saved) => rwf(x.summary.total_budget_rwf, true)],
                      ['Allocated', (x: Saved) => `${x.summary.allocated_pct.toFixed(1)}%`], ['Unallocated', (x: Saved) => rwf(x.summary.unallocated_rwf, true)],
                      ['Household-interventions', (x: Saved) => int(x.summary.household_interventions)], ['People in reached HH (est.)', (x: Saved) => int(x.summary.people_reached_est_sum)],
                      ['Idle funds', (x: Saved) => rwf(x.summary.idle_rwf, true)],
                      ['Interventions', (x: Saved) => x.inputs.interventions.map((i) => `${i.id.replace('_', ' ')} ${i.share_pct}%`).join(', ')]] as [string, (x: Saved) => string][]).map(([label, f]) => (
                      <tr key={label} className="border-b border-line/70"><td className="py-2 pr-3 font-semibold text-text-2">{label}</td>
                        {compare.map((id) => { const x = saved.find((y) => y.id === id); return <td key={id} className="tabular py-2 pr-3">{x ? f(x) : '—'}</td> })}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
      {toast && <div role="status" className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-ink-900 px-4 py-2 text-sm text-white shadow-[var(--shadow-lift)]">{toast}</div>}
    </div>
  )
}
