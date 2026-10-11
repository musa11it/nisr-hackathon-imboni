import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { LoadingBlock } from './components/ui'
import Landing from './pages/Landing'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Explorer = lazy(() => import('./pages/Explorer'))
const Profile = lazy(() => import('./pages/Profile'))
const Financial = lazy(() => import('./pages/Financial'))
const Simulator = lazy(() => import('./pages/Simulator'))
const Analysis = lazy(() => import('./pages/Analysis'))
const Ask = lazy(() => import('./pages/Ask'))
const Sources = lazy(() => import('./pages/Sources'))

function Page({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="mx-auto max-w-[1320px] px-4 py-10 sm:px-6"><LoadingBlock rows={4} /></div>}>
      {children}
    </Suspense>
  )
}

function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-6 py-24 text-center">
      <p className="eyebrow">404</p>
      <h1 className="h-display mt-2 text-3xl font-semibold">Page not found</h1>
      <p className="mt-3 text-text-2">The page you requested does not exist.</p>
      <Link to="/" className="btn-primary mt-6">Back to Imboni</Link>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Landing />} />
          <Route path="dashboard" element={<Page><Dashboard /></Page>} />
          <Route path="explorer" element={<Page><Explorer /></Page>} />
          <Route path="profile/:level/:geoId" element={<Page><Profile /></Page>} />
          <Route path="financial-inclusion" element={<Page><Financial /></Page>} />
          <Route path="simulator" element={<Page><Simulator /></Page>} />
          <Route path="analysis" element={<Page><Analysis /></Page>} />
          <Route path="ask" element={<Page><Ask /></Page>} />
          <Route path="sources" element={<Page><Sources /></Page>} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
