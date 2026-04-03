import { useState } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { ScanLine, FileSpreadsheet, Menu, X, Home as HomeIcon, ClipboardCheck, Search } from 'lucide-react'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import ScanPage from './pages/ScanPage'
import CountPage from './pages/CountPage'
import JournalPanel from './components/JournalPanel'
import { ARTE_NAVY } from './components/CitrusIcon'

const NAV = [
  { to: '/', icon: HomeIcon, label: 'Home', end: true },
  { to: '/scan', icon: ScanLine, label: 'Invoice Scan', end: false },
  { to: '/count', icon: ClipboardCheck, label: 'Cycle Count', end: false },
]

export default function App() {
  const [journalOpen, setJournalOpen] = useState(false)
  const [journalKey, setJournalKey] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      navigate(`/brand/all?cat=juice`)
      setSidebarOpen(false)
      // The Dashboard will pick up the search from the URL or we pass via state
      // For now, navigate to all inventory — user can filter from there
      window.__globalSearch = searchQuery.trim()
      navigate(`/brand/all?search=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery('')
    }
  }

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
        {/* Logo / branding */}
        <div className="p-4 border-b border-stone-100 flex items-center gap-3">
          <img src="/hpp-logo.png" alt="HPP Canada" className="h-10 w-10 object-contain" />
          <div>
            <h1 className="text-sm font-bold tracking-tight" style={{ color: ARTE_NAVY }}>HPP Canada</h1>
            <p className="text-[9px] text-stone-400 uppercase tracking-[0.2em] font-bold">Inventory</p>
          </div>
        </div>

        {/* Search */}
        <div className="px-3 pt-3">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-300" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="Search items..."
              className="w-full bg-stone-50 border border-stone-200 rounded-lg pl-8 pr-2 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-stone-300 transition"
            />
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
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

          {/* Journal — opens side panel */}
          <button
            onClick={() => { setJournalOpen(true); setJournalKey((k) => k + 1); setSidebarOpen(false) }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-stone-500 hover:text-stone-800 hover:bg-stone-50 transition"
          >
            <FileSpreadsheet size={18} />
            Journal
          </button>
        </nav>
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
          <Route path="/count" element={<CountPage />} />
        </Routes>
      </main>

      {/* Journal side panel */}
      <JournalPanel open={journalOpen} onClose={() => setJournalOpen(false)} refreshKey={journalKey} />
    </div>
  )
}
