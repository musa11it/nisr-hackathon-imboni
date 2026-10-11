import { ArrowUp, MessageSquareText, Sparkles } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { BarList } from '../components/charts'
import { Callout, Card, ErrorState, PageHeader, SourceLink, StatusBadge } from '../components/ui'
import { apiFetch, useApi, type ApiError } from '../lib/api'
import { fmt } from '../lib/format'
import type { IndicatorMeta, SourceRef } from '../lib/types'

interface Answer {
  kind: 'value' | 'comparison' | 'ranking' | 'list' | 'definition' | 'unavailable' | 'unmatched'
  answer: string
  indicator: IndicatorMeta | null
  rows: any[]
  chart: { type: 'bar'; x: string; y: string; unit: string } | null
  caveats: string[]
  sources: SourceRef[]
  examples: string[] | null
}

export default function Ask() {
  const examples = useApi<string[]>('/api/ask/examples')
  const [q, setQ] = useState('')
  const [history, setHistory] = useState<{ q: string; a: Answer }[]>([])
  const [error, setError] = useState<ApiError | null>(null)
  const [busy, setBusy] = useState(false)

  const ask = async (question: string) => {
    if (!question.trim()) return
    setBusy(true); setError(null)
    try {
      const a = await apiFetch<Answer>('/api/ask', { method: 'POST', body: JSON.stringify({ question }) })
      setHistory((h) => [{ q: question, a }, ...h].slice(0, 12))
      setQ('')
    } catch (e) { setError(e as ApiError) } finally { setBusy(false) }
  }
  const submit = (e: FormEvent) => { e.preventDefault(); ask(q) }

  return (
    <div className="mx-auto max-w-[1000px] px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Natural-language data explorer" title="Ask the data">
        Questions are matched to validated statistics with transparent rules — no language model, no API key, no invented answers. If a question can't
        be answered from published data, Imboni says so.
      </PageHeader>

      <form onSubmit={submit} className="card flex items-center gap-2 p-2 pl-4">
        <MessageSquareText size={18} className="shrink-0 text-brand-600" aria-hidden />
        <label htmlFor="q" className="sr-only">Your question</label>
        <input id="q" className="flex-1 bg-transparent py-2 text-[15px] outline-none placeholder:text-muted" maxLength={300} placeholder="e.g. Which districts have the highest poverty rate?"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-primary !rounded-full !p-2.5" disabled={busy || !q.trim()} aria-label="Ask"><ArrowUp size={18} /></button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {(examples.data ?? []).map((ex) => (
          <button key={ex} onClick={() => ask(ex)} className="chip border-line-strong bg-white py-1 text-[12px] font-medium text-text-2 hover:border-brand-300 hover:text-brand-700">
            <Sparkles size={11} className="text-brand-500" /> {ex}
          </button>
        ))}
      </div>

      {error && <div className="mt-6"><ErrorState error={error} /></div>}
      <div className="mt-8 space-y-5" aria-live="polite">
        {history.map(({ q, a }, i) => (
          <Card key={history.length - i} as="article">
            <p className="text-[12px] font-semibold uppercase tracking-wide text-muted">You asked</p>
            <p className="mt-0.5 font-semibold text-ink-900">{q}</p>
            <div className="mt-4 rounded-2xl bg-paper p-4">
              <p className="text-[15px] leading-relaxed text-ink-900">{a.answer}</p>
              {a.indicator && (
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px] text-text-2">
                  <StatusBadge status={a.indicator.status} /><span className="chip border-line bg-white">{a.indicator.period}</span>
                  <span>{a.indicator.universe}</span>
                </div>
              )}
            </div>
            {a.chart && a.rows.length > 1 && (
              <div className="mt-4">
                <BarList unit={a.chart.unit} decimals={a.chart.unit.startsWith('index') ? 3 : 1} color="#1d8477"
                  data={a.rows.map((r: any, j: number) => ({ key: `${j}`, label: r[a.chart!.x] ?? r.label, value: r[a.chart!.y] ?? r.value }))} />
              </div>
            )}
            {a.kind === 'list' && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-[12.5px]">
                  <thead><tr className="border-b border-line text-[11px] uppercase tracking-wide text-muted"><th className="py-2 pr-3">Indicator</th><th className="py-2 pr-3">Levels</th><th className="py-2 pr-3">Status</th><th className="py-2">Source</th></tr></thead>
                  <tbody>{a.rows.map((r: any) => <tr key={r.indicator} className="border-b border-line/70"><td className="py-1.5 pr-3 font-semibold">{r.indicator}</td><td className="py-1.5 pr-3 text-text-2">{r.levels}</td><td className="py-1.5 pr-3 text-text-2">{r.status.replace(/_/g, ' ')}</td><td className="py-1.5 text-text-2">{r.source}</td></tr>)}</tbody>
                </table>
              </div>
            )}
            {a.kind === 'value' && a.rows[0]?.value != null && a.rows[0]?.flags?.length > 0 && (
              <p className="mt-3 text-[12px] text-muted">Flags: {a.rows[0].flags.join(', ')}</p>
            )}
            {a.kind === 'definition' && a.indicator && a.rows[0] && (
              <p className="mt-3 text-[13px] text-text-2">National value: <strong>{fmt(a.rows[0].value, a.indicator.unit, a.indicator.decimals)}</strong></p>
            )}
            {a.caveats.length > 0 && <Callout tone="warn" className="mt-4"><ul className="list-disc space-y-0.5 pl-4">{a.caveats.map((c) => <li key={c}>{c}</li>)}</ul></Callout>}
            {a.sources.length > 0 && <div className="mt-3 flex flex-wrap gap-3">{a.sources.map((s) => <SourceLink key={s.id} source={s} />)}</div>}
            {a.kind === 'unmatched' && a.examples && <p className="mt-3 text-[13px] text-text-2">Try: {a.examples.slice(0, 3).join(' · ')}</p>}
          </Card>
        ))}
      </div>
    </div>
  )
}
