import { ArrowRight, BadgeCheck, Calculator, Database, FileDown, Landmark, Map, MessageSquareText, Microscope, ScanSearch, ShieldCheck, Sparkles, Workflow } from 'lucide-react'
import { Link } from 'react-router-dom'
import { StatusBadge } from '../components/ui'
import { useApi } from '../lib/api'
import { fmt, pct } from '../lib/format'
import type { Metric } from '../lib/types'

interface Dash {
  kpis: Record<string, any>
  overlap: { cells: Record<string, number>; either: number; share_of_monetary_poor_also_mpi_poor: number }
  validation: { total: number; passed: number; errors: number; warnings: number }
}

function HeroStat({ m, label, unit = '%' }: { m?: Metric | null; label: string; unit?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 backdrop-blur-sm">
      <p className="text-[11px] font-medium text-white/60">{label}</p>
      <p className="tabular mt-1 text-[28px] font-semibold leading-none text-white">
        {m ? fmt(m.value, unit, m.unit?.startsWith('index') ? 3 : 1) : <span className="inline-block h-7 w-16 animate-pulse rounded bg-white/10" />}
      </p>
      <p className="mt-2 text-[10.5px] text-white/50">{m ? `${m.source.short} · ${m.period}` : ' '}</p>
    </div>
  )
}

const STEPS = [
  { icon: Database, title: 'Acquire', text: 'Official NISR Excel and PDF publications are downloaded unchanged, checksummed and logged with retrieval dates.' },
  { icon: ShieldCheck, title: 'Validate', text: '189 automated checks: published benchmarks, H×A = M0, Σw·CH, totals, ranges, duplicates and CI coherence.' },
  { icon: ScanSearch, title: 'Explain', text: 'Every figure carries its definition, period, universe, source table and status — official, transcribed or calculated.' },
  { icon: Calculator, title: 'Simulate', text: 'Planners test budget allocations against measured deprivation, with transparent, editable assumptions.' },
]

const FEATURES = [
  { to: '/dashboard', icon: Sparkles, title: 'Intelligence dashboard', text: 'Verified headline indicators with definitions, periods, sources and uncertainty.' },
  { to: '/explorer', icon: Map, title: 'Geographic explorer', text: 'District and province choropleths with confidence intervals and rank uncertainty.' },
  { to: '/profile/district/nyamagabe', icon: ScanSearch, title: 'Deprivation fingerprints', text: 'Every district and province against national and peer values — with significance tests.' },
  { to: '/financial-inclusion', icon: Landmark, title: 'Financial inclusion', text: 'FinScope 2024 access strand for 30 districts, EICV7 savings & MoMo, VUP payment channels.' },
  { to: '/simulator', icon: Calculator, title: 'Budget simulator', text: 'Allocate a budget, see reach, coverage of need and cost sensitivity. Save, compare, export.' },
  { to: '/analysis', icon: Microscope, title: 'Explainable statistics', text: 'Validation, correlations with FDR control, MPI sensitivity, trends and an experimental index.' },
  { to: '/ask', icon: MessageSquareText, title: 'Ask the data', text: 'Plain-language questions answered only from validated, cited statistics. No AI key needed.' },
  { to: '/sources', icon: FileDown, title: 'Reports & sources', text: 'PDF briefs, CSV exports, a full source registry and every formula used.' },
]

