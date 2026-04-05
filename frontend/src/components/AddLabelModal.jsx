import { useState } from 'react'
import { X } from 'lucide-react'
import { createLabel, updateLabel } from '../api'
import { ARTE_NAVY } from './CitrusIcon'

export default function AddLabelModal({ onClose, onSaved, editLabel, defaults }) {
  const isEdit = !!editLabel
  const d = defaults || {}
  const [form, setForm] = useState({
    brand: editLabel?.brand || d.brand || 'Arte',
    category: editLabel?.category || d.category || 'juice',
    label_name: editLabel?.label_name || d.label_name || '',
    flavor: editLabel?.flavor || d.flavor || '',
    size: editLabel?.size || d.size || '1L',
    color_identifier: editLabel?.color_identifier || d.color_identifier || 'arte-orange',
    item_code: editLabel?.item_code || d.item_code || '',
    location_code: editLabel?.location_code || d.location_code || 'MAIN',
    unit_of_measure: editLabel?.unit_of_measure || d.unit_of_measure || 'BTL',
    case_quantity: editLabel?.case_quantity || d.case_quantity || 6,
    shelf_life_days: editLabel?.shelf_life_days || d.shelf_life_days || 365,
    min_stock: editLabel?.min_stock || d.min_stock || 0,
    reorder_qty: editLabel?.reorder_qty || d.reorder_qty || 0,
    expiry_date: editLabel?.expiry_date || d.expiry_date || '',
    notes: editLabel?.notes || d.notes || '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (isEdit) {
        await updateLabel(editLabel.id, {
          item_code: form.item_code, location_code: form.location_code,
          min_stock: parseInt(form.min_stock) || 0, reorder_qty: parseInt(form.reorder_qty) || 0,
          expiry_date: form.expiry_date || null, notes: form.notes,
        })
      } else {
        await createLabel({ ...form, case_quantity: parseInt(form.case_quantity), shelf_life_days: parseInt(form.shelf_life_days) })
      }
      onSaved()
      onClose()
    } catch (err) { setError(err.message) }
    setSaving(false)
  }

  const inputCls = "w-full bg-stone-50 border border-stone-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300 transition"
  const labelCls = "block text-[9px] font-bold text-stone-400 uppercase tracking-widest mb-1"

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl border border-stone-200 max-h-[90vh] overflow-y-auto animate-fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-stone-100 sticky top-0 bg-white rounded-t-2xl">
          <h2 className="text-lg font-bold" style={{ color: ARTE_NAVY }}>{isEdit ? 'Edit Item' : 'Add New Item'}</h2>
          <button onClick={onClose} className="p-2 hover:bg-stone-100 rounded-xl transition"><X size={18} className="text-stone-400" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {!isEdit && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelCls}>Category</label>
                  <select value={form.category} onChange={set('category')} className={inputCls}>
                    <option value="juice">Juice</option>
                    <option value="bottle">Bottle</option>
                    <option value="label">Label</option>
                    <option value="box">Box</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Brand</label>
                  <select value={form.brand} onChange={set('brand')} className={inputCls}>
                    <option value="Arte">Arte</option>
                    <option value="Quirkies">Quirkies</option>
                    <option value="Joosy">Joosy</option>
                    <option value="General">General</option>
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Size</label>
                  <input value={form.size} onChange={set('size')} className={inputCls} placeholder="1L / 300mL / 19x10x8" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelCls}>Name</label>
                  <input value={form.label_name} onChange={set('label_name')} required className={inputCls} placeholder="Arte Orange" />
                </div>
                <div>
                  <label className={labelCls}>Flavor / Type</label>
                  <input value={form.flavor} onChange={set('flavor')} required className={inputCls} placeholder="Orange" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelCls}>Case/Pack Qty</label>
                  <input type="number" value={form.case_quantity} onChange={set('case_quantity')} className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>Shelf Life (days)</label>
                  <input type="number" value={form.shelf_life_days} onChange={set('shelf_life_days')} className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>UOM</label>
                  <select value={form.unit_of_measure} onChange={set('unit_of_measure')} className={inputCls}>
                    <option value="BTL">BTL</option>
                    <option value="EA">EA</option>
                    <option value="CS">CS</option>
                  </select>
                </div>
              </div>
              <div>
                <label className={labelCls}>Color ID</label>
                <input value={form.color_identifier} onChange={set('color_identifier')} className={inputCls} placeholder="arte-orange / quirk-blueberry / box" />
              </div>
            </>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>Item Code</label>
              <input value={form.item_code} onChange={set('item_code')} required={!isEdit} className={`${inputCls} font-mono`} placeholder="ARTE-ORG-1L-BTL" />
            </div>
            <div>
              <label className={labelCls}>Location</label>
              <input value={form.location_code} onChange={set('location_code')} className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelCls}>Min Stock</label>
              <input type="number" value={form.min_stock} onChange={set('min_stock')} className={inputCls} placeholder="0" />
            </div>
            <div>
              <label className={labelCls}>Reorder Qty</label>
              <input type="number" value={form.reorder_qty} onChange={set('reorder_qty')} className={inputCls} placeholder="0" />
            </div>
            <div>
              <label className={labelCls}>Expiry Date</label>
              <input type="date" value={form.expiry_date} onChange={set('expiry_date')} className={inputCls} />
            </div>
          </div>
          <div>
            <label className={labelCls}>Notes</label>
            <textarea value={form.notes} onChange={set('notes')} rows={2} className={`${inputCls} resize-none`} />
          </div>
          {error && <p className="text-red-500 text-sm bg-red-50 p-3 rounded-xl">{error}</p>}
          <button type="submit" disabled={saving}
            className="w-full py-2.5 text-white rounded-xl font-bold transition disabled:opacity-50 shadow-sm"
            style={{ backgroundColor: ARTE_NAVY }}>
            {saving ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
        </form>
      </div>
    </div>
  )
}
