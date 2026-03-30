import { useState, useEffect, useMemo } from 'react'
import { Search, Plus, RefreshCw, Droplets, Tag, Box, Package, Wine } from 'lucide-react'
import { fetchLabels } from '../api'
import LabelCard from '../components/LabelCard'
import AddLabelModal from '../components/AddLabelModal'
import { ARTE_NAVY, getBrandColor } from '../components/CitrusIcon'

const MAIN_TABS = [
  { key: 'juice', label: 'Juice', icon: Droplets },
  { key: 'bottle', label: 'Bottles', icon: Wine },
  { key: 'label', label: 'Labels', icon: Tag },
  { key: 'box', label: 'Boxes', icon: Box },
]

export default function Dashboard() {
  const [allItems, setAllItems] = useState([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('juice')
  const [sizeFilter, setSizeFilter] = useState('')
  const [brandFilter, setBrandFilter] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [editLabel, setEditLabel] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchLabels(search)
      setAllItems(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [search])

  // Filter items by category
  const catItems = useMemo(() => allItems.filter((i) => i.category === category), [allItems, category])

  // Available sizes for current category
  const sizes = useMemo(() => {
    const s = [...new Set(catItems.map((i) => i.size))]
    return s.sort()
  }, [catItems])

  // Available brands for current category
  const brands = useMemo(() => {
    const b = [...new Set(catItems.map((i) => i.brand))]
    return b.sort()
  }, [catItems])

  // Apply size + brand filters
  const filtered = useMemo(() => {
    let items = catItems
    if (sizeFilter) items = items.filter((i) => i.size === sizeFilter)
    if (brandFilter) items = items.filter((i) => i.brand === brandFilter)
    return items
  }, [catItems, sizeFilter, brandFilter])

  // Group by brand
  const grouped = useMemo(() => {
    const groups = {}
    for (const item of filtered) {
      if (!groups[item.brand]) groups[item.brand] = []
      groups[item.brand].push(item)
    }
    return groups
  }, [filtered])

  const totalUnits = filtered.reduce((s, l) => s + l.current_stock_bottles, 0)

  // Reset sub-filters when switching main tab
  const switchTab = (tab) => {
    setCategory(tab)
    setSizeFilter('')
    setBrandFilter('')
  }

  return (
    <div className="space-y-4">
      {/* Main category tabs + total */}
      <div className="flex items-center gap-2">
        <div className="flex-1 overflow-x-auto scrollbar-hide">
          <div className="flex rounded-xl overflow-hidden border border-stone-200 bg-white shadow-sm w-max">
            {MAIN_TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => switchTab(key)}
                className={`px-3 md:px-5 py-2 md:py-2.5 text-[10px] md:text-xs font-bold uppercase tracking-wider transition flex items-center gap-1.5 whitespace-nowrap ${
                  category === key ? 'text-white' : 'text-stone-400 hover:text-stone-600'
                }`}
                style={category === key ? { backgroundColor: ARTE_NAVY } : {}}
              >
                <Icon size={12} />
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-stone-200 px-3 py-2 shadow-sm flex-shrink-0">
          <span className="text-[9px] text-stone-400 uppercase tracking-widest font-bold">Total: </span>
          <span className="text-base font-bold" style={{ color: ARTE_NAVY }}>{totalUnits}</span>
        </div>
      </div>

      {/* Size sub-tabs + brand filter */}
      <div className="overflow-x-auto scrollbar-hide">
        <div className="flex items-center gap-2 w-max">
          {/* Size tabs */}
          {sizes.length > 1 && (
            <div className="flex rounded-lg overflow-hidden border border-stone-200 bg-white">
              <button
                onClick={() => setSizeFilter('')}
                className={`px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition whitespace-nowrap ${
                  !sizeFilter ? 'bg-stone-800 text-white' : 'text-stone-400'
                }`}
              >All Sizes</button>
              {sizes.map((s) => (
                <button
                  key={s}
                  onClick={() => setSizeFilter(s)}
                  className={`px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition whitespace-nowrap ${
                    sizeFilter === s ? 'bg-stone-800 text-white' : 'text-stone-400'
                  }`}
                >{s}</button>
              ))}
            </div>
          )}

          {/* Brand filter */}
          {brands.length > 1 && (
            <div className="flex rounded-lg overflow-hidden border border-stone-200 bg-white">
              <button
                onClick={() => setBrandFilter('')}
                className={`px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition whitespace-nowrap ${
                  !brandFilter ? 'bg-stone-800 text-white' : 'text-stone-400'
                }`}
              >All Brands</button>
              {brands.map((b) => (
                <button
                  key={b}
                  onClick={() => setBrandFilter(b)}
                  className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition whitespace-nowrap"
                  style={brandFilter === b
                    ? { backgroundColor: getBrandColor(b), color: 'white' }
                    : { color: '#a8a29e' }
                  }
                >{b}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Search + Add */}
      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..."
            className="w-full bg-white border border-stone-200 rounded-xl pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 transition shadow-sm"
          />
        </div>
        <button onClick={load}
          className="p-2 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 transition shadow-sm">
          <RefreshCw size={14} className={`text-stone-500 ${loading ? 'animate-spin' : ''}`} />
        </button>
        <button
          onClick={() => { setEditLabel(null); setShowAdd(true) }}
          className="px-3 py-2 rounded-xl font-bold text-sm flex items-center gap-1.5 transition shadow-sm text-white whitespace-nowrap"
          style={{ backgroundColor: ARTE_NAVY }}
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {/* Grouped cards */}
      {Object.entries(grouped).map(([brand, items]) => (
        <div key={brand}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: getBrandColor(brand) }} />
            <h2 className="text-xs font-bold uppercase tracking-widest" style={{ color: getBrandColor(brand) }}>
              {brand}
            </h2>
            <span className="text-[10px] text-stone-400 font-medium">({items.length})</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mb-6">
            {items.map((l) => (
              <LabelCard key={l.id} label={l} onUpdate={load}
                onEdit={(l) => { setEditLabel(l); setShowAdd(true) }} />
            ))}
          </div>
        </div>
      ))}

      {filtered.length === 0 && !loading && (
        <p className="text-center text-stone-400 py-12">No items found.</p>
      )}

      {showAdd && (
        <AddLabelModal editLabel={editLabel} onClose={() => setShowAdd(false)} onSaved={load} />
      )}
    </div>
  )
}
