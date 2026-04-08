import { useState, useRef } from 'react'
import { Upload, FileText, Check, X, Loader2, Camera, Image, RotateCcw, AlertTriangle, Search, Plus } from 'lucide-react'
import { scanInvoice, confirmInvoice, fetchLabels } from '../api'
import { ARTE_NAVY } from './CitrusIcon'
import AddLabelModal from './AddLabelModal'

function parseDescription(desc, rawItemNo) {
  const d = (desc || '').toLowerCase()
  let brand = 'Arte'
  if (d.includes('quirk')) brand = 'Quirkies'
  else if (d.includes('joosy') || d.includes('juicy')) brand = 'Joosy'
  let size = '1L'
  const sizeMatch = d.match(/(\d+)\s*(ml|l|litre|liter)/i)
  if (sizeMatch) {
    size = sizeMatch[2].toLowerCase() === 'l' ? `${sizeMatch[1]}L` : `${sizeMatch[1]}mL`
  }
  const flavors = ['orange', 'lime', 'lemon', 'grapefruit', 'blueberry', 'apple', 'tropical', 'mandarin', 'sunshine']
  let flavor = ''
  for (const f of flavors) {
    if (d.includes(f)) { flavor = f.charAt(0).toUpperCase() + f.slice(1); break }
  }
  const brandCode = { 'Arte': 'ARTE', 'Quirkies': 'QRKS', 'Joosy': 'JOOS' }[brand] || 'GENL'
  const flavorCode = flavor.substring(0, 3).toUpperCase() || 'UNK'
  const sizeCode = size.replace('mL', '').replace('L', 'L')
  const itemCode = `${brandCode}-${flavorCode}-${sizeCode}-BTL`
  return {
    brand, flavor, size,
    label_name: `${brand} ${flavor}`.trim(),
    item_code: itemCode,
    color_identifier: `${brand.toLowerCase()}-${flavor.toLowerCase()}`,
    category: 'juice',
    case_quantity: 6,
    shelf_life_days: 365,
  }
}

