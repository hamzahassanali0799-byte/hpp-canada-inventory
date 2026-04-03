from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db.database import get_db
from backend.models.label import Label
from backend.models.journal_entry import JournalEntry
from backend.services.bc_client import create_journal_entry
from datetime import date

router = APIRouter(prefix="/api/labels", tags=["labels"])


class LabelCreate(BaseModel):
    brand: str = "Arte"
    category: str = "bottle"
    label_name: str
    flavor: str
    size: str = "1L"
    color_identifier: str
    item_code: str
    location_code: str = "MAIN"
    unit_of_measure: str = "BTL"
    case_quantity: int = 6
    shelf_life_days: int
    current_stock_bottles: int = 0
    min_stock: int = 0
    reorder_qty: int = 0
    expiry_date: str | None = None
    notes: str = ""


class LabelUpdate(BaseModel):
    item_code: str | None = None
    location_code: str | None = None
    min_stock: int | None = None
    reorder_qty: int | None = None
    expiry_date: str | None = None
    notes: str | None = None


class BulkCountItem(BaseModel):
    label_id: int
    actual_count: int


class StockAdjust(BaseModel):
    quantity: int
    mode: str = "bottle"
    description: str = ""


@router.get("")
def list_labels(
    search: str = "",
    brand: str = "",
    category: str = "",
    db: Session = Depends(get_db),
):
    query = db.query(Label)
    if brand:
        query = query.filter(Label.brand == brand)
    if category:
        query = query.filter(Label.category == category)
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            (Label.flavor.ilike(search_lower)) | (Label.item_code.ilike(search_lower))
        )
    labels = query.order_by(Label.brand, Label.label_name).all()
    return [l.to_dict() for l in labels]


@router.get("/{label_id}")
def get_label(label_id: int, db: Session = Depends(get_db)):
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    return label.to_dict()


@router.post("")
def create_label(data: LabelCreate, db: Session = Depends(get_db)):
    existing = db.query(Label).filter(Label.item_code == data.item_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Item code already exists")
    label = Label(**data.model_dump())
    db.add(label)
    db.commit()
    db.refresh(label)
    return label.to_dict()


@router.patch("/{label_id}")
def update_label(label_id: int, data: LabelUpdate, db: Session = Depends(get_db)):
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(label, key, value)
    db.commit()
    db.refresh(label)
    return label.to_dict()


@router.delete("/{label_id}")
def delete_label(label_id: int, db: Session = Depends(get_db)):
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    db.delete(label)
    db.commit()
    return {"ok": True}


@router.post("/{label_id}/adjust")
def adjust_stock(label_id: int, data: StockAdjust, db: Session = Depends(get_db)):
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    qty_bottles = data.quantity if data.mode == "bottle" else data.quantity * label.case_quantity
    label.current_stock_bottles = max(0, label.current_stock_bottles + qty_bottles)
    db.commit()
    db.refresh(label)

    entry_type = "Positive Adjmt." if qty_bottles > 0 else "Negative Adjmt."
    desc = data.description or f"{label.label_name} {label.size} — Manual adjustment"
    create_journal_entry(
        db=db,
        item_no=label.item_code,
        location_code=label.location_code,
        entry_type=entry_type,
        quantity=qty_bottles,
        description=desc,
        posting_date=date.today().isoformat(),
    )

    return label.to_dict()


@router.get("/{label_id}/history")
def get_history(label_id: int, db: Session = Depends(get_db)):
    label = db.query(Label).filter(Label.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")
    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.item_no == label.item_code)
        .order_by(JournalEntry.created_at.desc())
        .limit(15)
        .all()
    )
    return [
        {
            "id": e.id,
            "entry_type": e.entry_type,
            "quantity": e.quantity,
            "description": e.description,
            "posting_date": e.posting_date,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.post("/bulk-count")
def bulk_count(items: list[BulkCountItem], db: Session = Depends(get_db)):
    results = []
    for item in items:
        label = db.query(Label).filter(Label.id == item.label_id).first()
        if not label:
            continue
        diff = item.actual_count - label.current_stock_bottles
        if diff == 0:
            continue
        label.current_stock_bottles = max(0, item.actual_count)
        entry_type = "Positive Adjmt." if diff > 0 else "Negative Adjmt."
        create_journal_entry(
            db=db,
            item_no=label.item_code,
            location_code=label.location_code,
            entry_type=entry_type,
            quantity=diff,
            description=f"Cycle count — {label.label_name}",
            posting_date=date.today().isoformat(),
        )
        results.append({"id": label.id, "item_code": label.item_code, "diff": diff})
    db.commit()
    return {"adjusted": len(results), "results": results}
