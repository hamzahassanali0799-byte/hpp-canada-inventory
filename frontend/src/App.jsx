import { useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { ScanLine, FileSpreadsheet, Menu, X, Home as HomeIcon } from 'lucide-react'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import ScanPage from './pages/ScanPage'
import JournalPanel from './components/JournalPanel'
import { ARTE_NAVY } from './components/CitrusIcon'

const NAV = [
  { to: '/', icon: HomeIcon, label: 'Home', end: true },
  { to: '/scan', icon: ScanLine, label: 'Invoice Scan', end: false },
]

export default function App() {
  const [journalOpen, setJournalOpen] = useState(false)
  const [journalKey, setJournalKey] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen flex bg-stone-50 text-stone-900">
      {/* Mobile menu button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-50 p-2 bg-white rounded-xl md:hidden border border-stone-200 shadow-sm"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar */}
      <aside className={`fixed md:static inset-y-0 left-0 z-40 w-60 flex flex-col transition-transform duration-200 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`} style={{ backgroundColor: ARTE_NAVY }}>
        {/* Logo / branding */}
        <div className="p-5 pb-4 flex items-center gap-3">
          <img src="/hpp-logo.png" alt="HPP Canada" className="h-10 w-10 object-contain rounded-lg" />
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white">HPP Canada</h1>
            <p className="text-[9px] text-white/40 uppercase tracking-[0.2em] font-bold">Inventory</p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 pt-2 space-y-1">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? 'bg-white/15 text-white shadow-sm'
                    : 'text-white/50 hover:text-white hover:bg-white/10'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}

          {/* Journal — opens side panel */}
          <button
            onClick={() => { setJournalOpen(true); setJournalKey((k) => k + 1); setSidebarOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-white/50 hover:text-white hover:bg-white/10 transition"
          >
            <FileSpreadsheet size={18} />
            Journal
          </button>
        </nav>

        {/* Bottom branding */}
        <div className="p-4 pt-2">
          <div className="rounded-xl bg-white/5 p-3">
            <p className="text-[9px] text-white/30 uppercase tracking-widest font-bold">Processing Facility</p>
            <p className="text-[10px] text-white/50 mt-0.5">Delta, BC</p>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main content */}
      <main className="flex-1 p-3 pt-14 md:pt-8 md:p-8 overflow-auto">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/brand/:brand" element={<Dashboard />} />
          <Route path="/scan" element={<ScanPage />} />
        </Routes>
      </main>

      {/* Journal side panel */}
      <JournalPanel open={journalOpen} onClose={() => setJournalOpen(false)} refreshKey={journalKey} />
    </div>
  )
}