export default function Landing() {
  const { data } = useApi<Dash>('/api/dashboard')
  const k = data?.kpis
  const ov = data?.overlap

  return (
    <div>
      {/* ------------------------------------------------ hero */}
      <section className="relative -mt-16 overflow-hidden bg-ink-950 pt-16 text-white">
        <img src="/images/hills-western-rwanda.jpg" alt="Terraced tea hills in Western Rwanda under a cloudy sky"
          className="absolute inset-0 h-full w-full object-cover opacity-40" fetchPriority="high" />
        <div className="absolute inset-0 bg-gradient-to-r from-ink-950 via-ink-950/85 to-ink-950/30" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-transparent to-transparent" aria-hidden />
        <div className="relative mx-auto grid max-w-[1320px] gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.25fr_1fr] lg:pb-28 lg:pt-24">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-glow">
              NISR 2026 Big Data Hackathon · Financial Inclusion &amp; Poverty Reduction
            </p>
            <h1 className="h-display mt-6 text-[42px] font-semibold leading-[1.04] sm:text-6xl">
              From data to <span className="text-emerald-glow">development action</span>.
            </h1>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-white/75">
              <strong className="text-white">Imboni</strong> turns Rwanda's official poverty and financial-inclusion statistics into
              explainable evidence — where deprivation is concentrated, how certain we are, and what a budget could reach.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/dashboard" className="btn bg-emerald-glow px-5 py-2.5 text-ink-950 hover:bg-white">Open the dashboard <ArrowRight size={16} /></Link>
              <Link to="/simulator" className="btn border border-white/25 px-5 py-2.5 text-white hover:bg-white/10">Try the budget simulator</Link>
            </div>
            <p className="mt-6 text-[12px] text-white/50">A student project by team DataMinds · Not an official NISR publication</p>
          </div>
          <div className="self-end">
            <div className="grid grid-cols-2 gap-3">
              <HeroStat m={k?.poverty_rate} label="Monetary poverty rate" />
              <HeroStat m={k?.mpi_incidence} label="Multidimensional poverty incidence" />
              <HeroStat m={k?.mpi} label="Multidimensional Poverty Index" unit="index (0–1)" />
              <HeroStat m={k?.hh_savings_account} label="Households with a savings account" />
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-[11px] text-white/55">
              <BadgeCheck size={13} className="text-emerald-glow" /> Live from the validated pipeline
              {data && <> · {data.validation.passed}/{data.validation.total} automated checks passed</>}
            </p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ insight */}
      <section className="mx-auto max-w-[1320px] px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <p className="eyebrow">The challenge</p>
            <h2 className="h-display mt-3 text-3xl font-semibold text-ink-900 sm:text-[40px] sm:leading-tight">
              Two official lenses on poverty find <em className="text-brand-600 not-italic">different people</em>.
            </h2>
            <p className="mt-5 text-[15px] leading-relaxed text-text-2">
              Track 2 asks teams to "use data to understand financial exclusion, poverty dynamics, and the impact of social protection programs".
              EICV7 measures poverty two ways: <strong>consumption</strong> below the national poverty line, and <strong>multidimensional
              deprivation</strong> across education, health, basic services and living standards. They overlap far less than most people assume —
              so programmes targeted on one lens miss many people visible only in the other.
            </p>
            <Link to="/analysis" className="link mt-5 inline-flex items-center gap-1 text-sm">See the overlap analysis <ArrowRight size={14} /></Link>
          </div>
          <div className="card card-pad">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-ink-900">Share of Rwanda's population, EICV7 2023/24</p>
              <StatusBadge status="official" />
            </div>
            <div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
              <span />
              <span className="pb-1 text-center text-[11px] font-semibold text-muted">Monetary poor</span>
              <span className="pb-1 text-center text-[11px] font-semibold text-muted">Not monetary poor</span>
              <span className="self-center pr-2 text-right text-[11px] font-semibold text-muted">MPI-poor</span>
              <Cell v={ov?.cells.mpi_poor__monetary_poor} label="Poor on both" strong />
              <Cell v={ov?.cells.mpi_poor__monetary_nonpoor} label="MPI-poor only" />
              <span className="self-center pr-2 text-right text-[11px] font-semibold text-muted">Not MPI-poor</span>
              <Cell v={ov?.cells.mpi_nonpoor__monetary_poor} label="Monetary-poor only" />
              <Cell v={ov?.cells.mpi_nonpoor__monetary_nonpoor} label="Neither" muted />
            </div>
            <div className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-2">
              <p className="text-[13px] text-text-2"><span className="tabular text-xl font-semibold text-ink-900">{pct(ov?.either)}</span><br />poor on at least one measure <StatusBadge status="calculated" className="ml-1" /></p>
              <p className="text-[13px] text-text-2"><span className="tabular text-xl font-semibold text-ink-900">{pct(ov?.share_of_monetary_poor_also_mpi_poor, 0)}</span><br />of the monetary poor are also MPI-poor <StatusBadge status="calculated" className="ml-1" /></p>
            </div>
            <p className="mt-3 text-[11px] text-muted">Source: NISR, EICV7 Multidimensional Poverty Thematic Report, Table 3.1 (k = 33.3%, national poverty line).</p>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ how */}
      <section className="border-y border-line bg-white">
        <div className="mx-auto max-w-[1320px] px-4 py-20 sm:px-6">
          <div className="max-w-2xl">
            <p className="eyebrow">How Imboni works</p>
            <h2 className="h-display mt-3 text-3xl font-semibold text-ink-900">A reproducible path from official tables to decisions</h2>
          </div>
          <ol className="mt-10 grid gap-4 md:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative rounded-2xl border border-line bg-paper p-5">
                <span className="absolute right-4 top-4 font-display text-4xl font-semibold text-line-strong/70" aria-hidden>{i + 1}</span>
                <s.icon size={22} className="text-brand-600" aria-hidden />
                <h3 className="mt-4 font-semibold text-ink-900">{s.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-text-2">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------ capabilities */}
      <section className="mx-auto max-w-[1320px] px-4 py-20 sm:px-6">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div className="max-w-2xl">
            <p className="eyebrow">Capabilities</p>
            <h2 className="h-display mt-3 text-3xl font-semibold text-ink-900">Built for planners, analysts and development partners</h2>
          </div>
          <Link to="/sources" className="btn-ghost"><Workflow size={15} /> Methods &amp; sources</Link>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <Link key={f.to} to={f.to} className="card group p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition-colors group-hover:bg-brand-600 group-hover:text-white">
                <f.icon size={19} aria-hidden />
              </span>
              <h3 className="mt-4 font-semibold text-ink-900">{f.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-text-2">{f.text}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-[12px] font-semibold text-brand-600">Open <ArrowRight size={13} /></span>
            </Link>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------ principles + photo */}
      <section className="mx-auto max-w-[1320px] px-4 sm:px-6">
        <div className="grid overflow-hidden rounded-[28px] bg-ink-900 text-white lg:grid-cols-2">
          <div className="relative min-h-72">
            <img src="/images/tea-harvest.jpg" alt="A tea picker with a woven basket harvesting leaves on a Rwandan hillside" loading="lazy"
              className="absolute inset-0 h-full w-full object-cover" />
          </div>
          <div className="p-8 sm:p-12">
            <p className="eyebrow text-emerald-glow">Honest by design</p>
            <h2 className="h-display mt-3 text-3xl font-semibold">Every number traceable. No invented data.</h2>
            <ul className="mt-6 space-y-3 text-[14px] leading-relaxed text-white/75">
              {[
                'Monetary poverty and MPI incidence are never presented as interchangeable.',
                'District values only where NISR publishes them — MPI stays at province level.',
                'Collected-but-unpublished variables (credit, loan sources) are shown as unavailable, not estimated.',
                'Simulator outputs are labelled illustrative: budget arithmetic, not predicted poverty reduction.',
                'Source inconsistencies found during validation are documented, not silently fixed.',
              ].map((t) => <li key={t} className="flex gap-3"><BadgeCheck size={17} className="mt-0.5 shrink-0 text-emerald-glow" aria-hidden />{t}</li>)}
            </ul>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1320px] px-4 pt-16 sm:px-6">
        <p className="eyebrow">Official data sources</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['EICV7 Main Indicators 2023/24', 'Poverty, services and 30-district estimates with standard errors'],
            ['EICV7 Multidimensional Poverty', 'Rwanda national MPI: 13 indicators, 4 dimensions'],
            ['FinScope Rwanda 2024', 'Financial access strand, including 30 districts'],
            ['Census 2022 (PHC5)', 'Households and household size by district'],
          ].map(([t, d]) => (
            <div key={t} className="rounded-2xl border border-line bg-white px-4 py-3.5">
              <p className="text-[13px] font-semibold text-ink-900">{t}</p>
              <p className="mt-0.5 text-[12px] text-muted">{d}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

function Cell({ v, label, strong, muted }: { v?: number; label: string; strong?: boolean; muted?: boolean }) {
  return (
    <div className={`rounded-xl px-3 py-3 text-center ${strong ? 'bg-ink-900 text-white' : muted ? 'bg-paper text-text-2' : 'bg-brand-50 text-brand-800'}`}>
      <p className="tabular text-2xl font-semibold">{v == null ? '—' : pct(v)}</p>
      <p className={`text-[11px] ${strong ? 'text-white/70' : 'text-muted'}`}>{label}</p>
    </div>
  )
}
