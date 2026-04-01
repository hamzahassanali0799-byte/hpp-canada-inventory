import { useState } from 'react'
import { Minus, Plus, Edit3, Trash2 } from 'lucide-react'
import { adjustStock, deleteLabel } from '../api'
import BottleImage, { getCitrus, getBrandColor } from './CitrusIcon'

function getShelfBadge(days) {
  if (days > 9000) return null
  if (days > 300) return { bg: '#ecfdf5', color: '#047857', label: `${days}d` }
  if (days >= 200) return { bg: '#fffbeb', color: '#b45309', label: `${days}d` }
  return { bg: '#fef2f2', color: '#b91c1c', label: `${days}d` }
}

function getCategoryIcon(category) {
  if (category === 'label') return '🏷️'
  if (category === 'box') return '📦'
  if (category === 'bottle') return '🫙'
  return null
}

export default function LabelCard({ label, onUpdate, onEdit }) {
  const [manualQty, setManualQty] = useState('')
  const [loading, setLoading] = useState(false)
  const c = getCitrus(label.color_identifier)
  const shelf = getShelfBadge(label.shelf_life_days)
  const brandColor = getBrandColor(label.brand)
  const isJuice = label.category === 'juice'
  const isLabel = label.category === 'label'
  const isBox = label.category === 'box'

  // Clear unit names based on category
  const unitName = isBox ? 'units' : isLabel ? 'rolls' : 'bottles'
  const caseName = isBox ? 'packs' : isLabel ? 'boxes' : 'cases'

  const handleAdjust = async (qty, mode = 'bottle') => {
    if (qty === 0) return
    setLoading(true)
    try {
      await adjustStock(label.id, qty, mode)
      onUpdate()
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const handleManualSet = async () => {
    const val = parseInt(manualQty)
    if (isNaN(val) || val < 0) return
    const diff = val - label.current_stock_bottles
    if (diff === 0) return
    await handleAdjust(diff)
    setManualQty('')
  }

  const handleManualKeyDown = (e) => {
    if (e.key === 'Enter') handleManualSet()
  }

  const handleDelete = async () => {
    if (!confirm(`Delete "${label.flavor}"?`)) return
    setLoading(true)
    try {
      await deleteLabel(label.id)
      onUpdate()
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  return (
    <div className="rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200 bg-white border border-stone-200">
      {/* Top color bar */}
      <div className="h-1.5" style={{ backgroundColor: c.labelColor }} />

      {/* Header: image + name */}
      <div className="px-4 pt-3 pb-3 flex items-center gap-3" style={{ backgroundColor: c.cardBg }}>
        <div className="flex-shrink-0">
          {isJuice ? (
            <BottleImage colorId={label.color_identifier} size="sm" />
          ) : (
            <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
              style={{ backgroundColor: `${c.labelColor}15`, border: `1.5px solid ${c.labelColor}30` }}>
              {getCategoryIcon(label.category)}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider text-white"
              style={{ backgroundColor: brandColor }}>{label.brand}</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider bg-stone-200 text-stone-600">
              {label.size}
            </span>
            {shelf && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold" style={{ backgroundColor: shelf.bg, color: shelf.color }}>
                {shelf.label}
              </span>
            )}
          </div>
          <h3 className="text-sm font-bold truncate" style={{ color: brandColor }}>{label.flavor}</h3>
        </div>
        <button onClick={() => onEdit(label)}
          className="p-1.5 rounded-lg hover:bg-white/60 transition" style={{ color: brandColor }}>
          <Edit3 size={14} />
        </button>
      </div>

      <div className="px-4 pb-4 pt-3">
        {/* Stock display */}
        <div className="rounded-xl p-3 mb-3 bg-stone-50 border border-stone-200">
          <div className="flex items-center">
            <div className="flex-1 text-center">
              <span className="text-3xl font-extrabold" style={{ color: brandColor }}>
                {label.current_stock_bottles}
              </span>
              <p className="text-[9px] text-stone-500 mt-0.5 uppercase tracking-widest font-bold">{unitName}</p>
            </div>
            {!isBox && label.case_quantity > 1 && (
              <>
                <div className="w-px h-10 bg-stone-200" />
                <div className="flex-1 text-center">
                  <span className="text-3xl font-extrabold" style={{ color: brandColor }}>
                    {label.current_stock_cases}
                  </span>
                  <p className="text-[9px] text-stone-500 mt-0.5 uppercase tracking-widest font-bold">{caseName}</p>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Manual qty input */}
        <div className="flex items-center gap-1.5 mb-2.5">
          <input
            type="number"
            min="0"
            value={manualQty}
            onChange={(e) => setManualQty(e.target.value)}
            onKeyDown={handleManualKeyDown}
            placeholder="Set qty"
            className="flex-1 bg-white border border-stone-200 rounded-lg px-2.5 py-2 text-sm text-center font-medium focus:outline-none focus:ring-2 focus:ring-stone-300 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />
          <button
            onClick={handleManualSet}
            disabled={loading || manualQty === ''}
            className="px-3 py-2 rounded-lg text-xs font-bold uppercase text-white transition disabled:opacity-40 shadow-sm"
            style={{ backgroundColor: brandColor }}
          >
            Set
          </button>
        </div>

        {/* +/- quick adjust */}
        <div className="flex items-center gap-1.5">
          <button onClick={() => handleAdjust(-1)} disabled={loading}
            className="p-2 rounded-lg border border-stone-200 hover:bg-red-50 text-stone-500 hover:text-red-500 transition disabled:opacity-40">
            <Minus size={14} />
          </button>
          <button onClick={() => handleAdjust(-label.case_quantity)} disabled={loading}
            className="flex-1 py-2 rounded-lg border border-stone-200 text-xs font-bold text-stone-500 hover:bg-red-50 hover:text-red-500 transition disabled:opacity-40">
            -{label.case_quantity}
          </button>
          <button onClick={() => handleAdjust(label.case_quantity)} disabled={loading}
            className="flex-1 py-2 rounded-lg border border-stone-200 text-xs font-bold text-stone-500 hover:bg-emerald-50 hover:text-emerald-600 transition disabled:opacity-40">
            +{label.case_quantity}
          </button>
          <button onClick={() => handleAdjust(1)} disabled={loading}
            className="p-2 rounded-lg border border-stone-200 hover:bg-emerald-50 text-stone-500 hover:text-emerald-600 transition disabled:opacity-40">
            <Plus size={14} />
          </button>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-stone-100">
          <span className="text-[10px] font-mono text-stone-500 font-medium">{label.item_code}</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-stone-400 font-medium">{label.location_code}</span>
            <button onClick={handleDelete} disabled={loading}
              className="p-1 rounded hover:bg-red-50 text-stone-300 hover:text-red-500 transition">
              <Trash2 size={11} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
