import clsx from 'clsx'
import { BookOpenCheck, Calculator, ChartNoAxesCombined, Landmark, LayoutDashboard, Map, Menu, MessageSquareText, Microscope, X, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'

export const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/explorer', label: 'Explorer', icon: Map },
  { to: '/profile/district/nyamagabe', match: '/profile', label: 'Profiles', icon: UserRound },
  { to: '/financial-inclusion', label: 'Financial inclusion', icon: Landmark },
  { to: '/simulator', label: 'Simulator', icon: Calculator },
  { to: '/analysis', label: 'Analysis', icon: Microscope },
  { to: '/ask', label: 'Ask', icon: MessageSquareText },
  { to: '/sources', label: 'Sources & methods', icon: BookOpenCheck },
]

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 64 64" aria-hidden>
        <rect width="64" height="64" rx="16" fill={light ? '#ffffff14' : '#0b1a2b'} />
        <path d="M10 34c6-9 13.5-14 22-14s16 5 22 14c-6 9-13.5 14-22 14S16 43 10 34Z" fill="none" stroke="#5fd0c0" strokeWidth="4" strokeLinejoin="round" />
        <circle cx="32" cy="34" r="7.5" fill="#5fd0c0" />
        <circle cx="32" cy="34" r="3" fill={light ? '#0b1a2b' : '#0b1a2b'} />
      </svg>
      <span className={clsx('h-display text-[21px] font-semibold leading-none', light ? 'text-white' : 'text-ink-900')}>Imboni</span>
    </span>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const loc = useLocation()
  useEffect(() => { setOpen(false); window.scrollTo({ top: 0 }) }, [loc.pathname])
  const isLanding = loc.pathname === '/'

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-[100] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:shadow">Skip to content</a>
      <header className={clsx('sticky top-0 z-50 border-b backdrop-blur-md', isLanding ? 'border-white/10 bg-ink-950/80' : 'border-line bg-paper/85')}>
        <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" aria-label="Imboni home"><Logo light={isLanding} /></Link>
          <nav aria-label="Main" className="hidden items-center gap-0.5 xl:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to}
                className={({ isActive }) => {
                  const active = isActive || (n.match && loc.pathname.startsWith(n.match))
                  return clsx('rounded-full px-3 py-1.5 text-[13px] font-semibold transition-colors',
                    isLanding ? (active ? 'bg-white/15 text-white' : 'text-white/70 hover:text-white')
                      : (active ? 'bg-ink-900 text-white' : 'text-text-2 hover:bg-paper-2 hover:text-ink-900'))
                }}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <button className={clsx('rounded-full p-2 xl:hidden', isLanding ? 'text-white' : 'text-ink-900')} aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen((o) => !o)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
        {open && (
          <nav id="mobile-nav" aria-label="Mobile" className="border-t border-line bg-white px-4 py-3 xl:hidden">
            <ul className="grid gap-1 sm:grid-cols-2">
              {NAV.map((n) => (
                <li key={n.to}>
                  <NavLink to={n.to} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-ink-900 hover:bg-paper">
                    <n.icon size={17} className="text-brand-600" /> {n.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="mt-16 border-t border-line bg-white">
        <div className="mx-auto grid max-w-[1320px] gap-8 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-md text-[13px] leading-relaxed text-text-2">
              <strong className="text-ink-900">Imboni</strong> is a student project by team <strong className="text-ink-900">DataMinds</strong> for the
              NISR 2026 Big Data Hackathon (Financial Inclusion &amp; Poverty Reduction track). It is <strong>not</strong> an official NISR publication
              and is not endorsed by NISR. Statistics are reproduced from cited official sources; calculated, transcribed and illustrative values are labelled.
            </p>
          </div>
          <div>
            <p className="eyebrow mb-3">Explore</p>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[13px]">
              {NAV.map((n) => <li key={n.to}><Link className="text-text-2 hover:text-brand-600" to={n.to}>{n.label}</Link></li>)}
            </ul>
          </div>
          <div className="text-[12px] leading-relaxed text-text-2">
            <p className="eyebrow mb-3">Data &amp; credits</p>
            <p>Statistics: NISR — EICV7 (2023/24), FinScope Rwanda 2024, Census 2022.</p>
            <p className="mt-1">Boundaries: <a className="link" href="https://www.geoboundaries.org/" target="_blank" rel="noreferrer">geoBoundaries</a> (CC BY 4.0).</p>
            <p className="mt-1">Photos: Wikimedia Commons (CC0) — Synkubito; Germain92.</p>
            <p className="mt-3 flex items-center gap-1.5 text-muted"><ChartNoAxesCombined size={13} /> From Data to Development Action</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
