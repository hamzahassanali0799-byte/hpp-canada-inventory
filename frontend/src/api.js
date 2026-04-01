const API_KEY = 'changeme'
// When deployed separately (e.g., frontend on Vercel, backend on Render),
// set VITE_API_URL to the backend URL. Otherwise defaults to same-origin.
const API_BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-API-Key': API_KEY,
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res
}

export async function fetchLabels(search = '', brand = '', category = '') {
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (brand) params.set('brand', brand)
  if (category) params.set('category', category)
  const qs = params.toString() ? `?${params}` : ''
  const res = await request(`/api/labels${qs}`)
  return res.json()
}

export async function createLabel(data) {
  const res = await request('/api/labels', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function updateLabel(id, data) {
  const res = await request(`/api/labels/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return res.json()
}

export async function deleteLabel(id) {
  const res = await request(`/api/labels/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function adjustStock(id, quantity, mode = 'bottle', description = '') {
  const res = await request(`/api/labels/${id}/adjust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quantity, mode, description }),
  })
  return res.json()
}

export async function scanInvoice(file) {
  const form = new FormData()
  form.append('file', file)
  // Call Render backend directly to avoid Vercel's 30s proxy timeout
  const SCAN_URL = import.meta.env.VITE_SCAN_URL || 'https://hpp-canada-inventory.onrender.com'
  const res = await fetch(`${SCAN_URL}/api/invoice/scan`, {
    method: 'POST',
    headers: { 'X-API-Key': API_KEY },
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Scan failed')
  }
  return res.json()
}

export async function confirmInvoice(items, invoiceNumber = '') {
  const res = await request('/api/invoice/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items, invoice_number: invoiceNumber }),
  })
  return res.json()
}

export async function fetchJournalEntries(status = '') {
  const params = status ? `?status=${encodeURIComponent(status)}` : ''
  const res = await request(`/api/journal${params}`)
  return res.json()
}

export async function exportCSV() {
  const res = await request('/api/journal/export/csv')
  return res.text()
}

export async function deleteJournalEntry(id) {
  const res = await request(`/api/journal/${id}`, { method: 'DELETE' })
  return res.json()
}