function ProductPicker({ labels, value, onChange, highlighted, onCreateNew }) {
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)

  const selected = labels.find(l => l.item_code === value)
  const filtered = search
    ? labels.filter(l =>
        l.label_name.toLowerCase().includes(search.toLowerCase()) ||
        l.item_code.toLowerCase().includes(search.toLowerCase()) ||
        l.flavor.toLowerCase().includes(search.toLowerCase()) ||
        l.brand.toLowerCase().includes(search.toLowerCase())
      )
    : labels

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full border rounded-xl px-3 py-2.5 text-sm font-medium text-left focus:outline-none focus:ring-2 focus:ring-orange-300 flex items-center justify-between ${
          value ? 'bg-emerald-50 border-emerald-200 text-emerald-800' :
          highlighted ? 'bg-amber-50 border-amber-300 text-amber-700 animate-pulse' :
          'bg-stone-50 border-stone-200 text-stone-500'
        }`}
      >
        <span className="truncate">
          {selected ? `${selected.label_name} (${selected.item_code})` : '— select product —'}
        </span>
        <Search size={14} className="flex-shrink-0 ml-1 opacity-40" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-stone-200 rounded-xl shadow-lg overflow-hidden">
          <div className="p-2 border-b border-stone-100">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, code, brand..."
              className="w-full bg-stone-50 border border-stone-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            <button
              type="button"
              onClick={() => { onChange(''); setOpen(false); setSearch('') }}
              className="w-full text-left px-3 py-2 text-sm text-stone-400 hover:bg-stone-50"
            >
              — none —
            </button>
            {filtered.slice(0, 50).map((l) => (
              <button
                key={l.item_code}
                type="button"
                onClick={() => { onChange(l.item_code); setOpen(false); setSearch('') }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-orange-50 transition ${
                  l.item_code === value ? 'bg-emerald-50 font-bold' : ''
                }`}
              >
                <span className="font-medium text-stone-800">{l.label_name}</span>
                <span className="text-[10px] text-stone-400 ml-1.5">{l.item_code}</span>
                <span className="text-[9px] text-stone-300 ml-1">({l.brand})</span>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="text-center text-stone-400 text-xs py-3">No matches</p>
            )}
            {onCreateNew && (
              <button
                type="button"
                onClick={() => { setOpen(false); setSearch(''); onCreateNew() }}
                className="w-full text-left px-3 py-2.5 text-sm font-bold text-orange-600 hover:bg-orange-50 border-t border-stone-100 sticky bottom-0 bg-white flex items-center gap-1.5"
              >
                <Plus size={14} /> Create New Product
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const SCAN_STAGES = ['uploading', 'analyzing', 'extracting']
const STAGE_LABELS = {
  uploading: 'Uploading image',
  analyzing: 'Analyzing invoice',
  extracting: 'Extracting items',
}

export default function InvoiceScan({ labels, onConfirmed, onLabelsChanged }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanStage, setScanStage] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [result, setResult] = useState(null)
  const [editItems, setEditItems] = useState([])
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [retryCount, setRetryCount] = useState(0)
  const [mode, setMode] = useState('add') // 'add' or 'remove'
  const [newProductForIdx, setNewProductForIdx] = useState(null)
  const [newProductDefaults, setNewProductDefaults] = useState({})
  const fileRef = useRef()
  const cameraRef = useRef()
  const stageTimersRef = useRef([])

  const handleFile = (f) => {
    if (!f) return
    setFile(f)
    setError('')
    setRetryCount(0)
    if (f.type.startsWith('image/')) {
      setPreview(URL.createObjectURL(f))
    } else {
      setPreview(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    handleFile(e.dataTransfer.files?.[0])
  }

  const clearStageTimers = () => {
    stageTimersRef.current.forEach(clearInterval)
    stageTimersRef.current = []
    setElapsed(0)
  }

  const handleScan = async () => {
    if (!file) return
    setScanning(true)
    setError('')
    setResult(null)

    // Stage transitions: uploading → analyzing → extracting
    setScanStage('uploading')
    clearStageTimers()
    const startTime = Date.now()
    const analyzeAt = 1500 + Math.random() * 1000
    const extractAt = 5000 + Math.random() * 3000
    const ticker = setInterval(() => {
      const el = Math.floor((Date.now() - startTime) / 1000)
      setElapsed(el)
      if (Date.now() - startTime > extractAt) setScanStage('extracting')
      else if (Date.now() - startTime > analyzeAt) setScanStage('analyzing')
    }, 500)
    stageTimersRef.current = [ticker]

    // Retry up to 3 times on failure
    let lastError = ''
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const data = await scanInvoice(file)
        if (data.items && data.items.length > 0) {
          clearStageTimers()
          setScanStage('extracting')
          setResult(data)
          setEditItems(
            data.items.map((item, i) => {
              const matchedLabel = labels.find(l => l.item_code === item.matched_item_code)
              return {
                ...item,
                _id: i,
                _enabled: true,
                matched_item_code: item.matched_item_code || '',
                _case_quantity: matchedLabel?.case_quantity || 6,
              }
            })
          )
          setRetryCount(attempt)
          setScanning(false)
          setScanStage(null)
          return
        }
        lastError = 'No items detected in invoice. Try a clearer photo.'
      } catch (e) {
        lastError = e.message
      }
      // Wait 1s before retry
      if (attempt < 2) await new Promise(r => setTimeout(r, 1000))
    }

    clearStageTimers()
    setScanStage(null)
    setError(lastError)
    setRetryCount(3)
    setScanning(false)
  }

  const updateItem = (idx, field, value) => {
    setEditItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item))
    )
  }

  const updateCases = (idx, cases) => {
    setEditItems(prev => prev.map((item, i) => {
      if (i !== idx) return item
      const caseQty = item._case_quantity || 6
      return { ...item, quantity_cases: cases, quantity_bottles: cases * caseQty }
    }))
  }

  const updateMatchedProduct = (idx, code) => {
    const label = labels.find(l => l.item_code === code)
    setEditItems(prev => prev.map((item, i) => i === idx ? {
      ...item,
      matched_item_code: code,
      _case_quantity: label?.case_quantity || 6,
    } : item))
  }

  const handleConfirm = async () => {
    setConfirming(true)
    setError('')
    const multiplier = mode === 'remove' ? -1 : 1
    const items = editItems
      .filter((i) => i._enabled && i.matched_item_code)
      .map((i) => ({
        matched_item_code: i.matched_item_code,
        quantity_bottles: (parseInt(i.quantity_bottles) || 0) * multiplier,
        description: `${mode === 'remove' ? 'REMOVED: ' : ''}${i.description || ''}`,
      }))
    try {
      await confirmInvoice(items, result?.invoice_number || '')
      onConfirmed()
      setResult(null)
      setEditItems([])
      setFile(null)
      setPreview(null)
      setMode('add')
    } catch (e) {
      setError(e.message)
    }
    setConfirming(false)
  }

  const reset = () => {
    clearStageTimers()
    setScanStage(null)
    setFile(null)
    setPreview(null)
    setResult(null)
    setEditItems([])
    setError('')
    setRetryCount(0)
  }

  const retakePhoto = () => {
    clearStageTimers()
    setScanStage(null)
    setFile(null)
    setPreview(null)
    setError('')
    setRetryCount(0)
    setResult(null)
    setEditItems([])
    // Open camera immediately
    setTimeout(() => cameraRef.current?.click(), 100)
  }

  return (
    <div className="space-y-6">
      {/* Add / Remove toggle */}
      <div className="flex rounded-xl overflow-hidden border border-stone-200 bg-white shadow-sm">
        <button
          onClick={() => setMode('add')}
          className={`flex-1 py-2.5 text-sm font-bold uppercase tracking-wide transition ${
            mode === 'add' ? 'bg-emerald-500 text-white' : 'text-stone-400 hover:text-stone-600'
          }`}
        >
          + Add Stock
        </button>
        <button
          onClick={() => setMode('remove')}
          className={`flex-1 py-2.5 text-sm font-bold uppercase tracking-wide transition ${
            mode === 'remove' ? 'bg-red-500 text-white' : 'text-stone-400 hover:text-stone-600'
          }`}
        >
          − Remove Stock
        </button>
      </div>

      {/* Upload / Camera area */}
      {!file && (
        <div className="space-y-3">
          <button
            onClick={() => cameraRef.current?.click()}
            className="w-full py-5 rounded-2xl border-2 border-dashed border-orange-300 bg-orange-50/50 hover:bg-orange-50 transition-all flex flex-col items-center gap-2"
          >
            <div className="w-14 h-14 rounded-2xl bg-orange-100 flex items-center justify-center">
              <Camera size={28} className="text-orange-500" />
            </div>
            <span className="font-semibold text-stone-700">Scan with Phone Camera</span>
            <span className="text-xs text-stone-400">Take a clear, well-lit photo</span>
          </button>
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => handleFile(e.target.files?.[0])}
            className="hidden"
          />

          <div
            className="border-2 border-dashed border-stone-300 rounded-2xl p-6 text-center cursor-pointer hover:border-stone-400 transition-all"
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <input ref={fileRef} type="file" accept="image/*,.pdf" onChange={(e) => handleFile(e.target.files?.[0])} className="hidden" />
            <div className="flex items-center justify-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center">
                <Image size={20} className="text-stone-400" />
              </div>
              <div className="text-left">
                <p className="font-medium text-stone-600 text-sm">Upload File</p>
                <p className="text-xs text-stone-400">JPG, PNG, PDF — max 20MB</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview */}
      {file && !result && !error && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl border border-stone-200 overflow-hidden shadow-sm">
            {preview && (
              <div className="relative">
                <img src={preview} alt="Invoice preview" className="w-full max-h-80 object-contain bg-stone-50" />
                <button onClick={reset} className="absolute top-3 right-3 p-2 bg-white rounded-xl shadow-md hover:bg-stone-50 transition">
                  <X size={16} className="text-stone-500" />
                </button>
              </div>
            )}
            {!preview && (
              <div className="p-5 flex items-center gap-3">
                <FileText size={24} className="text-orange-500" />
                <div>
                  <p className="font-medium text-stone-800 text-sm">{file.name}</p>
                  <p className="text-xs text-stone-400">{(file.size / 1024).toFixed(0)} KB</p>
                </div>
                <button onClick={reset} className="ml-auto p-2 hover:bg-stone-100 rounded-xl transition">
                  <X size={16} className="text-stone-400" />
                </button>
              </div>
            )}
          </div>

          {scanning && scanStage && (
            <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
              {SCAN_STAGES.map((stage, i) => {
                const currentIdx = SCAN_STAGES.indexOf(scanStage)
                const isDone = i < currentIdx
                const isActive = i === currentIdx
                return (
                  <div key={stage} className={`flex items-center gap-3 px-4 py-3 ${i < SCAN_STAGES.length - 1 ? 'border-b border-stone-100' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${
                      isDone ? 'bg-emerald-500' : isActive ? 'bg-orange-500' : 'bg-stone-100'
                    }`}>
                      {isDone
                        ? <Check size={13} className="text-white" />
                        : isActive
                          ? <Loader2 size={13} className="text-white animate-spin" />
                          : <div className="w-2 h-2 rounded-full bg-stone-300" />
                      }
                    </div>
                    <span className={`text-sm font-medium transition-colors ${
                      isDone ? 'text-emerald-600' : isActive ? 'text-stone-800' : 'text-stone-400'
                    }`}>
                      {STAGE_LABELS[stage]}{isActive ? '...' : ''}
                    </span>
                  </div>
                )
              })}
              {elapsed > 0 && (
                <div className="px-4 py-2 border-t border-stone-100 text-center">
                  <span className="text-xs text-stone-400 font-medium">{elapsed}s elapsed</span>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleScan}
            disabled={scanning}
            className="w-full py-3.5 text-white rounded-xl font-bold flex items-center justify-center gap-2.5 transition disabled:opacity-50 shadow-sm"
            style={{ backgroundColor: ARTE_NAVY }}
          >
            {scanning ? (
              <><Loader2 size={18} className="animate-spin" /> {STAGE_LABELS[scanStage] || 'Reading document'}...</>
            ) : (
              <><FileText size={18} /> Scan Document</>
            )}
          </button>
        </div>
      )}

      {/* Error with retake option */}
      {error && (
        <div className="space-y-3">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-700 text-sm font-medium">{error}</p>
                <p className="text-red-400 text-xs mt-1">
                  Tip: Make sure the invoice is flat, well-lit, and text is readable
                </p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={retakePhoto}
              className="flex-1 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition shadow-sm"
            >
              <Camera size={18} /> Retake Photo
            </button>
            <button
              onClick={() => { setError(''); handleScan() }}
              disabled={scanning}
              className="flex-1 py-3 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition shadow-sm disabled:opacity-50"
              style={{ backgroundColor: ARTE_NAVY }}
            >
              <RotateCcw size={18} /> Try Again
            </button>
          </div>

          <button onClick={reset}
            className="w-full py-2.5 bg-white border border-stone-200 rounded-xl text-stone-500 text-sm font-medium hover:bg-stone-50 transition">
            Cancel
          </button>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Mode indicator */}
          <div className={`rounded-xl px-4 py-2.5 text-sm font-bold text-center ${
            mode === 'remove' ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
          }`}>
            {mode === 'remove' ? '− Removing stock from inventory' : '+ Adding stock to inventory'}
          </div>

          {/* Invoice header info */}
          <div className="flex items-center justify-between">
            <div className="bg-white rounded-2xl p-4 border border-stone-200 shadow-sm flex-1">
              <div className="flex flex-wrap items-center gap-4 text-sm">
                {result.invoice_number && (
                  <div>
                    <span className="text-[10px] text-stone-400 uppercase tracking-wider font-bold block">Invoice</span>
                    <span className="font-bold text-stone-800">#{result.invoice_number}</span>
                  </div>
                )}
                {result.supplier && (
                  <div>
                    <span className="text-[10px] text-stone-400 uppercase tracking-wider font-bold block">Supplier</span>
                    <span className="font-bold text-stone-800">{result.supplier}</span>
                  </div>
                )}
                {result.invoice_date && (
                  <div>
                    <span className="text-[10px] text-stone-400 uppercase tracking-wider font-bold block">Date</span>
                    <span className="font-bold text-stone-800">{result.invoice_date}</span>
                  </div>
                )}
              </div>
            </div>
            <button onClick={reset} className="ml-3 p-2.5 bg-white border border-stone-200 rounded-xl hover:bg-stone-50 transition shadow-sm">
              <X size={16} className="text-stone-400" />
            </button>
          </div>

          {/* Summary bar */}
          {(() => {
            const matched = editItems.filter(i => i._enabled && i.matched_item_code).length
            const unmatched = editItems.filter(i => i._enabled && !i.matched_item_code).length
            const noQty = editItems.filter(i => i._enabled && (!i.quantity_bottles || parseInt(i.quantity_bottles) === 0)).length
            return (
              <div className="flex gap-2 text-xs font-bold">
                <span className="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-700">{matched} matched</span>
                {unmatched > 0 && <span className="px-2.5 py-1 rounded-lg bg-amber-100 text-amber-700">{unmatched} need match</span>}
                {noQty > 0 && <span className="px-2.5 py-1 rounded-lg bg-red-100 text-red-700">{noQty} missing qty</span>}
              </div>
            )
          })()}

          {/* Item rows */}
          <div className="space-y-3">
            {editItems.map((item, idx) => {
              const warnings = item.warnings || []
              const hasWarning = warnings.length > 0
              return (
              <div key={idx}
                className={`bg-white rounded-2xl p-4 border shadow-sm transition ${
                  !item._enabled ? 'border-stone-100 opacity-50' :
                  !item.matched_item_code ? 'border-amber-300 bg-amber-50/30' :
                  'border-stone-200'
                }`}>

                <div className="flex items-start gap-3 mb-3">
                  <button onClick={() => updateItem(idx, '_enabled', !item._enabled)}
                    className={`mt-0.5 p-1.5 rounded-lg transition ${item._enabled ? 'bg-emerald-500 text-white' : 'bg-stone-200 text-stone-400'}`}>
                    {item._enabled ? <Check size={14} /> : <X size={14} />}
                  </button>
                  <div className="flex-1">
                    <label className="block text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-1">Description</label>
                    <p className="text-sm font-medium text-stone-800">{item.description}</p>
                    {item.raw_supplier_code && (
                      <p className="text-[10px] text-stone-400 font-mono mt-0.5">Code: {item.raw_supplier_code}</p>
                    )}
                    {/* Warning badges */}
                    {(hasWarning || warnings.includes('auto_created')) && item._enabled && (
                      <div className="flex gap-1.5 mt-1.5 flex-wrap">
                        {warnings.includes('no_match') && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-bold flex items-center gap-0.5">
                            <AlertTriangle size={9} /> Select product below
                          </span>
                        )}
                        {warnings.includes('no_qty') && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-100 text-red-600 font-bold flex items-center gap-0.5">
                            <AlertTriangle size={9} /> Enter quantity
                          </span>
                        )}
                        {warnings.includes('auto_created') && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold flex items-center gap-0.5">
                            <Plus size={9} /> New product created
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className={`block text-[10px] font-bold uppercase tracking-widest mb-1 ${
                      warnings.includes('no_qty') ? 'text-red-500' : 'text-stone-400'
                    }`}>Cases</label>
                    <input type="number" value={item.quantity_cases ?? ''}
                      onChange={(e) => updateCases(idx, parseInt(e.target.value) || 0)}
                      className={`w-full border rounded-xl px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-orange-300 ${
                        warnings.includes('no_qty') ? 'bg-red-50 border-red-300' : 'bg-white border-stone-200'
                      }`} />
                  </div>
                  <div>
                    <label className={`block text-[10px] font-bold uppercase tracking-widest mb-1 ${
                      warnings.includes('no_qty') ? 'text-red-500' : 'text-stone-400'
                    }`}>Qty ({item.raw_unit || 'units'})</label>
                    <input type="number" value={item.quantity_bottles || 0}
                      onChange={(e) => updateItem(idx, 'quantity_bottles', e.target.value)}
                      className={`w-full border rounded-xl px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-orange-300 ${
                        warnings.includes('no_qty') ? 'bg-red-50 border-red-300' : 'bg-white border-stone-200'
                      }`} />
                  </div>
                  {item.unit_price != null && (
                    <div>
                      <label className="block text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-1">Unit Price</label>
                      <div className="bg-stone-50 border border-stone-200 rounded-xl px-3 py-2 text-sm text-stone-600">
                        ${item.unit_price}
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <label className={`block text-[10px] font-bold uppercase tracking-widest mb-1 ${
                    !item.matched_item_code && item._enabled ? 'text-amber-600' : 'text-stone-400'
                  }`}>
                    {item.matched_item_code ? 'Matched Product' : 'Select Product'}
                  </label>
                  {/* Searchable product picker */}
                  <ProductPicker
                    labels={labels}
                    value={item.matched_item_code}
                    onChange={(code) => updateMatchedProduct(idx, code)}
                    highlighted={!item.matched_item_code && item._enabled}
                    onCreateNew={() => {
                      setNewProductForIdx(idx)
                      setNewProductDefaults(parseDescription(item.description, item.raw_item_no))
                    }}
                  />
                </div>
              </div>
            )})}
          </div>

          <button onClick={handleConfirm}
            disabled={confirming || editItems.filter((i) => i._enabled && i.matched_item_code).length === 0}
            className={`w-full py-3.5 text-white rounded-xl font-bold flex items-center justify-center gap-2.5 transition disabled:opacity-50 shadow-sm ${
              mode === 'remove' ? 'bg-red-500 hover:bg-red-600' : 'bg-emerald-500 hover:bg-emerald-600'
            }`}>
            {confirming ? (
              <><Loader2 size={18} className="animate-spin" /> Posting...</>
            ) : mode === 'remove' ? (
              <><Check size={18} /> Remove from Inventory</>
            ) : (
              <><Check size={18} /> Add to Inventory</>
            )}
          </button>
        </div>
      )}

      {/* New product modal */}
      {newProductForIdx !== null && (
        <AddLabelModal
          onClose={() => setNewProductForIdx(null)}
          onSaved={async () => {
            const updated = await fetchLabels()
            const newLabel = updated.find(l => l.item_code === newProductDefaults.item_code)
            if (newLabel) {
              updateMatchedProduct(newProductForIdx, newLabel.item_code)
            }
            onLabelsChanged?.()
            setNewProductForIdx(null)
          }}
          editLabel={null}
          defaults={newProductDefaults}
        />
      )}
    </div>
  )
}
