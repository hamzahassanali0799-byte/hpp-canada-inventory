from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.models.journal_entry import JournalEntry
from backend.services.bc_client import export_csv, post_to_bc
import io

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("")
def list_entries(status: str = "", db: Session = Depends(get_db)):
    query = db.query(JournalEntry)
    if status:
        query = query.filter(JournalEntry.status == status)
    entries = query.order_by(JournalEntry.created_at.desc()).all()
    return [e.to_dict() for e in entries]


@router.get("/export/csv")
def export_to_csv(db: Session = Depends(get_db)):
    csv_content = export_csv(db)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bc_item_journal.csv"},
    )


@router.post("/export/bc")
async def export_to_bc(db: Session = Depends(get_db)):
    result = await post_to_bc(db)
    return result


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
    return {"ok": True}
