import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { fetchLabels } from '../api'
import InvoiceScan from '../components/InvoiceScan'
import { ARTE_NAVY } from '../components/CitrusIcon'

export default function ScanPage() {
  const [labels, setLabels] = useState([])
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchLabels().then(setLabels).catch(console.error)
  }, [])

  const handleConfirmed = () => {
    setSuccess(true)
    setTimeout(() => setSuccess(false), 3000)
    fetchLabels().then(setLabels).catch(console.error)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="p-2 rounded-xl bg-white border border-stone-200 hover:bg-stone-50 transition shadow-sm"
        >
          <ArrowLeft size={18} className="text-stone-500" />
        </button>
        <div>
          <h1 className="text-xl font-bold" style={{ color: ARTE_NAVY }}>Invoice Scan</h1>
          <p className="text-stone-400 text-[10px] uppercase tracking-[0.15em] font-semibold">
            Upload a delivery invoice to auto-extract items
          </p>
        </div>
      </div>

      {success && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl text-sm font-medium">
          Inventory updated and journal entries created successfully.
        </div>
      )}

      <InvoiceScan labels={labels} onConfirmed={handleConfirmed} />
    </div>
  )
}
