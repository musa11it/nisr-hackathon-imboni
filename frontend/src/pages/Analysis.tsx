import clsx from 'clsx'
import { BrainCircuit, CheckCircle2, FlaskConical, GitBranch, LineChart as LineIcon, ShieldCheck, TriangleAlert, Waypoints } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { Legend } from '../components/charts'
import { Callout, Card, CardTitle, ErrorState, Flag, LoadingBlock, PageHeader, StatusBadge, Tabs } from '../components/ui'
import { useApi } from '../lib/api'
import { DIVERGING, diverging, INK, SERIES } from '../lib/colors'
import { pct, pp, r2 } from '../lib/format'
import type { IndicatorMeta, Metric } from '../lib/types'

type Tab = 'validation' | 'correlations' | 'mpi' | 'trends' | 'composite'

export default function Analysis() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as Tab) || 'validation'
  const setTab = (t: Tab) => setParams({ tab: t }, { replace: true })
  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Explainable statistical analysis" title="Methods you can check">
        Every statistic here is computed from validated official values with the method stated. Associations are descriptive; nothing on this page
        claims a causal effect.
      </PageHeader>
      <Tabs value={tab} onChange={setTab} tabs={[
        { id: 'validation', label: 'Validation & data quality', icon: ShieldCheck },
        { id: 'correlations', label: 'District associations', icon: Waypoints },
        { id: 'mpi', label: 'MPI deep-dive', icon: GitBranch },
        { id: 'trends', label: 'Trends', icon: LineIcon },
        { id: 'composite', label: 'Experimental index', icon: FlaskConical },
      ]} />
      <div className="mt-6">
        {tab === 'validation' && <Validation />}
        {tab === 'correlations' && <Correlations />}
        {tab === 'mpi' && <MpiDeep />}
        {tab === 'trends' && <Trends />}
        {tab === 'composite' && <Composite />}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ validation */
interface Check { check: string; passed: boolean; detail: string; severity: 'info' | 'warning' | 'error' }
interface DQ {
  n_observations: number; status_counts: Record<string, number>; missing: { indicator_id: string; geo_name: string; flags: string[]; breakdown?: string }[]
  precision_flags: Record<string, number>; flagged_observations: Metric[]; validation: { summary: { total: number; passed: number; errors: number; warnings: number }; checks: Check[]; generated_at: string }
  cv_rule: string
}

