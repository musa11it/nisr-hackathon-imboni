import { ArrowRight, Download, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BarList } from '../components/charts'
import { KpiCard } from '../components/KpiCard'
import { Callout, Card, CardTitle, ErrorState, LoadingBlock, PageHeader, Segmented, StatusBadge } from '../components/ui'
import { downloadUrl, useApi } from '../lib/api'
import { SERIES } from '../lib/colors'
import { pct } from '../lib/format'
import type { MapLayer } from '../lib/types'

interface Dep { id: string; label: string; dimension: string; weight: number; weight_label: string; censored: number; uncensored: number; contribution_calc: number; deprived_if: string }
interface Dash {
  kpis: Record<string, any>
  deprivations: Dep[]
  overlap: { cells: Record<string, number>; either: number; share_of_monetary_poor_also_mpi_poor: number }
  provinces: { geo_id: string; name: string; poverty_rate: number; mpi_incidence: number; mpi: number; extreme_poverty_rate: number }[]
  validation: { total: number; passed: number; errors: number; warnings: number }
}

export default function Dashboard() {
  const { data, error, loading, reload } = useApi<Dash>('/api/dashboard')
  const dist = useApi<MapLayer>('/api/map?indicator=poverty_rate&level=district')
  const ranked = dist.data ? [...dist.data.rows].filter((r) => r.value != null).sort((a, b) => (a.value ?? 0) - (b.value ?? 0)) : []
  const lowest = ranked.slice(0, 2)
  const highest = ranked[ranked.length - 1]
  const [mode, setMode] = useState<'censored' | 'uncensored'>('censored')

  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Data intelligence dashboard" title="Rwanda's poverty picture, verified"
        actions={<a className="btn-ghost" href={downloadUrl('/api/observations?format=csv')}><Download size={15} /> All data (CSV)</a>}>
        Headline indicators from EICV7 (2023/24), FinScope 2024 and the 2022 Census. Each card states its definition, period, source table and
        whether the value is <em>official</em> or <em>calculated</em> by Imboni.
      </PageHeader>

      {loading && <LoadingBlock rows={3} />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && (
        <div className="space-y-6">
          <Callout tone="note" title="Two different poverty concepts">
            The <strong>monetary poverty rate</strong> counts people whose consumption is below the national poverty line. <strong>MPI incidence</strong> counts
            people deprived in at least one third of 13 weighted indicators. They measure different things and are shown side by side — never as substitutes.
          </Callout>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard m={data.kpis.poverty_rate} label="Monetary poverty rate" accent>
              Extreme poverty: <strong className="text-ink-900">{pct(data.kpis.extreme_poverty_rate.value)}</strong>
            </KpiCard>
            <KpiCard m={data.kpis.mpi_incidence} label="Multidimensional poverty incidence (H)" accent>
              Average intensity among the MPI-poor: <strong className="text-ink-900">{pct(data.kpis.mpi_intensity.value)}</strong>
            </KpiCard>
            <KpiCard m={data.kpis.mpi} label="Multidimensional Poverty Index (M0)" decimals={3}>
              M0 = H × A = {(data.kpis.mpi_incidence.value / 100).toFixed(3)} × {(data.kpis.mpi_intensity.value / 100).toFixed(3)}
            </KpiCard>
            <KpiCard m={data.kpis.rural_urban_gap} label="Rural − urban MPI incidence gap" decimals={1}>
              Rural {pct(data.kpis.rural_urban_gap.rural)} vs urban {pct(data.kpis.rural_urban_gap.urban)} — rural incidence is
              <strong className="text-ink-900"> {data.kpis.rural_urban_gap.ratio.toFixed(2)}×</strong> urban.
            </KpiCard>
            <KpiCard m={data.kpis.poverty_change} label="Change in poverty, 2017 → 2024" decimals={1}
              footnote="2017 is NISR's modelled re-estimate on the EICV7 methodology (comparable baseline).">
              {pct(data.kpis.poverty_change.from)} (2017, modelled) → {pct(data.kpis.poverty_change.to)} (2024)
            </KpiCard>
            <KpiCard m={data.kpis.poverty_gap} label="Poverty gap index" decimals={2}
              footnote="Average shortfall below the poverty line across the whole population." />
            <KpiCard m={data.kpis.gini} label="Inequality (Gini)" decimals={1} unit="index">
              Consumption per adult equivalent, 0–100 scale.
            </KpiCard>
            <KpiCard m={data.kpis.hh_savings_account} label="Households with a savings account">
              Mobile-money account: <strong className="text-ink-900">{pct(data.kpis.hh_momo_account.value)}</strong> of households.
            </KpiCard>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
            <Card>
              <CardTitle title="Leading reported deprivations"
                subtitle={mode === 'censored' ? 'Censored headcount: % of people who are MPI-poor AND deprived in the indicator' : 'Uncensored headcount: % of ALL people deprived in the indicator'}
                info="Rwanda's national MPI (EICV7). Censored headcounts are the official building blocks of the MPI: MPI = Σ weight × censored headcount. Ranked here by value; weights shown in the tooltip."
                right={<Segmented label="Headcount type" size="sm" value={mode} onChange={setMode}
                  options={[{ value: 'censored', label: 'Censored' }, { value: 'uncensored', label: 'Uncensored' }]} />} />
              <BarList unit="%" color={mode === 'censored' ? '#1d8477' : SERIES.s1}
                data={[...data.deprivations].sort((a, b) => (mode === 'censored' ? b.censored - a.censored : b.uncensored - a.uncensored)).map((d) => ({
                  key: d.id, label: d.label, value: mode === 'censored' ? d.censored : d.uncensored,
                  tip: <><strong>{d.label}</strong> · {d.dimension}<br />Weight {d.weight_label}<br />Deprived if: {d.deprived_if}</>,
                }))} />
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                <span className="text-[11px] text-muted">Source: NISR EICV7 MPI Thematic Report, Tables B.1–B.2 · 2023/24</span>
                <StatusBadge status="official" />
              </div>
            </Card>

            <Card>
              <CardTitle title="Provinces: two lenses side by side" subtitle="Monetary poverty rate vs MPI incidence, % of people (EICV7 2023/24)"
                info="Both are official province estimates. They are different measures: compare the ranking pattern, not the gap between the two numbers." />
              <div className="space-y-4">
                {data.provinces.map((p) => (
                  <Link key={p.geo_id} to={`/profile/province/${p.geo_id}`} className="block rounded-xl p-2 -m-2 hover:bg-paper">
                    <div className="flex items-baseline justify-between">
                      <span className="text-[13px] font-semibold text-ink-900">{p.name}</span>
                      <span className="text-[11px] text-muted">MPI {p.mpi.toFixed(3)}</span>
                    </div>
                    {[{ v: p.poverty_rate, c: SERIES.s1, l: 'Monetary poverty' }, { v: p.mpi_incidence, c: SERIES.s2, l: 'MPI incidence' }].map((s) => (
                      <div key={s.l} className="mt-1.5 grid grid-cols-[6.5rem_1fr_3rem] items-center gap-2">
                        <span className="text-[11px] text-text-2">{s.l}</span>
                        <span className="h-2.5 rounded-r-[4px]" style={{ width: `${(s.v / 45) * 100}%`, background: s.c }} />
                        <span className="tabular text-right text-[12px] font-semibold text-ink-900">{pct(s.v)}</span>
                      </div>
                    ))}
                  </Link>
                ))}
              </div>
              <p className="mt-4 border-t border-line pt-3 text-[11px] text-muted">Sources: EICV7 Main Indicators Table 9.1; MPI Thematic Report Table B.5.</p>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardTitle title="Where is deprivation concentrated?" subtitle="Monetary poverty by district — 30 official EICV7 estimates with 95% confidence intervals" />
              {highest && (
                <p className="text-[13px] leading-relaxed text-text-2">
                  District poverty ranges from {lowest.map((r) => `${pct(r.value)} in ${r.geo_name}`).join(' and ')} to {pct(highest.value)} in {highest.geo_name}{' '}
                  (95% CI {highest.ci_low?.toFixed(1)}–{highest.ci_high?.toFixed(1)}%). Because district samples are smaller, many neighbouring ranks are
                  statistically indistinguishable — the explorer shows rank intervals so differences are not over-read.
                </p>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/explorer" className="btn-primary">Open the map explorer <ArrowRight size={15} /></Link>
                {highest && <Link to={`/profile/district/${highest.geo_id}`} className="btn-ghost">{highest.geo_name} profile</Link>}
              </div>
            </Card>
            <Card className="bg-ink-900 text-white">
              <div className="flex items-center gap-2 text-emerald-glow"><ShieldCheck size={18} /><span className="text-sm font-semibold">Data validation</span></div>
              <p className="tabular mt-3 text-4xl font-semibold">{data.validation.passed}<span className="text-lg text-white/50">/{data.validation.total}</span></p>
              <p className="mt-1 text-[13px] text-white/70">automated checks passed · {data.validation.errors} pipeline errors · {data.validation.warnings} inconsistencies in source tables documented</p>
              <Link to="/analysis" className="mt-4 inline-flex items-center gap-1 text-[13px] font-semibold text-emerald-glow hover:text-white">Inspect the checks <ArrowRight size={14} /></Link>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
