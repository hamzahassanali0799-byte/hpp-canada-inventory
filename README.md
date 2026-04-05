# HPP Canada Inventory Management System

Inventory tracker for HPP Canada beverage labels — Arte, Joosy, Quirks brands.

## Stack

- **Frontend** — React + Vite, deployed on **Vercel**
- **Backend** — FastAPI + SQLite, deployed on **Railway**
- **AI Scanner** — Claude Haiku 4.5 (primary), Gemini Flash 2.0 (fallback)

## Features

- **Dashboard** — Card grid with bottle images, stock levels, +/- adjusters, reorder alerts, expiry tracking
- **Smart Scanner** — Upload any document (invoices, packing slips, delivery notes, receipts) → AI extracts line items → searchable product picker → confirm & post to inventory
- **Cycle Count** — Bulk stock counting
- **Journal** — Every stock change logged; export as CSV
- **Global Search** — Search across all inventory items
- **Add/Remove Stock** — Toggle between adding and removing stock via scanner

## Deployment

| Service | URL | Auto-deploy |
|---------|-----|-------------|
| Frontend (Vercel) | Via `vercel.json` proxy | On push to master |
| Backend (Railway) | `hpp-canada-inventory-production.up.railway.app` | On push to master |

**Important:** The scanner bypasses Vercel's proxy (30s timeout) and calls Railway directly. The scan URL is configured in `frontend/src/api.js`.

## Quick Start (Local)

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For scanner (primary) | Claude Haiku 4.5 vision |
| `GEMINI_API_KEY` | For scanner (fallback) | Gemini Flash 2.0 |
| `API_KEY` | Yes | API auth key (default: `changeme`) |
| `BC_BASE_URL` | No | Business Central OData endpoint |
| `BC_COMPANY_ID` | No | BC company GUID |
| `BC_USERNAME` | No | BC auth username |
| `BC_PASSWORD` | No | BC auth password |

## Scanner Details

- Images compressed to **900px wide, 72% JPEG quality** before sending to AI (faster upload, no accuracy loss)
- Prompt includes up to 80 known inventory items as matching hints
- Hardcoded FG code mapping + keyword matching + DB fuzzy matching
- 3-step progress indicator: Uploading → Analyzing → Extracting
- Auto-retry up to 3 times on failure

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/labels` | List labels (optional `?search=&brand=&category=`) |
| POST | `/api/labels` | Create label |
| PATCH | `/api/labels/{id}` | Update label |
| DELETE | `/api/labels/{id}` | Delete label |
| POST | `/api/labels/{id}/adjust` | Adjust stock (+/- bottles or cases) |
| GET | `/api/labels/{id}/history` | Stock history for a label |
| POST | `/api/labels/bulk-count` | Bulk cycle count |
| POST | `/api/invoice/scan` | Scan document (multipart image/PDF) |
| POST | `/api/invoice/confirm` | Confirm scanned items to inventory |
| GET | `/api/journal` | List journal entries |
| GET | `/api/journal/export/csv` | Download CSV export |
| DELETE | `/api/journal/{id}` | Delete journal entry |

## Brands & Products

- **Arte** — Orange, Lime, Lemon, Grapefruit (1L bottles)
- **Joosy** — Tropical, Mandarin, Blueberry, Apple (1L and 300ml)
- **Quirks** — Blueberry, Sunshine, Apple, Tropical (250ml)
