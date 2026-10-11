import { ArrowDownUp, ArrowRight, Download, MapPin } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ChoroplethMap, MapLegend } from '../components/ChoroplethMap'
import { CIRow } from '../components/charts'
import { Callout, Card, CardTitle, ErrorState, Flag, LoadingBlock, PageHeader, Segmented, SourceLink, StatusBadge } from '../components/ui'
import { downloadUrl, useApi } from '../lib/api'
import { quantileBreaks } from '../lib/colors'
import { fmt, sigText, titleCase } from '../lib/format'
import { rewindForD3 } from '../lib/geo'
import type { FeatureCollection, IndicatorMeta, MapLayer, MapRow } from '../lib/types'

const THEME_LABEL: Record<string, string> = {
  monetary_poverty: 'Monetary poverty', multidimensional_poverty: 'Multidimensional poverty', mpi_indicator: 'MPI indicators',
  basic_services: 'Basic services', health: 'Health', housing: 'Housing', digital: 'Digital access', labour: 'Labour',
  transfers: 'Transfers', financial_inclusion: 'Financial inclusion', demography: 'Demography',
}

type Level = 'district' | 'province'
type SortKey = 'rank' | 'name' | 'value'

export default function Explorer() {
  const [params, setParams] = useSearchParams()
  const level = (params.get('level') as Level) || 'district'
  const indicator = params.get('indicator') || 'poverty_rate'
  const [selected, setSelected] = useState<string | null>(null)
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'rank', dir: 1 })

  const inds = useApi<IndicatorMeta[]>('/api/indicators')
  const geo = useApi<FeatureCollection>(`/api/geo/${level}`)
  const outline = useApi<FeatureCollection>(level === 'district' ? '/api/geo/province' : null)
  const layer = useApi<MapLayer>(`/api/map?indicator=${indicator}&level=${level}`)

  const geoD3 = useMemo(() => (geo.data ? rewindForD3(geo.data) : null), [geo.data])
  const outlineD3 = useMemo(() => (outline.data && level === 'district' ? rewindForD3(outline.data) : null), [outline.data, level])

  const options = useMemo(() => {
    const list = (inds.data ?? []).filter((i) => i.levels.includes(level) && !i.id.startsWith('mpi_contrib') && !i.id.startsWith('mpi_uh_')
      && !['fs_headline', 'mpi_monetary_overlap', 'shock_response', 'households_eicv', 'population_share'].includes(i.id))
    const groups: Record<string, IndicatorMeta[]> = {}
    list.forEach((i) => { (groups[i.theme] ??= []).push(i) })
    return groups
  }, [inds.data, level])

  const setParam = (k: string, v: string) => { const p = new URLSearchParams(params); p.set(k, v); setParams(p, { replace: true }); setSelected(null) }

  const rows = useMemo(() => layer.data?.rows ?? [], [layer.data])
  const values = Object.fromEntries(rows.map((r) => [r.geo_id, r.value]))
  const nums = rows.map((r) => r.value).filter((v): v is number => v != null)
  const breaks = nums.length >= 5 ? quantileBreaks(nums, 5) : [...nums].sort((a, b) => a - b).slice(0, -1)
  const meta = layer.data?.indicator
  const higherIsDarker = meta?.polarity !== 'higher_better'
  const unit = meta?.unit ?? '%'
  const dec = meta?.decimals ?? 1
  const sel = rows.find((r) => r.geo_id === selected) ?? null
  const nat = layer.data?.national

  const sorted = useMemo(() => {
    const r = [...rows]
    r.sort((a, b) => {
      const va = sort.key === 'name' ? a.geo_name : sort.key === 'value' ? a.value ?? -1 : a.rank ?? 999
      const vb = sort.key === 'name' ? b.geo_name : sort.key === 'value' ? b.value ?? -1 : b.rank ?? 999
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir
    })
    return r
  }, [rows, sort])
  const maxCI = Math.max(...rows.map((r) => r.ci_high ?? r.value ?? 0), nat?.value ?? 0)
  const scaleMax = unit === '%' ? Math.min(100, Math.ceil((maxCI * 1.05) / 10) * 10 || 100) : maxCI * 1.1

  const tip = (id: string, name: string) => {
    const r = rows.find((x) => x.geo_id === id)
    if (!r || r.value == null) return <><strong>{name}</strong><br />No published value</>
    return (
      <>
        <strong className="text-white">{name}</strong><br />
        {meta?.short_name}: <strong>{fmt(r.value, unit, dec)}</strong>
        {r.ci_low != null && <><br />95% CI {r.ci_low.toFixed(1)}–{r.ci_high?.toFixed(1)}</>}
        {r.rank && <><br />Rank {r.rank}/{rows.length}{r.rank_low ? ` (90% interval ${r.rank_low}–${r.rank_high})` : ''}</>}
        {r.vs_national?.available && <><br />{sigText(r.vs_national.label)} vs national</>}
      </>
    )
  }

  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Interactive geographic explorer" title="Where deprivation is concentrated"
        actions={<a className="btn-ghost" href={downloadUrl(`/api/map?indicator=${indicator}&level=${level}&format=csv`)}><Download size={15} /> CSV</a>}>
        Choose an indicator and geography. Only values NISR publishes at that level are mapped — the official MPI exists down to province, so it
        is not offered for districts.
      </PageHeader>

      <div className="card mb-6 flex flex-col gap-4 p-4 md:flex-row md:items-end">
        <div className="flex-1">
          <label htmlFor="ind" className="mb-1.5 block text-xs font-semibold text-text-2">Indicator</label>
          <select id="ind" className="input" value={indicator} onChange={(e) => setParam('indicator', e.target.value)}>
            {Object.entries(options).map(([theme, list]) => (
              <optgroup key={theme} label={THEME_LABEL[theme] ?? titleCase(theme)}>
                {list.map((i) => <option key={i.id} value={i.id}>{i.name}{i.status === 'official_transcribed' ? ' (FinScope)' : ''}</option>)}
              </optgroup>
            ))}
            {!Object.values(options).flat().some((i) => i.id === indicator) && <option value={indicator}>{indicator}</option>}
          </select>
        </div>
        <div>
          <span className="mb-1.5 block text-xs font-semibold text-text-2">Geography</span>
          <Segmented label="Geographic level" value={level} onChange={(v) => {
            const p = new URLSearchParams(params); p.set('level', v)
            const ok = inds.data?.find((i) => i.id === indicator)?.levels.includes(v)
            if (!ok) p.set('indicator', 'poverty_rate')
            setParams(p, { replace: true }); setSelected(null)
          }} options={[{ value: 'district', label: '30 districts' }, { value: 'province', label: '5 provinces' }]} />
        </div>
      </div>

      {(layer.error || geo.error) && <ErrorState error={layer.error ?? geo.error} onRetry={() => { layer.reload(); geo.reload() }} />}
      {(layer.loading || geo.loading) && !layer.data && <LoadingBlock rows={2} />}

      {layer.data && geoD3 && meta && (
        <>
          <div className="grid gap-6 lg:grid-cols-[1.45fr_1fr]">
            <Card className="!p-4 sm:!p-5">
              <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-[15px] font-semibold text-ink-900">{meta.name}</h2>
                  <p className="text-xs text-muted">{meta.universe} · {meta.period} · {level === 'district' ? 'Districts' : 'Provinces'}</p>
                </div>
                <StatusBadge status={meta.status} />
              </div>
              <ChoroplethMap geo={geoD3} outline={outlineD3} values={values} breaks={breaks} higherIsDarker={higherIsDarker}
                unit={unit} decimals={dec} selected={selected} onSelect={setSelected} tooltip={tip}
                title={`Map of ${meta.name} by ${level}. Use Tab to move between areas and Enter to select.`} />
              <div className="mt-2 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
                {nums.length > 1 && <MapLegend breaks={breaks} min={Math.min(...nums)} max={Math.max(...nums)} higherIsDarker={higherIsDarker} unit={unit} decimals={dec}
                  caption={meta.polarity === 'neutral' ? 'Darker = higher value (quintile classes)' : 'Darker = more deprived (quintile classes)'} />}
                <p className="text-[10.5px] leading-relaxed text-muted sm:max-w-56 sm:text-right">
                  Boundaries: geoBoundaries (CC BY 4.0). Province outlines overlaid. No household locations are shown.
                </p>
              </div>
            </Card>

            <div className="space-y-6">
              <Card>
                {sel ? (
                  <>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="eyebrow flex items-center gap-1"><MapPin size={12} /> {level}</p>
                        <h2 className="h-display mt-1 text-2xl font-semibold text-ink-900">{sel.geo_name}</h2>
                      </div>
                      <button className="btn-ghost btn-sm" onClick={() => setSelected(null)}>Clear</button>
                    </div>
                    <p className="tabular mt-4 text-4xl font-semibold text-ink-900">{fmt(sel.value, unit, dec)}</p>
                    {sel.ci_low != null && <p className="tabular mt-1 text-xs text-muted">95% CI {sel.ci_low.toFixed(1)}–{sel.ci_high?.toFixed(1)} · SE {sel.se?.toFixed(2)} · CV {sel.cv?.toFixed(1)}%</p>}
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-[13px]">
                      <div className="rounded-xl bg-paper p-3"><dt className="text-[11px] text-muted">Rwanda</dt><dd className="tabular font-semibold">{fmt(nat?.value, unit, dec)}</dd></div>
                      <div className="rounded-xl bg-paper p-3"><dt className="text-[11px] text-muted">Rank (1 = most deprived)</dt>
                        <dd className="tabular font-semibold">{sel.rank ?? '—'}/{rows.length}{sel.rank_low ? <span className="font-normal text-muted"> · {sel.rank_low}–{sel.rank_high}</span> : null}</dd></div>
                    </dl>
                    {sel.vs_national?.available && (
                      <p className="mt-3 text-[13px] text-text-2">Statistically <strong className="text-ink-900">{sel.vs_national.label}</strong> the national estimate
                        (approx. z-test, p = {sel.vs_national.p_value?.toFixed(3)}).</p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-1">{sel.flags.map((f) => <Flag key={f} flag={f} />)}</div>
                    <Link to={`/profile/${level}/${sel.geo_id}`} className="btn-primary mt-4 w-full">Open full profile <ArrowRight size={15} /></Link>
                  </>
                ) : (
                  <>
                    <CardTitle title="Summary" subtitle="Select an area on the map or in the table" />
                    <dl className="grid grid-cols-2 gap-3 text-[13px]">
                      {[['Rwanda', nat?.value], ['Median of areas', layer.data.summary.median], ['Lowest', layer.data.summary.min], ['Highest', layer.data.summary.max]].map(([l, v]) => (
                        <div key={l as string} className="rounded-xl bg-paper p-3"><dt className="text-[11px] text-muted">{l}</dt><dd className="tabular text-lg font-semibold">{fmt(v as number, unit, dec)}</dd></div>
                      ))}
                    </dl>
                    {layer.data.summary.range_ratio && <p className="mt-3 text-[13px] text-text-2">Highest area is <strong className="text-ink-900">{layer.data.summary.range_ratio.toFixed(1)}×</strong> the lowest. <StatusBadge status="calculated" /></p>}
                  </>
                )}
              </Card>
              <Card>
                <CardTitle title="About this indicator" />
                <p className="text-[13px] leading-relaxed text-text-2">{meta.definition}</p>
                {meta.notes && <Callout tone="warn" className="mt-3">{meta.notes}</Callout>}
                <p className="mt-3 text-[12px] text-muted">{layer.data.rank_note}</p>
                <div className="mt-3"><SourceLink source={{ id: meta.source_id, title: '', short: nat?.source.short ?? meta.source_id, url: nat?.source.url ?? '', landing_page: nat?.source.landing_page }} table={meta.table_ref} /></div>
              </Card>
            </div>
          </div>

          <Card className="mt-6">
            <CardTitle title={`${meta.short_name} by ${level} — table view`} subtitle="Accessible alternative to the map. Bars show 95% confidence intervals where NISR publishes them; the vertical line is the national value." />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted">
                    {([['rank', 'Rank'], ['name', 'Area'], ['value', 'Value']] as [SortKey, string][]).map(([k, l]) => (
                      <th key={k} className="py-2 pr-3 font-semibold" aria-sort={sort.key === k ? (sort.dir === 1 ? 'ascending' : 'descending') : 'none'}>
                        <button className="inline-flex items-center gap-1 hover:text-ink-900" onClick={() => setSort((s) => ({ key: k, dir: s.key === k ? (s.dir === 1 ? -1 : 1) : 1 }))}>
                          {l} <ArrowDownUp size={11} />
                        </button>
                      </th>
                    ))}
                    <th className="w-[38%] py-2 pr-3 font-semibold">Estimate &amp; 95% CI</th>
                    <th className="py-2 font-semibold">vs national</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((r: MapRow) => (
                    <tr key={r.geo_id} className={`border-b border-line/70 ${selected === r.geo_id ? 'bg-brand-50' : 'hover:bg-paper'}`}>
                      <td className="tabular py-2 pr-3 text-muted">{r.rank}{r.rank_low ? <span className="text-[11px]"> ({r.rank_low}–{r.rank_high})</span> : ''}</td>
                      <td className="py-2 pr-3"><button className="font-semibold text-ink-900 hover:text-brand-600" onClick={() => setSelected(r.geo_id)}>{r.geo_name}</button>
                        <div className="mt-0.5 flex flex-wrap gap-1">{r.flags.filter((f) => f.startsWith('cv_') || f.startsWith('unlabelled')).map((f) => <Flag key={f} flag={f} />)}</div></td>
                      <td className="tabular py-2 pr-3 font-semibold">{fmt(r.value, unit, dec)}</td>
                      <td className="py-2 pr-3">
                        <CIRow value={r.value} lo={r.ci_low} hi={r.ci_high} reference={nat?.value} max={scaleMax} highlight={selected === r.geo_id}
                          right={r.ci_low != null ? `${r.ci_low.toFixed(1)}–${r.ci_high?.toFixed(1)}` : '—'} />
                      </td>
                      <td className="py-2 text-[12px] text-text-2">{r.vs_national?.available ? sigText(r.vs_national.label) : <span className="text-muted">no SE published</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
