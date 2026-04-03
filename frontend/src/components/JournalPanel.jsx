import { useState, useEffect } from 'react'
import { Download, Trash2, Clock, CheckCircle, X } from 'lucide-react'
import { fetchJournalEntries, exportCSV, deleteJournalEntry } from '../api'

export default function JournalPanel({ open, onClose, refreshKey }) {
  const [entries, setEntries] = useState([])
  const [filter, setFilter] = useState('')

  const load = async () => {
    const data = await fetchJournalEntries(filter)
    setEntries(data)
  }

  useEffect(() => { load() }, [filter, refreshKey])

  const handleExport = async () => {
    const csv = await exportCSV()
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'bc_item_journal.csv'
    a.click()
    URL.revokeObjectURL(url)
    load()
  }

  const handleDelete = async (id) => {
    await deleteJournalEntry(id)
    load()
  }

  const pending = entries.filter((e) => e.status === 'Pending').length

  if (!open) return null

  return (
    <>
    {/* Backdrop — click to close */}
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 transition-opacity" onClick={onClose} />
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white border-l border-stone-200 z-40 flex flex-col shadow-2xl animate-slide-in">
      <div className="flex items-center justify-between p-5 border-b border-stone-100">
        <div>
          <h2 className="font-bold text-lg text-stone-900">BC Journal</h2>
          <p className="text-xs text-stone-400 mt-0.5">{pending} pending entries</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExport}
            disabled={pending === 0}
            className="px-4 py-2 bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white rounded-xl text-sm font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shadow-sm"
          >
            <Download size={14} /> Export CSV
          </button>
          <button onClick={onClose} className="p-2 hover:bg-stone-100 rounded-xl transition">
            <X size={18} className="text-stone-400" />
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 p-4 border-b border-stone-100">
        {['', 'Pending', 'Exported'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wide transition ${
              filter === f ? 'bg-stone-900 text-white' : 'text-stone-400 hover:bg-stone-100'
            }`}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
        {entries.length === 0 && (
          <p className="text-center text-stone-400 py-12">No journal entries</p>
        )}
        {entries.map((e) => (
          <div key={e.id} className="bg-stone-50 rounded-xl p-4 text-sm border border-stone-100">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-stone-600 font-medium">{e.item_no}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-lg font-semibold ${
                    e.entry_type === 'Positive Adjmt.' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'
                  }`}>
                    {e.entry_type === 'Positive Adjmt.' ? '+' : '-'}{e.quantity} {e.unit_of_measure}
                  </span>
                </div>
                <p className="text-xs text-stone-400 mt-1.5 truncate">{e.description}</p>
                <div className="flex items-center gap-3 mt-2">
                  {e.status === 'Pending' ? (
                    <span className="flex items-center gap-1 text-xs text-amber-600 font-medium">
                      <Clock size={10} /> Pending
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                      <CheckCircle size={10} /> Exported
                    </span>
                  )}
                  <span className="text-xs text-stone-300">{e.posting_date}</span>
                </div>
              </div>
              {e.status === 'Pending' && (
                <button
                  onClick={() => handleDelete(e.id)}
                  className="p-1.5 hover:bg-red-50 rounded-lg transition text-stone-300 hover:text-red-500"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
    </>
  )
}
