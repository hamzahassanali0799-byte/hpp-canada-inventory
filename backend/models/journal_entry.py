from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from backend.db.database import Base


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    journal_batch = Column(String(20), nullable=False, default="INV-ADJ")
    item_no = Column(String(50), nullable=False)
    location_code = Column(String(20), nullable=False, default="MAIN")
    entry_type = Column(String(30), nullable=False)  # "Positive Adjmt." or "Negative Adjmt."
    quantity = Column(Integer, nullable=False)
    unit_of_measure = Column(String(10), nullable=False, default="BTL")
    description = Column(Text, default="")
    posting_date = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="Pending")  # Pending / Exported
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "journal_batch": self.journal_batch,
            "item_no": self.item_no,
            "location_code": self.location_code,
            "entry_type": self.entry_type,
            "quantity": self.quantity,
            "unit_of_measure": self.unit_of_measure,
            "description": self.description,
            "posting_date": self.posting_date,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
