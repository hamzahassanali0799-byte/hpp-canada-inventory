import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.db.database import engine, SessionLocal, Base
from backend.models.label import Label  # noqa: F401
from backend.models.journal_entry import JournalEntry  # noqa: F401
from backend.routers import labels, invoice_scan, journal
from backend.services.seeder import seed_labels

Base.metadata.create_all(bind=engine)

# Seed on startup
db = SessionLocal()
seed_labels(db)
db.close()

app = FastAPI(title="Label Inventory Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "changeme")


@app.middleware("http")
async def check_api_key(request: Request, call_next):
    # Skip auth for health endpoint (keep-alive pings)
    if request.url.path == "/api/health":
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return await call_next(request)


app.include_router(labels.router)
app.include_router(invoice_scan.router)
app.include_router(journal.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static files if built
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
