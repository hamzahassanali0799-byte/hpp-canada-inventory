# Arte Label Inventory Management System

HPP food & beverage label inventory tracker for Arte juice labels (drinkarte.com).

## Features

- **Dashboard** — Card grid with real Arte bottle images, stock levels, +/- adjusters, shelf life badges
- **Invoice Scan** — Upload invoice image → Groq AI (Llama 3.2 90B Vision) extracts line items → confirm & post
- **BC Journal** — Every stock change queues a Business Central journal entry; export as CSV
- **Add/Edit Labels** — Full CRUD with Arte bottle previews and brand colors

## Quick Start

### Backend
```bash
cd label-inventory
pip install -r backend/requirements.txt
# Edit .env with your GROQ_API_KEY (free at console.groq.com)
uvicorn backend.main:app --reload --port 8000
```

### Frontend (dev)
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — API proxied to :8000.

### Production
```bash
cd frontend && npm run build
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | For invoice scan | Free at console.groq.com |
| `API_KEY` | Yes | API auth key (default: `changeme`) |
| `BC_BASE_URL` | No | Business Central OData endpoint |
| `BC_COMPANY_ID` | No | BC company GUID |
| `BC_USERNAME` | No | BC auth username |
| `BC_PASSWORD` | No | BC auth password |

## AI Model

Uses **Llama 3.2 90B Vision** via Groq (free tier, no credit card needed).
Handles invoice OCR, line item extraction, and fuzzy matching to known labels.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/labels` | List labels (optional `?search=`) |
| POST | `/api/labels` | Create label |
| PATCH | `/api/labels/{id}` | Update label |
| POST | `/api/labels/{id}/adjust` | Adjust stock |
| POST | `/api/invoice/scan` | Scan invoice (multipart) |
| POST | `/api/invoice/confirm` | Confirm scanned items |
| GET | `/api/journal` | List journal entries |
| GET | `/api/journal/export/csv` | Download BC CSV |
| DELETE | `/api/journal/{id}` | Delete entry |

## Pre-Seeded Labels

| Label | Flavor | Size | Shelf Life | Item Code |
|-------|--------|------|------------|-----------|
| Arte Orange | Orange | 1L | 250 days | ARTE-ORG-1L |
| Arte Lime | Lime | 1L | 395 days | ARTE-LME-1L |
| Arte Lemon | Lemon | 1L | 395 days | ARTE-LMN-1L |
| Arte Grapefruit | Grapefruit | 1L | 240 days | ARTE-GRF-1L |