function Validation() {
  const { data, error, loading, reload } = useApi<DQ>('/api/analysis/data-quality')
  const [show, setShow] = useState<'issues' | 'all'>('issues')
  if (loading) return <LoadingBlock />
  if (error || !data) return <ErrorState error={error} onRetry={reload} />
  const v = data.validation
  const checks = show === 'issues' ? v.checks.filter((c) => !c.passed || c.check.startsWith('benchmark')) : v.checks
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[['Automated checks passed', `${v.summary.passed}/${v.summary.total}`], ['Pipeline errors', v.summary.errors], ['Source inconsistencies documented', v.summary.warnings], ['Observations', data.n_observations.toLocaleString('en-GB')]].map(([l, x]) => (
          <div key={l as string} className="card p-5"><p className="text-[12px] font-semibold text-text-2">{l}</p><p className="tabular mt-2 text-3xl font-semibold text-ink-900">{x}</p></div>
        ))}
      </div>
      <Callout tone="warn" title="Inconsistency found in an official table">
        The MPI workbook's indicator-contribution tables (B.7–B.9) cannot be reproduced from its own censored headcounts (Table B.2) and the official weights
        (report pp. 22–23) — see the “MPI deep-dive” tab for printed vs recomputed values side by side. Imboni keeps both, labels the recomputed
        version <em>calculated</em>, and flags the check below. The identity Σ w·CH ≈ M0 itself holds within rounding (see “mpi weighted ch sum” checks).
      </Callout>
      <Card>
        <CardTitle title="Validation checks" subtitle={`Generated ${new Date(v.generated_at).toLocaleString('en-GB')} by the pipeline`}
          right={<div className="flex gap-1">{(['issues', 'all'] as const).map((k) => <button key={k} onClick={() => setShow(k)} className={clsx('chip', show === k ? 'border-ink-900 bg-ink-900 text-white' : 'border-line-strong bg-white text-text-2')}>{k === 'issues' ? 'Benchmarks & issues' : 'All checks'}</button>)}</div>} />
        <ul className="divide-y divide-line">
          {checks.map((c) => (
            <li key={c.check} className="flex gap-3 py-2 text-[13px]">
              {c.passed ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#0ca30c]" aria-label="passed" /> : <TriangleAlert size={16} className={clsx('mt-0.5 shrink-0', c.severity === 'error' ? 'text-[#d03b3b]' : 'text-amber-600')} aria-label={c.severity} />}
              <div className="min-w-0"><p className="font-semibold text-ink-900">{c.check.replace(/_/g, ' ')}</p><p className="break-words text-[12px] text-text-2">{c.detail}</p></div>
            </li>
          ))}
        </ul>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle title="Missing values" subtitle="Kept as missing with a reason — never replaced by zero" />
          <ul className="space-y-1.5 text-[13px]">{data.missing.map((m, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2"><span className="font-semibold">{m.indicator_id}</span><span className="text-text-2">{m.geo_name}{m.breakdown ? ` · ${m.breakdown}` : ''}</span>{m.flags.map((f) => <Flag key={f} flag={f} />)}</li>
          ))}</ul>
        </Card>
        <Card>
          <CardTitle title="Precision flags" subtitle={data.cv_rule} />
          <p className="text-[13px] text-text-2">CV &gt; 15%: <strong>{data.precision_flags.cv_gt_15_use_with_caution}</strong> estimates · CV &gt; 30%: <strong>{data.precision_flags.cv_gt_30_unreliable}</strong> estimates.</p>
          <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto pr-2 text-[12px]">{data.flagged_observations.map((o, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2 border-b border-line/60 py-1"><span className="font-semibold">{o.short_name}</span><span className="text-text-2">{o.geo_name}</span><span className="tabular text-muted">CV {o.cv?.toFixed(1)}%</span>{o.flags.map((f) => <Flag key={f} flag={f} />)}</li>
          ))}</ul>
        </Card>
      </div>
      <Callout tone="note" title="Why no machine-learning model?">
        Only aggregate tables are public: 30 districts and 5 provinces. Training a predictive model on 30 rows would overfit and invite misuse, and the
        household microdata needed for a defensible model require authorised access. Imboni therefore uses transparent survey-aware statistics; a microdata
        import workflow is documented for authorised users.
      </Callout>
    </div>
  )
}

/* ------------------------------------------------------------------ correlations */
interface Corr { method: string; indicators: (IndicatorMeta & { n: number })[]; pairs: { a: string; b: string; n: number; rho: number; p_value: number; q_value: number; ci_low: number; ci_high: number }[]; caveats: string[]; data: Record<string, Record<string, number | null>> }

