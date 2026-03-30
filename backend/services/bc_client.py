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


async def post_to_bc(db: Session) -> dict:
    base_url = os.getenv("BC_BASE_URL")
    company_id = os.getenv("BC_COMPANY_ID")
    username = os.getenv("BC_USERNAME")
    password = os.getenv("BC_PASSWORD")

    if not all([base_url, company_id, HAS_HTTPX]):
        return {"error": "BC integration not configured or httpx not installed"}

    entries = db.query(JournalEntry).filter(JournalEntry.status == "Pending").all()
    results = []

    async with httpx.AsyncClient(auth=(username, password) if username else None) as client:
        for e in entries:
            payload = {
                "journalBatchName": e.journal_batch,
                "accountNumber": e.item_no,
                "postingDate": e.posting_date,
                "documentType": " ",
                "amount": e.quantity if e.entry_type == "Positive Adjmt." else -e.quantity,
                "description": e.description,
            }
            url = f"{base_url}/companies({company_id})/journals"
            resp = await client.post(url, json=payload)
            if resp.status_code in (200, 201):
                e.status = "Exported"
                results.append({"id": e.id, "status": "ok"})
            else:
                results.append({"id": e.id, "status": "error", "detail": resp.text})
        db.commit()

    return {"results": results}
