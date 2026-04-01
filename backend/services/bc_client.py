import csv
import io
import os
from datetime import date
from sqlalchemy.orm import Session
from backend.models.journal_entry import JournalEntry

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def create_journal_entry(
    db: Session,
    item_no: str,
    location_code: str,
    entry_type: str,
    quantity: int,
    description: str,
    posting_date: str | None = None,
) -> JournalEntry:
    entry = JournalEntry(
        item_no=item_no,
        location_code=location_code,
        entry_type=entry_type,
        quantity=abs(quantity),
        description=description,
        posting_date=posting_date or date.today().isoformat(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def export_csv(db: Session) -> str:
    entries = db.query(JournalEntry).filter(JournalEntry.status == "Pending").all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Item No.", "Location Code", "Entry Type", "Quantity",
        "Unit of Measure", "Description", "Posting Date"
    ])
    for e in entries:
        writer.writerow([
            e.item_no, e.location_code, e.entry_type, e.quantity,
            e.unit_of_measure, e.description, e.posting_date
        ])
        e.status = "Exported"
    db.commit()
    return output.getvalue()


def _get_bc_config():
    """Get BC configuration from env vars."""
    base_url = os.getenv("BC_BASE_URL")
    company_id = os.getenv("BC_COMPANY_ID")
    username = os.getenv("BC_USERNAME")
    password = os.getenv("BC_PASSWORD")
    return base_url, company_id, username, password


def is_bc_configured():
    """Check if Business Central integration is configured."""
    base_url, company_id, username, password = _get_bc_config()
    return bool(base_url and company_id and HAS_HTTPX)


async def test_bc_connection() -> dict:
    """Test the Business Central connection."""
    base_url, company_id, username, password = _get_bc_config()

    if not base_url or not company_id:
        return {"connected": False, "error": "BC_BASE_URL and BC_COMPANY_ID not configured in .env"}
    if not HAS_HTTPX:
        return {"connected": False, "error": "httpx not installed"}

    try:
        async with httpx.AsyncClient(
            auth=(username, password) if username else None,
            timeout=15.0,
        ) as client:
            url = f"{base_url}/companies({company_id})"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "connected": True,
                    "company_name": data.get("name", "Unknown"),
                    "company_id": company_id,
                }
            else:
                return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


async def post_to_bc(db: Session) -> dict:
    base_url, company_id, username, password = _get_bc_config()

    if not all([base_url, company_id, HAS_HTTPX]):
        return {"error": "BC integration not configured. Set BC_BASE_URL, BC_COMPANY_ID, BC_USERNAME, BC_PASSWORD in .env"}

    entries = db.query(JournalEntry).filter(JournalEntry.status == "Pending").all()
    if not entries:
        return {"results": [], "message": "No pending entries to export"}

    results = []

    async with httpx.AsyncClient(
        auth=(username, password) if username else None,
        timeout=30.0,
    ) as client:
        for e in entries:
            payload = {
                "journalBatchName": e.journal_batch,
                "accountNumber": e.item_no,
                "postingDate": e.posting_date,
                "documentType": " ",
                "amount": e.quantity if e.entry_type == "Positive Adjmt." else -e.quantity,
                "description": e.description[:50],  # BC has 50 char limit
            }
            url = f"{base_url}/companies({company_id})/journals"
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code in (200, 201):
                    e.status = "Exported"
                    results.append({"id": e.id, "status": "ok"})
                else:
                    results.append({"id": e.id, "status": "error", "detail": resp.text[:200]})
            except Exception as ex:
                results.append({"id": e.id, "status": "error", "detail": str(ex)})
        db.commit()

    return {"results": results}
