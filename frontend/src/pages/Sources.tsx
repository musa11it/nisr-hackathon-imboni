import { Download, ExternalLink, Lock } from 'lucide-react'
import { Callout, Card, CardTitle, ErrorState, LoadingBlock, PageHeader, StatusBadge } from '../components/ui'
import { downloadUrl, useApi } from '../lib/api'

interface Src { id: string; short: string; title: string; publisher: string; period: string; url: string; landing_page: string; file: string | null; format: string; access: string; license: string; used_for: string; citation: string; caveat?: string; retrieval?: { sha256: string; retrieved_at: string; bytes: number; status: string } }
interface Fw { name: string; method: string; unit_of_identification: string; unit_of_analysis: string; poverty_cutoff_label: string; source: string; changes_vs_eicv5: string[]; indicators: { id: string; label: string; dimension: string; weight_label: string; deprived_if: string }[] }

const FORMULAS: [string, string, string][] = [
  ['MPI identity (Alkire–Foster)', 'M0 = H × A = Σⱼ wⱼ · CHⱼ', 'Checked for every published group; Σ w·CH uses printed censored headcounts (1 decimal), so small rounding gaps are expected.'],
  ['Indicator contribution', 'contribⱼ = wⱼ · CHⱼ / Σᵢ wᵢ · CHᵢ', 'Recomputed by Imboni (status: calculated) because the printed Tables B.7–B.9 cannot be reproduced.'],
  ['Rural–urban gap', 'gap = H_rural − H_urban (pp); ratio = H_rural / H_urban', 'MPI incidence, Table B.5.'],
  ['Overlap “poor on either measure”', 'both + MPI-only + monetary-only', 'Shares of national population, MPI Table 3.1.'],
  ['Difference vs national', 'z = (x̂ − x̂_nat) / √(SE² + SE_nat²); significant if |z| > 1.96', 'Approximate: ignores covariance between a district and the national estimate.'],
  ['Rank interval', '90% interval of ranks over 4,000 draws from Normal(x̂, SE)', 'Fixed seed for reproducibility.'],
  ['Correlation', 'Spearman ρ; 95% CI via Fisher z with SE = 1.06/√(n − 3); Benjamini–Hochberg q', 'Ecological, descriptive only.'],
  ['Simulator amounts', 'amountⱼ = budget × shareⱼ, largest-remainder rounding so Σ amounts = budget × Σ shares', 'Whole RWF; remaining budget reported explicitly.'],
  ['Simulator reach', 'reachedⱼ = min(⌊amountⱼ / unit costⱼ⌋, householdsₐ × needⱼ)', 'Households from Census 2022; need rates from EICV7/FinScope at the finest published level.'],
  ['Experimental service-gap index', 'SGI = mean of z-scores of 6 service deprivation rates', 'Validated against district poverty (not an input).'],
]

