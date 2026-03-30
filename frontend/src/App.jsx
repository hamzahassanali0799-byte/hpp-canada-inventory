import { useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { LayoutGrid, ScanLine, FileSpreadsheet, Menu, X } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import ScanPage from './pages/ScanPage'
import JournalPanel from './components/JournalPanel'
import { ARTE_NAVY } from './components/CitrusIcon'

const NAV = [
  { to: '/', icon: LayoutGrid, label: 'Dashboard' },
  { to: '/scan', icon: ScanLine, label: 'Invoice Scan' },
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
      <aside className={`fixed md:static inset-y-0 left-0 z-40 w-60 bg-white border-r border-stone-200 flex flex-col transition-transform duration-200 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      }`}>
        <div className="p-4 border-b border-stone-100 flex items-center gap-3">
          <img src="/hpp-logo.png" alt="HPP Canada" className="h-10 w-10 object-contain" />
          <div>
            <h1 className="text-sm font-bold tracking-tight" style={{ color: ARTE_NAVY }}>HPP Canada</h1>
            <p className="text-[9px] text-stone-400 uppercase tracking-[0.2em] font-bold">Inventory</p>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition ${
                  isActive
                    ? 'text-white shadow-sm'
                    : 'text-stone-500 hover:text-stone-800 hover:bg-stone-50'
                }`
              }
              style={({ isActive }) => isActive ? { backgroundColor: ARTE_NAVY } : {}}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Journal button */}
        <div className="p-3 border-t border-stone-100">
          <button
            onClick={() => { setJournalOpen(true); setJournalKey((k) => k + 1); setSidebarOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-stone-500 hover:text-stone-800 hover:bg-stone-50 transition"
          >
            <FileSpreadsheet size={18} />
            BC Journal
          </button>
        </div>

        {/* Footer - mini bottles */}
        <div className="p-4 border-t border-stone-100 flex items-center justify-center gap-1 opacity-40">
          {['orange', 'lime', 'lemon', 'grapefruit'].map((f) => (
            <img key={f} src={`/bottles/${f}.png`} alt={f} className="h-10 object-contain" />
          ))}
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main */}
      <main className="flex-1 p-3 pt-14 md:pt-8 md:p-8 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scan" element={<ScanPage />} />
        </Routes>
      </main>

      {/* Journal side panel */}
      <JournalPanel open={journalOpen} onClose={() => setJournalOpen(false)} refreshKey={journalKey} />
    </div>
  )
}