function Correlations() {
  const { data, error, loading, reload } = useApi<Corr>('/api/analysis/correlations')
  const [sel, setSel] = useState<[string, string]>(['poverty_rate', 'electricity_lighting'])
  const names = useMemo(() => Object.fromEntries((data?.indicators ?? []).map((i) => [i.id, i.short_name])), [data])
  if (loading) return <LoadingBlock />
  if (error || !data) return <ErrorState error={error} onRetry={reload} />
  const ids = data.indicators.map((i) => i.id)
  const get = (a: string, b: string) => data.pairs.find((p) => (p.a === a && p.b === b) || (p.a === b && p.b === a))
  const cur = get(...sel)
  const points = Object.keys(data.data[sel[0]] ?? {}).map((g) => ({ g, x: data.data[sel[0]][g], y: data.data[sel[1]]?.[g] })).filter((p) => p.x != null && p.y != null)
  return (
    <div className="space-y-6">
      <Callout tone="warn" title="Associations, not causes">
        <ul className="list-disc space-y-0.5 pl-4">{data.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </Callout>
      <div className="grid gap-6 2xl:grid-cols-[1.3fr_1fr]">
        <Card className="min-w-0">
          <CardTitle title="Spearman correlation matrix — 30 districts" subtitle={data.method} />
          <div className="overflow-x-auto">
            <table className="table-fixed border-separate border-spacing-[2px] text-[10.5px]">
              <thead><tr><th className="w-36" />{ids.map((b) => <th key={b} className="relative h-28 w-8 p-0"><span className="absolute bottom-1 left-1/2 origin-bottom-left -rotate-[55deg] whitespace-nowrap font-medium text-text-2">{names[b]}</span></th>)}</tr></thead>
              <tbody>{ids.map((a) => (
                <tr key={a}><th className="whitespace-nowrap pr-2 text-right font-medium text-text-2">{names[a]}</th>
                  {ids.map((b) => {
                    if (a === b) return <td key={b} className="h-8 w-8 rounded bg-paper-2" />
                    const p = get(a, b)
                    const active = (sel[0] === a && sel[1] === b) || (sel[0] === b && sel[1] === a)
                    return (
                      <td key={b} className="p-0">
                        <button title={p ? `${names[a]} × ${names[b]}: ρ = ${r2(p.rho)}, q = ${p.q_value.toFixed(3)}` : ''} onClick={() => setSel([a, b])}
                          aria-label={`${names[a]} and ${names[b]}: rho ${p?.rho.toFixed(2)}`}
                          className={clsx('tabular flex h-8 w-8 items-center justify-center rounded text-[9.5px] font-semibold', active && 'ring-2 ring-ink-900')}
                          style={{ background: p ? diverging(p.rho) : '#eee', color: p && Math.abs(p.rho) > 0.55 ? '#fff' : INK.primary }}>
                          {p ? (p.q_value < 0.05 ? p.rho.toFixed(1) : '·') : ''}
                        </button>
                      </td>
                    )
                  })}</tr>))}</tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted">
            <span>ρ = −1</span><span className="flex gap-[2px]">{[...DIVERGING].reverse().map((c) => <span key={c} className="h-3 w-5 rounded-sm" style={{ background: c }} />)}</span><span>+1</span>
            <span>· = not significant after FDR (q ≥ 0.05)</span>
          </div>
        </Card>
        <Card className="min-w-0">
          <CardTitle title={`${names[sel[0]]} × ${names[sel[1]]}`} subtitle="Click any matrix cell. Each dot is one district." right={<StatusBadge status="calculated" />} />
          <div className="h-72">
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 12, bottom: 24, left: 0 }}>
                <CartesianGrid stroke={INK.grid} />
                <XAxis type="number" dataKey="x" name={names[sel[0]]} tick={{ fontSize: 11, fill: INK.muted }} label={{ value: names[sel[0]], position: 'bottom', fontSize: 11 }} domain={['auto', 'auto']} />
                <YAxis type="number" dataKey="y" name={names[sel[1]]} tick={{ fontSize: 11, fill: INK.muted }} width={40} domain={['auto', 'auto']} />
                <ZAxis range={[64, 64]} />
                <Tooltip content={({ payload }) => payload?.[0] ? <div className="rounded-xl bg-ink-900 px-3 py-2 text-xs text-white"><strong>{(payload[0].payload as any).g}</strong><br />{(payload[0].payload as any).x?.toFixed(1)} · {(payload[0].payload as any).y?.toFixed(1)}</div> : null} />
                <Scatter isAnimationActive={false} data={points} fill={SERIES.s1} stroke="#fff" strokeWidth={1.5} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          {cur && <p className="text-[13px] leading-relaxed text-text-2">ρ = <strong className="text-ink-900">{r2(cur.rho)}</strong>, 95% CI {r2(cur.ci_low)} to {r2(cur.ci_high)}, n = {cur.n}, p = {cur.p_value.toFixed(4)}, FDR q = {cur.q_value.toFixed(4)}.
            {' '}{cur.q_value < 0.05 ? 'The rank association is unlikely to be chance alone across these districts' : 'No reliable association across these districts'} — it says nothing about causation.</p>}
        </Card>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ MPI deep dive */
interface MpiRow { level: string; geo_id: string; name: string; population_share: number; mpi_incidence: number; mpi_intensity: number; mpi: number; mpi_check_HxA: number; sum_w_ch: number; censored: Record<string, number>; contrib_published: Record<string, number>; contrib_calc: Record<string, number> }
interface Mpi { framework: { indicators: { id: string; label: string; dimension: string; weight: number; weight_label: string; deprived_if: string }[] }; table: MpiRow[]; k_curve: { k: number; incidence: number; intensity: number; mpi: number }[]; overlap: Record<string, any>[]; contribution_note: string }

function MpiDeep() {
  const { data, error, loading, reload } = useApi<Mpi>('/api/mpi')
  if (loading) return <LoadingBlock />
  if (error || !data) return <ErrorState error={error} onRetry={reload} />
  const nat = data.table.find((r) => r.level === 'national')!
  const inds = data.framework.indicators
  const prov = data.table.filter((r) => r.level === 'province')
  const heat = (v: number) => { const t = Math.min(1, v / 40); return `rgba(13, 87, 85, ${0.08 + t * 0.85})` }
  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardTitle title="Sensitivity to the poverty cut-off k" subtitle="NISR Table B.10: incidence H and intensity A as k varies. The official cut-off is k = 33.3%."
            info="As k rises, fewer people qualify as poor (H falls) but those who do are more deprived (A rises). M0 = H × A falls monotonically." />
          <Legend items={[{ label: 'Incidence H (%)', color: SERIES.s1 }, { label: 'Intensity A (%)', color: SERIES.s2 }]} />
          <div className="mt-2 h-72">
            <ResponsiveContainer>
              <LineChart data={data.k_curve} margin={{ top: 24, right: 16, bottom: 20, left: 0 }}>
                <CartesianGrid stroke={INK.grid} />
                <XAxis dataKey="k" tick={{ fontSize: 11, fill: INK.muted }} label={{ value: 'Poverty cut-off k (%)', position: 'bottom', fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11, fill: INK.muted }} width={36} domain={[0, 100]} />
                <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} formatter={(v: any, n: any) => [`${Number(v).toFixed(1)}%`, n]} labelFormatter={(k) => `k = ${k}%`} />
                <ReferenceLine x={33} stroke={INK.primary} strokeDasharray="4 3" label={{ value: 'official', fontSize: 10, position: 'top' }} />
                <Line isAnimationActive={false} dataKey="incidence" name="Incidence H" stroke={SERIES.s1} strokeWidth={2} dot={{ r: 3 }} />
                <Line isAnimationActive={false} dataKey="intensity" name="Intensity A" stroke={SERIES.s2} strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardTitle title="Contribution of each indicator to the national MPI" subtitle="Recomputed (w·CH/M0, calculated) vs as printed in Table B.7 (official)" />
          <Legend items={[{ label: 'Recomputed', color: SERIES.s1 }, { label: 'Printed in Table B.7', color: SERIES.s2 }]} />
          <ul className="mt-3 space-y-1.5">
            {[...inds].sort((a, b) => nat.contrib_calc[b.id] - nat.contrib_calc[a.id]).map((i) => (
              <li key={i.id} className="grid grid-cols-[8.5rem_1fr_5.5rem] items-center gap-2 text-[12px]">
                <span className="truncate text-text-2">{i.label}</span>
                <span className="space-y-[2px]">
                  <span className="block h-2 rounded-r" style={{ width: `${nat.contrib_calc[i.id] * 4}%`, background: SERIES.s1 }} />
                  <span className="block h-2 rounded-r" style={{ width: `${nat.contrib_published[i.id] * 4}%`, background: SERIES.s2 }} />
                </span>
                <span className="tabular text-right text-text-2">{nat.contrib_calc[i.id].toFixed(1)} / {nat.contrib_published[i.id].toFixed(1)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-muted">{data.contribution_note}</p>
        </Card>
      </div>
      <Card>
        <CardTitle title="Censored headcounts by province (% MPI-poor and deprived)" subtitle="NISR MPI Table B.3. Darker = higher share. Weights from the official framework." right={<StatusBadge status="official" />} />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-separate border-spacing-[2px] text-[12px]">
            <thead><tr><th className="text-left text-[11px] text-muted">Indicator (weight)</th>{[nat, ...prov].map((r) => <th key={r.geo_id} className="px-1 text-[11px] font-semibold text-text-2">{r.name.replace(' Province', '')}</th>)}</tr></thead>
            <tbody>{inds.map((i) => (
              <tr key={i.id}><td className="whitespace-nowrap pr-2 text-text-2">{i.label} <span className="text-muted">({i.weight_label})</span></td>
                {[nat, ...prov].map((r) => { const v = r.censored[i.id]; return <td key={r.geo_id} className="tabular rounded py-1.5 text-center font-semibold" style={{ background: heat(v), color: v > 22 ? '#fff' : INK.primary }}>{v.toFixed(1)}</td> })}
              </tr>))}
              <tr><td className="pr-2 pt-2 font-semibold text-ink-900">MPI (M0)</td>{[nat, ...prov].map((r) => <td key={r.geo_id} className="tabular pt-2 text-center font-semibold">{r.mpi.toFixed(3)}</td>)}</tr>
              <tr><td className="pr-2 text-muted">Σ w·CH (check)</td>{[nat, ...prov].map((r) => <td key={r.geo_id} className="tabular text-center text-muted">{r.sum_w_ch.toFixed(3)}</td>)}</tr>
            </tbody>
          </table>
        </div>
      </Card>
      <Card>
        <CardTitle title="MPI by consumption quintile" subtitle="NISR MPI Table B.6 — multidimensional poverty falls steeply with consumption, but is present in every quintile" />
        <div className="grid gap-3 sm:grid-cols-5">
          {data.table.filter((r) => r.level === 'quintile').map((r) => (
            <div key={r.geo_id} className="rounded-2xl bg-paper p-4"><p className="text-[11px] font-semibold text-muted">{r.name}</p><p className="tabular text-2xl font-semibold">{pct(r.mpi_incidence)}</p><p className="tabular text-[11px] text-text-2">A {pct(r.mpi_intensity)} · M0 {r.mpi.toFixed(3)}</p></div>
          ))}
        </div>
      </Card>
    </div>
  )
}

/* ------------------------------------------------------------------ trends */
interface Trend { poverty: { name: string; level: string; p2017: number; p2024: number; change_pp: number; change_pct: number; flags: string[] }[]; consumption: { name: string; level: string; c2017: number; c2024: number; change_pct: number }[]; finscope: { name: string; period: string; fs_banked: number; fs_excluded: number; fs_other_formal: number; fs_informal_only: number }[]; notes: string[] }

function Trends() {
  const { data, error, loading, reload } = useApi<Trend>('/api/analysis/trends')
  if (loading) return <LoadingBlock />
  if (error || !data) return <ErrorState error={error} onRetry={reload} />
  const x = (v: number) => `${(v / 60) * 100}%`
  return (
    <div className="space-y-6">
      <Callout tone="note"><ul className="list-disc space-y-0.5 pl-4">{data.notes.map((n) => <li key={n}>{n}</li>)}</ul></Callout>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle title="Poverty rate, 2017 (modelled) → 2024" subtitle="NISR Poverty Profile Tables 0.1 and 5.2 · comparable methodology" right={<StatusBadge status="official" />} />
          <Legend items={[{ label: '2017 (modelled)', color: SERIES.s2, shape: 'dot' }, { label: '2024', color: SERIES.s1, shape: 'dot' }]} />
          <ul className="mt-4 space-y-3">{data.poverty.map((r) => (
            <li key={r.name + r.level} className="grid grid-cols-[8.5rem_1fr_4.5rem] items-center gap-3 text-[12.5px]">
              <span className="truncate text-text-2">{r.name}{r.flags.includes('urban_rural_2012_definition') ? '*' : ''}</span>
              <span className="relative h-5">
                <span className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded bg-line-strong" style={{ left: x(r.p2024), width: `calc(${x(r.p2017)} - ${x(r.p2024)})` }} />
                <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white" style={{ left: x(r.p2017), background: SERIES.s2 }} />
                <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-white" style={{ left: x(r.p2024), background: SERIES.s1 }} />
              </span>
              <span className="tabular text-right font-semibold text-ink-900">{pp(r.change_pp)}</span>
            </li>))}</ul>
          <p className="mt-3 text-[11px] text-muted">* Urban/rural using 2012 definitions (Poverty Profile Table 5.2). Change in percentage points is calculated.</p>
        </Card>
        <Card>
          <CardTitle title="Median consumption per adult equivalent" subtitle="Thousand RWF per year, January 2024 prices · Poverty Profile Table 5.3" right={<StatusBadge status="official" />} />
          <table className="w-full text-[13px]"><thead><tr className="border-b border-line text-left text-[11px] uppercase tracking-wide text-muted"><th className="py-2">Group</th><th className="py-2 text-right">2017</th><th className="py-2 text-right">2024</th><th className="py-2 text-right">Change</th></tr></thead>
            <tbody>{data.consumption.map((r) => <tr key={r.name + r.level} className="border-b border-line/70"><td className="py-1.5">{r.name}</td><td className="tabular py-1.5 text-right text-text-2">{r.c2017.toLocaleString('en-GB')}</td><td className="tabular py-1.5 text-right font-semibold">{r.c2024.toLocaleString('en-GB')}</td><td className="tabular py-1.5 text-right">+{r.change_pct.toFixed(0)}%</td></tr>)}</tbody></table>
        </Card>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ composite */
interface Comp { name: string; formula: string; components: { indicator_id: string; name: string; weight: number; transform: string }[]; validation: { n: number; spearman_rho: number; p_value: number; ci_low: number; ci_high: number; against: string }; sensitivity_leave_one_out: { dropped: string; rank_correlation_with_full: number }[]; rows: { geo_id: string; name: string; score: number; rank: number; poverty_rate: number }[]; warnings: string[] }

function Composite() {
  const { data, error, loading, reload } = useApi<Comp>('/api/analysis/composite')
  if (loading) return <LoadingBlock />
  if (error || !data) return <ErrorState error={error} onRetry={reload} />
  return (
    <div className="space-y-6">
      <Callout tone="warn" title={`${data.name} — not the official MPI`}><ul className="list-disc space-y-0.5 pl-4">{data.warnings.map((w) => <li key={w}>{w}</li>)}</ul></Callout>
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Card>
          <CardTitle title="Formula & weights" right={<StatusBadge status="experimental" />} />
          <p className="rounded-xl bg-paper p-3 font-mono text-[12px] leading-relaxed text-ink-900">{data.formula}</p>
          <ul className="mt-3 space-y-1 text-[13px] text-text-2">{data.components.map((c) => <li key={c.indicator_id}>• {c.transform === 'complement' ? 'Lacking: ' : ''}{c.name} — weight {(c.weight * 100).toFixed(1)}%</li>)}</ul>
          <div className="mt-5 rounded-2xl border border-line p-4">
            <p className="flex items-center gap-2 text-[13px] font-semibold text-ink-900"><BrainCircuit size={15} /> External validation</p>
            <p className="mt-1 text-[13px] text-text-2">Spearman ρ with {data.validation.against}: <strong className="text-ink-900">{r2(data.validation.spearman_rho)}</strong> (95% CI {r2(data.validation.ci_low)} to {r2(data.validation.ci_high)}, n = {data.validation.n}, p = {data.validation.p_value.toExponential(1)}).</p>
            <p className="mt-3 text-[12px] font-semibold text-text-2">Leave-one-out rank stability</p>
            <ul className="mt-1 grid grid-cols-2 gap-1 text-[12px] text-text-2">{data.sensitivity_leave_one_out.map((l) => <li key={l.dropped} className="tabular">drop {l.dropped.replace(/_/g, ' ')}: ρ {r2(l.rank_correlation_with_full)}</li>)}</ul>
          </div>
        </Card>
        <Card>
          <CardTitle title="District ranking (0 = smallest relative service gap, 100 = largest)" />
          <ul className="space-y-1">{data.rows.map((r) => (
            <li key={r.geo_id} className="grid grid-cols-[1.5rem_7rem_1fr_3rem_4.5rem] items-center gap-2 text-[12px]">
              <span className="tabular text-muted">{r.rank}</span><span className="truncate text-text-2">{r.name}</span>
              <span className="h-2.5 rounded-r" style={{ width: `${Math.max(2, r.score)}%`, background: '#1d8477' }} />
              <span className="tabular text-right font-semibold">{r.score.toFixed(0)}</span>
              <span className="tabular text-right text-muted">pov {r.poverty_rate.toFixed(0)}%</span>
            </li>))}</ul>
        </Card>
      </div>
    </div>
  )
}