export default function Sources() {
  const src = useApi<Src[]>('/api/sources')
  const fw = useApi<Fw>('/api/mpi')
  const framework = (fw.data as unknown as { framework: Fw } | null)?.framework

  return (
    <div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Sources & methodology" title="Where every number comes from"
        actions={<a className="btn-ghost" href={downloadUrl('/api/observations?format=csv')}><Download size={15} /> Full processed dataset (CSV)</a>}>
        A registry of every dataset used, the official MPI framework, the formulas behind each calculated value, and the limits of what this project can say.
      </PageHeader>

      <Callout tone="info" title="Independence statement" className="mb-6">
        Imboni is built by DataMinds, a student team, for the NISR 2026 Big Data Hackathon. It is not an official NISR product and is not endorsed by NISR.
        Official statistics are reproduced from public NISR publications and cited; nothing here replaces the original reports.
      </Callout>

      <Card>
        <CardTitle title="Source registry" subtitle="Raw files are kept unchanged in data/raw with SHA-256 checksums and retrieval dates (data/metadata/retrieval_log.json)." />
        {src.loading && <LoadingBlock rows={2} />}
        {src.error && <ErrorState error={src.error} onRetry={src.reload} />}
        <div className="space-y-3">
          {src.data?.map((s) => (
            <details key={s.id} className="group rounded-2xl border border-line bg-white p-4 open:bg-paper/50">
              <summary className="flex cursor-pointer list-none flex-wrap items-center gap-3">
                <span className="flex-1 font-semibold text-ink-900">{s.title}</span>
                {s.access.startsWith('registration') ? <span className="chip border-amber-300 bg-amber-50 text-amber-900"><Lock size={11} /> not downloaded</span>
                  : <span className="chip border-brand-200 bg-brand-50 text-brand-700">{s.format.toUpperCase()} · public</span>}
                <span className="chip border-line bg-white text-text-2">{s.period}</span>
              </summary>
              <dl className="mt-3 grid gap-x-6 gap-y-2 text-[12.5px] md:grid-cols-2">
                <div><dt className="text-muted">Publisher</dt><dd>{s.publisher}</dd></div>
                <div><dt className="text-muted">Access / licence</dt><dd>{s.access} — {s.license}</dd></div>
                <div className="md:col-span-2"><dt className="text-muted">Used for</dt><dd>{s.used_for}</dd></div>
                {s.caveat && <div className="md:col-span-2"><dt className="text-muted">Caveat</dt><dd className="text-amber-900">{s.caveat}</dd></div>}
                <div><dt className="text-muted">File</dt><dd className="font-mono text-[11.5px]">{s.file ?? '—'}</dd></div>
                <div><dt className="text-muted">Retrieved · SHA-256</dt><dd className="font-mono text-[11.5px] break-all">{s.retrieval ? `${s.retrieval.retrieved_at} · ${s.retrieval.sha256.slice(0, 24)}…` : '—'}</dd></div>
                <div className="md:col-span-2"><dt className="text-muted">Citation</dt><dd>{s.citation}</dd></div>
                <div className="md:col-span-2"><a className="link inline-flex items-center gap-1" href={s.landing_page || s.url} target="_blank" rel="noreferrer">Official page <ExternalLink size={12} /></a></div>
              </dl>
            </details>
          ))}
        </div>
      </Card>

      {framework && (
        <Card className="mt-6">
          <CardTitle title={framework.name} subtitle={`${framework.method}. ${framework.poverty_cutoff_label}. Identification: ${framework.unit_of_identification}; analysis: ${framework.unit_of_analysis}.`} right={<StatusBadge status="official" />} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-[13px]">
              <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted"><th className="py-2 pr-3">Dimension</th><th className="py-2 pr-3">Indicator</th><th className="py-2 pr-3">Weight</th><th className="py-2">Deprived if…</th></tr></thead>
              <tbody>{framework.indicators.map((i) => <tr key={i.id} className="border-b border-line/70 align-top"><td className="py-2 pr-3 text-text-2">{i.dimension}</td><td className="py-2 pr-3 font-semibold">{i.label}</td><td className="tabular py-2 pr-3">{i.weight_label}</td><td className="py-2 text-text-2">{i.deprived_if}</td></tr>)}</tbody>
            </table>
          </div>
          <p className="mt-4 text-[12px] font-semibold text-ink-900">Changes from the EICV5 MPI (as stated by NISR)</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-[12.5px] text-text-2">{framework.changes_vs_eicv5.map((c) => <li key={c}>{c}</li>)}</ul>
          <p className="mt-3 text-[11px] text-muted">Source: {framework.source}</p>
        </Card>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle title="Formulas used for calculated values" />
          <ul className="space-y-3">{FORMULAS.map(([t, f, n]) => (
            <li key={t}><p className="text-[13px] font-semibold text-ink-900">{t}</p><p className="mt-0.5 rounded-lg bg-paper px-2 py-1 font-mono text-[12px] text-ink-900">{f}</p><p className="mt-0.5 text-[12px] text-muted">{n}</p></li>
          ))}</ul>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardTitle title="Status labels" />
            <ul className="space-y-2 text-[13px] text-text-2">
              <li className="flex gap-2"><StatusBadge status="official" /> Printed in an official NISR Excel table, reproduced unchanged.</li>
              <li className="flex gap-2"><StatusBadge status="official_transcribed" /> Official value transcribed from a published figure/PDF text; programmatically extracted and checked.</li>
              <li className="flex gap-2"><StatusBadge status="calculated" /> Derived by Imboni from official values with a published formula.</li>
              <li className="flex gap-2"><StatusBadge status="illustrative" /> Depends on user/placeholder assumptions (simulator).</li>
              <li className="flex gap-2"><StatusBadge status="experimental" /> Research method by Imboni, not an official measure.</li>
            </ul>
          </Card>
          <Card>
            <CardTitle title="Known limitations" />
            <ul className="list-disc space-y-1 pl-5 text-[13px] leading-relaxed text-text-2">
              <li>Only public aggregate tables are used; EICV7 microdata require registration and were not accessed.</li>
              <li>No district-level MPI exists; district profiles show the parent province for MPI context.</li>
              <li>FinScope (adults 16+, 2024) and EICV7 (households/population, 2023/24) differ in universe and period.</li>
              <li>FinScope district values are transcribed rounded chart labels.</li>
              <li>Simulator unit costs are placeholders; outputs are not forecasts of poverty reduction.</li>
              <li>Significance tests are approximate and not adjusted for multiple comparisons (except correlations, which use FDR).</li>
            </ul>
          </Card>
          <Card>
            <CardTitle title="AI assistance disclosure" />
            <p className="text-[13px] leading-relaxed text-text-2">This project was built with the help of an AI coding assistant (Anthropic's Claude) for code generation, data-pipeline scaffolding and
              documentation drafting. The DataMinds team reviewed, tested and is responsible for all content. All statistics come from the cited official sources;
              the application itself uses no external AI service. See <span className="font-mono text-[12px]">docs/AI_DISCLOSURE.md</span>.</p>
          </Card>
        </div>
      </div>
    </div>
  )
}
