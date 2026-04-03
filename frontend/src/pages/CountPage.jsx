import { useState, useEffect } from 'react'
import { ClipboardCheck, Search, Check, X } from 'lucide-react'
import { fetchLabels, bulkCount } from '../api'
import { ARTE_NAVY, getBrandColor } from '../components/CitrusIcon'

export default function CountPage() {
  const [items, setItems] = useState([])
  const [counts, setCounts] = useState({})
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchLabels()
      setItems(data)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const filtered = items.filter(i => {
    if (category && i.category !== category) return false
    if (search) {
      const q = search.toLowerCase()
      return i.flavor.toLowerCase().includes(q) || i.item_code.toLowerCase().includes(q) || i.label_name.toLowerCase().includes(q)
    }
    return true
  })

  const setCount = (id, val) => {
    setCounts(prev => ({ ...prev, [id]: val }))
  }

  const changedItems = Object.entries(counts).filter(([id, val]) => {
    const item = items.find(i => i.id === parseInt(id))
    return item && val !== '' && parseInt(val) !== item.current_stock_bottles
  })

  const handleSubmit = async () => {
    if (changedItems.length === 0) return
    setSubmitting(true)
    try {
      const payload = changedItems.map(([id, val]) => ({
        label_id: parseInt(id),
        actual_count: parseInt(val),
      }))
      const res = await bulkCount(payload)
      setResult(res)
      setCounts({})
      await load()
    } catch (e) { console.error(e) }
    setSubmitting(false)
  }

  const CATS = [
    { key: '', label: 'All' },
    { key: 'juice', label: 'Juice' },
    { key: 'label', label: 'Labels' },
    { key: 'bottle', label: 'Bottles' },
    { key: 'box', label: 'Boxes' },
    { key: 'raw', label: 'Raw' },
    { key: 'misc', label: 'Misc' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-stone-100 rounded-xl flex items-center justify-center">
            <ClipboardCheck size={20} style={{ color: ARTE_NAVY }} />
          </div>
          <div>
            <h1 className="text-xl font-bold" style={{ color: ARTE_NAVY }}>Cycle Count</h1>
            <p className="text-xs text-stone-400">Enter actual physical counts to reconcile inventory</p>
          </div>
        </div>
        {changedItems.length > 0 && (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 rounded-xl text-white text-sm font-bold shadow-sm transition disabled:opacity-50 flex items-center gap-2"
            style={{ backgroundColor: ARTE_NAVY }}
          >
            <Check size={16} />
            Submit {changedItems.length} {changedItems.length === 1 ? 'change' : 'changes'}
          </button>
        )}
      </div>

      {result && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
          <span className="text-sm text-emerald-800 font-medium">
            {result.adjusted} item{result.adjusted !== 1 ? 's' : ''} adjusted and logged to journal.
          </span>
          <button onClick={() => setResult(null)} className="p-1 hover:bg-emerald-100 rounded">
            <X size={14} className="text-emerald-600" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex-1 relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search items..."
            className="w-full bg-white border border-stone-200 rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-stone-300 transition shadow-sm"
          />
        </div>
        <div className="flex rounded-lg overflow-hidden border border-stone-200 bg-white shadow-sm">
          {CATS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setCategory(key)}
              className={`px-2.5 py-2 text-xs font-bold uppercase tracking-wide transition whitespace-nowrap ${
                category === key ? 'text-white' : 'text-stone-400 hover:text-stone-600'
              }`}
              style={category === key ? { backgroundColor: ARTE_NAVY } : {}}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Count table */}
      <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 px-4 py-2 bg-stone-50 border-b border-stone-200 text-[9px] font-bold text-stone-400 uppercase tracking-wider">
          <span>Item</span>
          <span className="w-20 text-right">Current</span>
          <span className="w-24 text-center">Actual Count</span>
          <span className="w-16 text-right">Diff</span>
        </div>
        <div className="max-h-[60vh] overflow-y-auto divide-y divide-stone-100">
          {filtered.map((item) => {
            const val = counts[item.id] ?? ''
            const diff = val !== '' ? parseInt(val) - item.current_stock_bottles : null
            return (
              <div key={item.id} className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 px-4 py-2.5 items-center hover:bg-stone-50/50">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[8px] px-1 py-0.5 rounded font-bold text-white" style={{ backgroundColor: getBrandColor(item.brand) }}>
                      {item.brand}
                    </span>
                    <span className="text-xs font-semibold text-stone-800 truncate">{item.flavor}</span>
                  </div>
                  <span className="text-[10px] text-stone-400 font-mono">{item.item_code}</span>
                </div>
                <span className="w-20 text-right text-sm font-bold text-stone-500">{item.current_stock_bottles}</span>
                <input
                  type="number"
                  min="0"
                  value={val}
                  onChange={(e) => setCount(item.id, e.target.value)}
                  placeholder="—"
                  className="w-24 bg-stone-50 border border-stone-200 rounded-lg px-2 py-1.5 text-sm text-center font-medium focus:outline-none focus:ring-2 focus:ring-stone-300 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <span className={`w-16 text-right text-sm font-bold ${
                  diff === null ? 'text-stone-300' : diff > 0 ? 'text-emerald-600' : diff < 0 ? 'text-red-500' : 'text-stone-400'
                }`}>
                  {diff === null ? '—' : diff > 0 ? `+${diff}` : diff}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {loading && <p className="text-center text-stone-400 py-8">Loading...</p>}
    </div>
  )
}
