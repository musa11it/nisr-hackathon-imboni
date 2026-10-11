import { AlertTriangle, Calculator, CheckCircle2, Download, FileText, Home, Users } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BarList, DotPlot } from '../components/charts'
import { Callout, Card, CardTitle, ErrorState, Flag, LoadingBlock, PageHeader, SourceLink, StatusBadge } from '../components/ui'
import { downloadUrl, useApi } from '../lib/api'
import { fmt, int, pct, sigText } from '../lib/format'
import type { FeatureCollection, Metric, SourceRef } from '../lib/types'

interface Entry extends Metric {
  national: number | null
  province: number | null
  vs_national: { available: boolean; label: string; p_value?: number }
  rank?: number; rank_low?: number; rank_high?: number; n_peers?: number
  peer_min?: number; peer_median?: number; peer_max?: number
}
interface Profile {
  level: string; geo_id: string; name: string; province_id: string | null; province_name: string | null
  indicators: Entry[]
  fingerprint: { indicator_id: string; label: string; value: number; national: number; province: number | null; status: string; source: SourceRef }[]
  mpi: null | {
    level: string; geo_name: string; is_parent_province: boolean; note: string | null
    incidence: Metric; intensity: Metric; mpi: Metric
    censored_headcounts: { id: string; label: string; dimension: string; weight_label: string; censored_headcount: number; national: number }[]
  }
  findings: { indicator_id: string; kind: 'concern' | 'strength'; text: string }[]
}

