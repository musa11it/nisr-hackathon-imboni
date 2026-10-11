import { Ban, Download } from 'lucide-react'
import { useMemo, useState } from 'react'
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { BarList, Legend, StackRow, useHoverTip } from '../components/charts'
import { Callout, Card, CardTitle, ErrorState, LoadingBlock, PageHeader, Segmented, SourceLink, StatusBadge } from '../components/ui'
import { downloadUrl, useApi } from '../lib/api'
import { INK, SERIES, STRAND } from '../lib/colors'
import { pct, pp, rwf, titleCase, r2 } from '../lib/format'
import type { SourceRef } from '../lib/types'

type Strand = Record<string, number | null>
interface Fin {
  national_strand: Record<'2020' | '2024', Strand>
  area: Record<string, Record<'2020' | '2024', Strand>>
  sex: Record<string, Record<'2020' | '2024', Strand>>
  provinces: ({ geo_id: string; name: string } & Strand)[]
  districts: ({ geo_id: string; name: string; province_id: string; formally_served: number; poverty_rate: number; smartphone: number; mobile_phone: number } & Strand)[]
  headline: { key: string; label: string; value: number; status: string }[]
  eicv: Record<string, { all: number; poor: number; non_poor: number; gap_pp: number; meta: { name: string; definition: string; table_ref: string } }>
  vup: { component: string; sacco: number; momo: number; on_time: number; households: number; poverty_rate: number }[]
  vup_financial_services: { loan_approved: number; avg_loan: number; households: number; poverty_rate: { value: number; ci_low: number; ci_high: number } }
  shock_responses: { response: string; all: number; poor: number; non_poor: number }[]
  correlations: { pairs: { a: string; b: string; rho: number; ci_low: number; ci_high: number; p_value: number; q_value: number; n: number }[] }
  unavailable: { variable: string; where_collected: string; status: string; how_to_obtain: string }[]
  sources: SourceRef[]
  caveats: string[]
}

const segs = (s: Strand) => STRAND.map((x) => ({ key: x.key, label: x.label, value: s[x.key] ?? null, color: x.color }))

