import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tag, Wine, Leaf, Droplets, Box, Package, AlertTriangle } from 'lucide-react'
import { ARTE_NAVY, getBrandColor } from '../components/CitrusIcon'
import { fetchLabels } from '../api'

const CATEGORIES = [
  {
    key: 'juice',
    label: 'Juices',
    icon: Droplets,
    bg: 'bg-gradient-to-br from-orange-50 to-amber-50',
    iconBg: 'bg-orange-100',
    iconColor: 'text-orange-600',
    border: 'border-orange-200',
    accentColor: '#ea580c',
    emoji: '🧃',
  },
  {
    key: 'label',
    label: 'Labels',
    icon: Tag,
    bg: 'bg-gradient-to-br from-blue-50 to-indigo-50',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    border: 'border-blue-200',
    accentColor: '#2563eb',
    emoji: '🏷️',
  },
  {
    key: 'bottle',
    label: 'Bottles & Caps',
    icon: Wine,
    bg: 'bg-gradient-to-br from-violet-50 to-purple-50',
    iconBg: 'bg-violet-100',
    iconColor: 'text-violet-600',
    border: 'border-violet-200',
    accentColor: '#7c3aed',
    emoji: '🫙',
  },
  {
    key: 'box',
    label: 'Boxes',
    icon: Box,
    bg: 'bg-gradient-to-br from-amber-50 to-yellow-50',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-700',
    border: 'border-amber-200',
    accentColor: '#b45309',
    emoji: '📦',
  },
  {
    key: 'raw',
    label: 'Raw Ingredients',
    icon: Leaf,
    bg: 'bg-gradient-to-br from-green-50 to-emerald-50',
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
    border: 'border-green-200',
    accentColor: '#16a34a',
    emoji: '🌿',
  },
  {
    key: 'misc',
    label: 'Miscellaneous',
    icon: Package,
    bg: 'bg-gradient-to-br from-slate-50 to-gray-100',
    iconBg: 'bg-slate-100',
    iconColor: 'text-slate-500',
    border: 'border-slate-200',
    accentColor: '#64748b',
    emoji: '🔧',
  },
]

export default function Home() {
  const navigate = useNavigate()
  const [counts, setCounts] = useState({})
  const [totalItems, setTotalItems] = useState(0)
  const [totalStock, setTotalStock] = useState(0)
  const [lowStock, setLowStock] = useState([])

  useEffect(() => {
    fetchLabels().then((items) => {
      const c = {}
      let stock = 0
      for (const item of items) {
        c[item.category] = (c[item.category] || 0) + 1
        stock += item.current_stock_bottles
      }
      setCounts(c)
      setTotalItems(items.length)
      setTotalStock(stock)
      // Items with stock > 0 but running low (bottom 10 by stock, excluding 0)
      const withStock = items.filter(i => i.current_stock_bottles > 0 && i.current_stock_bottles < 100)
      withStock.sort((a, b) => a.current_stock_bottles - b.current_stock_bottles)
      setLowStock(withStock.slice(0, 8))
    }).catch(() => {})
  }, [])

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header with stats */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight" style={{ color: ARTE_NAVY }}>
          Inventory Dashboard
        </h1>
        <p className="text-stone-400 text-sm mt-1">HPP Canada Processing Facility</p>

        {/* Quick stats */}
        <div className="flex gap-3 mt-4">
          <div className="bg-white rounded-xl border border-stone-200 px-4 py-3 shadow-sm">
            <p className="text-[10px] text-stone-400 uppercase tracking-wider font-bold">Total SKUs</p>
            <p className="text-2xl font-extrabold" style={{ color: ARTE_NAVY }}>{totalItems}</p>
          </div>
          <div className="bg-white rounded-xl border border-stone-200 px-4 py-3 shadow-sm">
            <p className="text-[10px] text-stone-400 uppercase tracking-wider font-bold">Total Stock</p>
            <p className="text-2xl font-extrabold" style={{ color: ARTE_NAVY }}>{totalStock.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {/* Category grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        {CATEGORIES.map(({ key, label, icon: Icon, bg, iconBg, iconColor, border, accentColor, emoji }) => (
          <button
            key={key}
            onClick={() => navigate(`/brand/all?cat=${key}`)}
            className={`group relative ${bg} border ${border} rounded-2xl p-5 sm:p-6 text-left transition-all duration-200 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] cursor-pointer overflow-hidden`}
          >
            {/* Big faded emoji background */}
            <span className="absolute -right-2 -bottom-2 text-6xl sm:text-7xl opacity-[0.08] select-none pointer-events-none">
              {emoji}
            </span>

            <div className="flex items-start justify-between mb-3">
              <div className={`w-10 h-10 sm:w-12 sm:h-12 ${iconBg} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-200`}>
                <Icon size={22} className={iconColor} />
              </div>
              {counts[key] > 0 && (
                <span className="text-lg sm:text-xl font-extrabold" style={{ color: accentColor }}>
                  {counts[key]}
                </span>
              )}
            </div>

            <h3 className="text-sm sm:text-base font-bold text-stone-800">{label}</h3>
            <p className="text-[10px] sm:text-xs text-stone-400 mt-0.5 font-medium">
              {counts[key] ? `${counts[key]} items` : 'View & manage'}
            </p>

            {/* Arrow */}
            <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        ))}
      </div>
      {/* Running Low */}
      {lowStock.length > 0 && (
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={18} className="text-red-500" />
            <h2 className="text-base font-bold" style={{ color: ARTE_NAVY }}>Running Low</h2>
            <span className="text-xs text-stone-400 font-medium">(&lt; 100 units)</span>
          </div>
          <div className="bg-white rounded-2xl border border-red-100 divide-y divide-stone-100 overflow-hidden shadow-sm">
            {lowStock.map((item) => (
              <div key={item.id} className="flex items-center justify-between px-4 py-3 hover:bg-red-50/30 transition">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-stone-800 truncate">{item.flavor}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase text-white"
                      style={{ backgroundColor: getBrandColor(item.brand) }}>{item.brand}</span>
                    <span className="text-[10px] text-stone-400 font-mono">{item.item_code}</span>
                  </div>
                </div>
                <div className="text-right ml-3">
                  <span className="text-lg font-extrabold text-red-600">{item.current_stock_bottles}</span>
                  <p className="text-[9px] text-stone-400 uppercase font-bold">{item.unit_of_measure}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
