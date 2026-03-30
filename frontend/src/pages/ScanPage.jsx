import { useState, useEffect } from 'react'
import { fetchLabels } from '../api'
import InvoiceScan from '../components/InvoiceScan'

export default function ScanPage() {
  const [labels, setLabels] = useState([])
  const [success, setSuccess] = useState(false)

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
      <div>
        <h1 className="text-2xl font-bold">Invoice Scan</h1>
        <p className="text-gray-400 text-sm mt-1">
          Upload a delivery invoice to auto-extract line items and post to inventory
        </p>
      </div>

      {success && (
        <div className="bg-emerald-900/30 border border-emerald-700 text-emerald-300 px-4 py-3 rounded-xl text-sm">
          Inventory updated and journal entries created successfully.
        </div>
      )}

      <InvoiceScan labels={labels} onConfirmed={handleConfirmed} />
    </div>
  )
}