export default function ProfilePage() {
  const { level = 'district', geoId = 'nyamagabe' } = useParams()
  const nav = useNavigate()
  const { data, error, loading, reload } = useApi<Profile>(`/api/profile/${level}/${geoId}`)
  const districts = useApi<FeatureCollection>('/api/geo/district')
  const provinces = useApi<FeatureCollection>('/api/geo/province')

  const hh = data?.indicators.find((i) => i.indicator_id === 'households_census')
  const hhs = data?.indicators.find((i) => i.indicator_id === 'household_size_census')
  const main = data?.indicators.filter((i) => !['households_census', 'household_size_census'].includes(i.indicator_id)) ?? []

  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <div className="card mb-6 flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
        <label htmlFor="area" className="text-xs font-semibold text-text-2">Choose an area</label>
        <select id="area" className="input sm:max-w-sm" value={`${level}/${geoId}`} onChange={(e) => nav(`/profile/${e.target.value}`)}>
          <option value="national/rwanda">Rwanda (national)</option>
          <optgroup label="Provinces">
            {provinces.data?.features.map((f) => <option key={f.properties.geo_id} value={`province/${f.properties.geo_id}`}>{f.properties.name}</option>)}
          </optgroup>
          <optgroup label="Districts">
            {[...(districts.data?.features ?? [])].sort((a, b) => a.properties.name.localeCompare(b.properties.name)).map((f) => (
              <option key={f.properties.geo_id} value={`district/${f.properties.geo_id}`}>{f.properties.name} — {f.properties.province}</option>
            ))}
          </optgroup>
        </select>
      </div>

      {loading && <LoadingBlock rows={4} />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && (
        <>
          <PageHeader eyebrow={`${data.level} profile${data.province_name ? ` · ${data.province_name}` : ''}`} title={data.name}
            actions={<>
              <a className="btn-primary" href={downloadUrl(`/api/reports/profile/${data.level}/${data.geo_id}.pdf`)}><FileText size={15} /> PDF brief</a>
              <a className="btn-ghost" href={downloadUrl(`/api/reports/profile/${data.level}/${data.geo_id}.csv`)}><Download size={15} /> CSV</a>
              <Link className="btn-brand" to={`/simulator?level=${data.level}&geo=${data.geo_id}`}><Calculator size={15} /> Simulate a budget</Link>
            </>}>
            <div className="flex flex-wrap gap-4 text-[13px]">
              {hh && <span className="flex items-center gap-1.5"><Home size={14} className="text-brand-600" /> {int(hh.value)} private households <span className="text-muted">(Census 2022)</span></span>}
              {hhs && <span className="flex items-center gap-1.5"><Users size={14} className="text-brand-600" /> {hhs.value?.toFixed(1)} persons per household</span>}
            </div>
          </PageHeader>

          <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
            <Card>
              <CardTitle title="Deprivation fingerprint" subtitle="Share lacking each service or in poverty (%). Further right = more deprived."
                info="Each row converts the official indicator into a deprivation rate (e.g. 100 − % with electricity). Area values come from EICV7 district/province tables and FinScope 2024 (adults). Hover a row for sources." />
              <DotPlot areaLabel={data.name} provinceLabel={data.level === 'district' ? data.province_name ?? undefined : undefined}
                rows={data.fingerprint.map((f) => ({
                  key: f.indicator_id, label: f.label, area: f.value, province: f.province, national: f.national,
                  tip: <><strong>{f.label}</strong><br />{data.name}: {pct(f.value)}{f.province != null && <><br />{data.province_name}: {pct(f.province)}</>}<br />Rwanda: {pct(f.national)}<br /><span className="text-white/60">{f.source.short}</span></>,
                }))} />
            </Card>

            <Card>
              <CardTitle title="What stands out" subtitle="Differences vs national that are statistically significant (95%, approximate z-test using NISR standard errors)" />
              {data.findings.length === 0 ? (
                <p className="text-sm text-text-2">{data.level === 'national' ? 'National profile — see district and province profiles for comparisons.' : 'No indicator differs significantly from the national estimate.'}</p>
              ) : (
                <ul className="space-y-2.5">
                  {data.findings.map((f) => (
                    <li key={f.indicator_id} className="flex gap-2.5 text-[13px] leading-relaxed text-text-2">
                      {f.kind === 'concern'
                        ? <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[#d03b3b]" aria-label="Concern" />
                        : <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#0ca30c]" aria-label="Strength" />}
                      <span>{f.text}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-4 border-t border-line pt-3 text-[11px] leading-relaxed text-muted">Tests ignore the covariance between a district and the national estimate that contains it, and are not adjusted for multiple comparisons — treat them as screening signals.</p>
            </Card>
          </div>

          <Card className="mt-6">
            <CardTitle title="All indicators" subtitle="Official values with published precision. Rank 1 = most deprived among peers; brackets give 90% rank intervals." />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-[13px]">
                <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
                  <th className="py-2 pr-3 font-semibold">Indicator</th><th className="py-2 pr-3 font-semibold">Value</th><th className="py-2 pr-3 font-semibold">95% CI</th>
                  {data.level === 'district' && <th className="py-2 pr-3 font-semibold">Province</th>}
                  <th className="py-2 pr-3 font-semibold">Rwanda</th><th className="py-2 pr-3 font-semibold">Rank</th><th className="py-2 pr-3 font-semibold">vs national</th><th className="py-2 font-semibold">Source</th>
                </tr></thead>
                <tbody>
                  {main.map((e) => (
                    <tr key={e.indicator_id} className="border-b border-line/70 align-top">
                      <td className="py-2.5 pr-3"><span className="font-semibold text-ink-900">{e.short_name}</span>
                        <div className="mt-1 flex flex-wrap gap-1"><StatusBadge status={e.status} />{e.flags.map((f) => <Flag key={f} flag={f} />)}</div></td>
                      <td className="tabular py-2.5 pr-3 font-semibold">{fmt(e.value, e.unit, e.decimals)}</td>
                      <td className="tabular py-2.5 pr-3 text-text-2">{e.ci_low != null ? `${e.ci_low.toFixed(1)}–${e.ci_high?.toFixed(1)}` : '—'}</td>
                      {data.level === 'district' && <td className="tabular py-2.5 pr-3 text-text-2">{fmt(e.province, e.unit, e.decimals)}</td>}
                      <td className="tabular py-2.5 pr-3 text-text-2">{fmt(e.national, e.unit, e.decimals)}</td>
                      <td className="tabular py-2.5 pr-3 text-text-2">{e.rank ? <>{e.rank}/{e.n_peers}{e.rank_low ? <span className="text-[11px] text-muted"> ({e.rank_low}–{e.rank_high})</span> : null}</> : '—'}</td>
                      <td className="py-2.5 pr-3 text-[12px] text-text-2">{e.vs_national.available ? sigText(e.vs_national.label) : '—'}</td>
                      <td className="py-2.5"><SourceLink source={e.source} table={e.table_ref} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {data.mpi && (
            <Card className="mt-6">
              <CardTitle title={`Multidimensional poverty — ${data.mpi.geo_name}`}
                subtitle="Rwanda national MPI (Alkire–Foster, 13 indicators, k = 33.3%). Bars: censored headcount ratio (% MPI-poor and deprived); hover for the national value."
                right={<StatusBadge status="official" />} />
              {data.mpi.note && <Callout tone="warn" className="mb-4">{data.mpi.note}</Callout>}
              <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
                <dl className="grid grid-cols-3 gap-3 lg:grid-cols-1">
                  {[['Incidence (H)', pct(data.mpi.incidence.value)], ['Intensity (A)', pct(data.mpi.intensity.value)], ['MPI (M0)', data.mpi.mpi.value?.toFixed(3)]].map(([l, v]) => (
                    <div key={l} className="rounded-2xl bg-paper p-4"><dt className="text-[11px] text-muted">{l}</dt><dd className="tabular mt-1 text-2xl font-semibold text-ink-900">{v}</dd></div>
                  ))}
                </dl>
                <BarList unit="%" labelWidth="w-44"
                  data={[...data.mpi.censored_headcounts].sort((a, b) => b.censored_headcount - a.censored_headcount).map((c) => ({
                    key: c.id, label: c.label, value: c.censored_headcount,
                    tip: <><strong>{c.label}</strong> ({c.dimension}, weight {c.weight_label})<br />{data.mpi!.geo_name}: {pct(c.censored_headcount)} · Rwanda: {pct(c.national)}</>,
                  }))}
                  reference={null} />
              </div>
              <p className="mt-3 text-[11px] text-muted">Source: NISR EICV7 Multidimensional Poverty Thematic Report, Tables B.2–B.5.</p>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
