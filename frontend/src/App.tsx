import { lazy, Suspense, useState } from 'react'
import { Activity, BarChart3, Wind } from 'lucide-react'

const AccuracyView = lazy(() => import('./views/AccuracyView'))
const DecisionView = lazy(() => import('./views/DecisionView'))
const HorizonView = lazy(() => import('./views/HorizonView'))

type View = 'decision' | 'accuracy' | 'horizon'

const navigation: { id: View; label: string; icon: typeof Wind }[] = [
  { id: 'decision', label: 'Decision view', icon: Wind },
  { id: 'accuracy', label: 'Accuracy', icon: BarChart3 },
  { id: 'horizon', label: 'Horizon analysis', icon: Activity },
]

export default function App() {
  const [view, setView] = useState<View>('decision')
  return (
    <div className="app-container">
      <header className="nav-header">
        <div className="nav-inner">
          <a className="nav-brand" href="#" onClick={(event) => { event.preventDefault(); setView('decision') }}>
            <span className="brand-symbol"><Wind size={20} /></span>
            <span><strong className="nav-brand-text">Northstar</strong><small className="nav-brand-subtitle">Wind procurement intelligence</small></span>
          </a>
          <nav className="nav-links" aria-label="Primary navigation">
            {navigation.map(({ id, label, icon: Icon }) => (
              <button
                className={`nav-link ${view === id ? 'active' : ''}`}
                key={id}
                type="button"
                aria-current={view === id ? 'page' : undefined}
                onClick={() => setView(id)}
              >
                <Icon size={16} /><span>{label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="main-content">
        <Suspense fallback={<div className="loading-state"><span className="loading-spinner" />Preparing workspace…</div>}>
          {view === 'decision' && <DecisionView />}
          {view === 'accuracy' && <AccuracyView />}
          {view === 'horizon' && <HorizonView />}
        </Suspense>
      </main>
      <footer className="app-footer">
        <span>National wind · Elexon BMRS FUELHH + WINDFOR · January 2026</span>
        <span>Decision support only · Validate against your trading process</span>
      </footer>
    </div>
  )
}
