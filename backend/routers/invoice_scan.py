from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.models.label import Label
from backend.services.claude_extractor import extract_invoice
from backend.services.bc_client import create_journal_entry
from datetime import date

router = APIRouter(prefix="/api/invoice", tags=["invoice"])


class ConfirmItem(BaseModel):
    matched_item_code: str
    quantity_bottles: int
    description: str = ""


class ConfirmPayload(BaseModel):
    items: list[ConfirmItem]
    invoice_number: str = ""


@router.post("/scan")
async def scan_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.content_type:
        raise HTTPException(status_code=400, detail="No content type")

    allowed = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    try:
        result = await extract_invoice(file_bytes, file.content_type, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return result


@router.post("/confirm")
def confirm_items(payload: ConfirmPayload, db: Session = Depends(get_db)):
    results = []
    for item in payload.items:
        label = db.query(Label).filter(Label.item_code == item.matched_item_code).first()
        if not label:
            results.append({"item_code": item.matched_item_code, "status": "error", "detail": "Label not found"})
            continue

        label.current_stock_bottles += item.quantity_bottles
        db.commit()
        db.refresh(label)

        desc = item.description or f"{label.label_name} {label.size}"
        if payload.invoice_number:
            desc += f" — Invoice #{payload.invoice_number}"

        create_journal_entry(
            db=db,
            item_no=label.item_code,
            location_code=label.location_code,
            entry_type="Positive Adjmt.",
            quantity=item.quantity_bottles,
            description=desc,
            posting_date=date.today().isoformat(),
        )

        results.append({
            "item_code": item.matched_item_code,
            "status": "ok",
            "new_stock": label.current_stock_bottles,
        })

    return {"results": results}