export default function Financial() {
  const { data, error, loading, reload } = useApi<Fin>('/api/financial-inclusion')
  const [sortBy, setSortBy] = useState<'exclusion' | 'banked'>('exclusion')
  const hv = useHoverTip()
  const hv2 = useHoverTip()

  const districts = useMemo(() => {
    if (!data) return []
    const d = [...data.districts]
    if (sortBy === 'banked') d.sort((a, b) => (a.fs_banked ?? 0) - (b.fs_banked ?? 0))
    else d.sort((a, b) => ((b.fs_excluded ?? 0) + (b.fs_informal_only ?? 0)) - ((a.fs_excluded ?? 0) + (a.fs_informal_only ?? 0)))
    return d
  }, [data, sortBy])

  const pair = (a: string, b: string) => data?.correlations.pairs.find((p) => (p.a === a && p.b === b) || (p.a === b && p.b === a))
  const hl = (k: string) => data?.headline.find((h) => h.key === k)?.value

  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Financial inclusion analytics" title="Who is served — and who is not"
        actions={<a className="btn-ghost" href={downloadUrl('/api/map?indicator=fs_excluded&level=district&format=csv')}><Download size={15} /> District CSV</a>}>
        Financial inclusion is analysed only with indicators that official sources actually publish: FinScope Rwanda 2024 (adults 16+), EICV7 household
        savings and mobile-money accounts, and EICV7 VUP programme payment data. Variables that are collected but unpublished are listed as unavailable.
      </PageHeader>
      {loading && <LoadingBlock rows={4} />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && (
        <div className="space-y-6">
          <Callout tone="note" title="Read with care">
            <ul className="list-disc space-y-0.5 pl-4">{data.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
          </Callout>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Financially included', hl('overall_inclusion'), 'Formal or informal products, adults 16+'],
              ['Formally included', hl('formal_inclusion'), 'Banks, mobile money, SACCO, MFI, insurance or pension'],
              ['Banked', hl('bank_account'), 'Bank product in own name'],
              ['Mobile-money account', hl('mobile_money_account'), 'Registered wallet in own name'],
            ].map(([l, v, d]) => (
              <div key={l as string} className="card p-5">
                <p className="text-[13px] font-semibold text-text-2">{l}</p>
                <p className="tabular mt-2 text-[34px] font-semibold leading-none text-ink-900">{pct(v as number, 0)}</p>
                <p className="mt-2 text-[12px] text-muted">{d}</p>
                <div className="mt-3 flex items-center gap-2"><StatusBadge status="official_transcribed" /><span className="chip border-line bg-paper text-text-2">2024</span></div>
              </div>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardTitle title="FinScope Access Strand, 2020 → 2024" subtitle="% of adults (16+). Each adult is counted once, in the most formal category they use."
                info="Banked = uses a commercial bank. Other formal = uses only non-bank formal products (mobile money, SACCO, MFI, insurance, pension). Informal only = e.g. savings groups. Excluded = none." />
              <div className="mb-4"><Legend items={STRAND.map((s) => ({ label: s.label, color: s.color }))} /></div>
              <div ref={hv.attach} className="relative space-y-2.5" onMouseLeave={hv.hide}>
                {([['Rwanda 2020', data.national_strand['2020']], ['Rwanda 2024', data.national_strand['2024']],
                  ['Urban 2020', data.area.urban['2020']], ['Urban 2024', data.area.urban['2024']],
                  ['Rural 2020', data.area.rural['2020']], ['Rural 2024', data.area.rural['2024']],
                  ['Men 2020', data.sex.male['2020']], ['Men 2024', data.sex.male['2024']],
                  ['Women 2020', data.sex.female['2020']], ['Women 2024', data.sex.female['2024']]] as [string, Strand][]).map(([l, s], i) => (
                  <div key={l} className={i % 2 === 0 && i > 0 ? 'pt-2' : ''}>
                    <StackRow label={l} segments={segs(s)} onHover={(e, seg) => hv.show(e, <>{l}<br />{seg.label}: <strong>{pct(seg.value, 0)}</strong></>)} />
                  </div>
                ))}
                {hv.node}
              </div>
              <SourceLink className="mt-4" source={data.sources[0]} table="Figures 5–7" />
            </Card>

            <Card>
              <CardTitle title="Households with accounts, by poverty status" subtitle="EICV7 2023/24 · % of households with at least one account (any member)" right={<StatusBadge status="official" />} />
              <div className="space-y-6">
                {Object.entries(data.eicv).map(([k, v]) => (
                  <div key={k}>
                    <p className="mb-2 text-[13px] font-semibold text-ink-900">{v.meta.name}</p>
                    {[{ l: 'Non-poor households', val: v.non_poor, c: SERIES.s1 }, { l: 'Poor households', val: v.poor, c: SERIES.s2 }].map((r) => (
                      <div key={r.l} className="mb-1.5 grid grid-cols-[9rem_1fr_3.5rem] items-center gap-3">
                        <span className="text-[12px] text-text-2">{r.l}</span>
                        <span className="h-5 rounded-r-[4px]" style={{ width: `${r.val}%`, background: r.c }} />
                        <span className="tabular text-right text-[12.5px] font-semibold">{pct(r.val)}</span>
                      </div>
                    ))}
                    <p className="text-[12px] text-text-2">All households: <strong>{pct(v.all)}</strong> · Gap: <strong>{pp(v.gap_pp)}</strong> <StatusBadge status="calculated" /></p>
                  </div>
                ))}
              </div>
              <SourceLink className="mt-4" source={data.sources[1]} table="Table 6.9 (memo items)" />
            </Card>
          </div>

          <Card>
            <CardTitle title="Financial Access Strand by district" subtitle="FinScope 2024, % of adults. 30 districts — the finest level published."
              info="Values transcribed from the data labels of FinScope 2024 Figure 13 (rounded integers, may sum to 99–101%). Nyarugenge's informal-only segment is unlabelled in the figure and is left blank."
              right={<Segmented label="Sort districts" size="sm" value={sortBy} onChange={setSortBy}
                options={[{ value: 'exclusion', label: 'Most excluded + informal' }, { value: 'banked', label: 'Least banked' }]} />} />
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><Legend items={STRAND.map((s) => ({ label: s.label, color: s.color }))} /><StatusBadge status="official_transcribed" /></div>
            <div ref={hv2.attach} onMouseLeave={hv2.hide} className="relative grid gap-x-10 gap-y-2 lg:grid-cols-2">
              {hv2.node}
              {districts.map((d) => (
                <StackRow key={d.geo_id} label={d.name} segments={segs(d)} onHover={(e, seg) => hv2.show(e, <>{d.name}<br />{seg.label}: <strong>{seg.value == null ? 'not labelled' : pct(seg.value, 0)}</strong></>)} />
              ))}
            </div>
            <SourceLink className="mt-4" source={data.sources[0]} table="Figure 13" />
          </Card>

          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
            <Card>
              <CardTitle title="District association: poverty vs banking" subtitle="Each dot is a district. x = EICV7 poverty rate (2023/24); y = % adults banked (FinScope 2024)."
                info="Spearman rank correlation with a 95% confidence interval. This is an ecological association between district averages — it does not show that banking reduces poverty or vice versa." />
              <div className="h-72">
                <ResponsiveContainer>
                  <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 4 }}>
                    <CartesianGrid stroke={INK.grid} />
                    <XAxis type="number" dataKey="poverty_rate" name="Poverty rate" unit="%" tick={{ fontSize: 11, fill: INK.muted }} label={{ value: 'Poverty rate (%)', position: 'bottom', fontSize: 11, fill: INK.secondary }} />
                    <YAxis type="number" dataKey="fs_banked" name="Banked" unit="%" tick={{ fontSize: 11, fill: INK.muted }} width={44} />
                    <ZAxis range={[70, 70]} />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ payload }) => payload?.[0] ? (
                      <div className="rounded-xl bg-ink-900 px-3 py-2 text-xs text-white">
                        <strong>{(payload[0].payload as any).name}</strong><br />Poverty {pct((payload[0].payload as any).poverty_rate)} · Banked {pct((payload[0].payload as any).fs_banked, 0)}
                      </div>) : null} />
                    <Scatter isAnimationActive={false} data={data.districts} fill={SERIES.s1} stroke="#fff" strokeWidth={1.5} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              {(() => {
                const p = pair('poverty_rate', 'fs_banked')
                return p ? <p className="text-[13px] text-text-2">Spearman ρ = <strong className="text-ink-900">{r2(p.rho)}</strong> (95% CI {r2(p.ci_low)} to {r2(p.ci_high)}, n = {p.n}, FDR q = {p.q_value.toFixed(3)}) <StatusBadge status="calculated" /></p> : null
              })()}
            </Card>

            <Card>
              <CardTitle title="Responses to shocks" subtitle="Main response among households reporting a severe shock, EICV7 2024" right={<StatusBadge status="official" />} />
              <BarList unit="%" labelWidth="w-44" color={SERIES.s2}
                data={data.shock_responses.map((s) => ({ key: `p-${s.response}`, label: s.response, value: s.poor, tip: <>{s.response}<br />Poor: {pct(s.poor)} · Non-poor: {pct(s.non_poor)}</> }))} />
              <p className="mt-3 text-[12px] leading-relaxed text-text-2">Bars show <strong>poor</strong> households. Using savings or borrowing: {pct(data.shock_responses.find((s) => s.response.startsWith('Using savings'))?.poor)} of poor vs{' '}
                {pct(data.shock_responses.find((s) => s.response.startsWith('Using savings'))?.non_poor)} of non-poor households.</p>
              <SourceLink className="mt-3" source={data.sources[1]} table="Table 6.11" />
            </Card>
          </div>

          <Card>
            <CardTitle title="Social protection payments: channels and timeliness" subtitle="EICV7 VUP thematic tables · share of beneficiaries by how their most recent payment was received" right={<StatusBadge status="official" />} />
            <div className="mb-3"><Legend items={[{ label: 'Umurenge SACCO', color: SERIES.s1 }, { label: 'Mobile money (MoMo / Airtel Money)', color: SERIES.s2 }]} /></div>
            <div className="space-y-2.5">
              {data.vup.map((v) => (
                <div key={v.component} className="grid gap-2 md:grid-cols-[1fr_11rem] md:items-center">
                  <StackRow label={v.component} segments={[{ key: 's', label: 'SACCO', value: v.sacco, color: SERIES.s1 }, { key: 'm', label: 'MoMo', value: v.momo, color: SERIES.s2 }]} />
                  <p className="text-[12px] text-text-2">Paid on time: <strong className="text-ink-900">{pct(v.on_time)}</strong></p>
                </div>
              ))}
            </div>
            <div className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-3">
              <div className="rounded-2xl bg-paper p-4"><p className="text-[11px] text-muted">VUP Financial Services: loans approved</p><p className="tabular text-2xl font-semibold">{pct(data.vup_financial_services.loan_approved)}</p></div>
              <div className="rounded-2xl bg-paper p-4"><p className="text-[11px] text-muted">Average FS loan per participant</p><p className="tabular text-2xl font-semibold">{rwf(data.vup_financial_services.avg_loan)}</p></div>
              <div className="rounded-2xl bg-paper p-4"><p className="text-[11px] text-muted">Poverty rate among FS beneficiaries</p><p className="tabular text-2xl font-semibold">{pct(data.vup_financial_services.poverty_rate.value)}</p>
                <p className="tabular text-[11px] text-muted">95% CI {data.vup_financial_services.poverty_rate.ci_low.toFixed(1)}–{data.vup_financial_services.poverty_rate.ci_high.toFixed(1)}</p></div>
            </div>
            <p className="mt-3 text-[12px] text-muted">Payment-delay data describe programme delivery; they are not an evaluation of programme impact. <SourceLink source={data.sources[2]} table="Tables 4.2–4.13, A.1" /></p>
          </Card>

          <Card>
            <CardTitle title="Not available — and not estimated" subtitle="Variables relevant to financial inclusion that official public tables do not report" />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-[13px]">
                <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted"><th className="py-2 pr-3">Variable</th><th className="py-2 pr-3">Where collected</th><th className="py-2 pr-3">Status</th><th className="py-2">How to obtain</th></tr></thead>
                <tbody>{data.unavailable.map((u) => (
                  <tr key={u.variable} className="border-b border-line/70 align-top">
                    <td className="py-2 pr-3 font-semibold text-ink-900"><Ban size={13} className="mr-1.5 inline text-muted" />{u.variable}</td>
                    <td className="py-2 pr-3 text-text-2">{u.where_collected}</td>
                    <td className="py-2 pr-3"><span className="chip border-line bg-paper text-text-2">{titleCase(u.status)}</span></td>
                    <td className="py-2 text-text-2">{u.how_to_obtain}</td>
                  </tr>))}</tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
