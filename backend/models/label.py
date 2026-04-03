from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from backend.db.database import Base


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(50), nullable=False, default="Arte")
    category = Column(String(20), nullable=False, default="bottle")  # "label", "bottle", "box"
    label_name = Column(String(100), nullable=False)
    flavor = Column(String(50), nullable=False)
    size = Column(String(30), nullable=False, default="1L")  # "1L", "300mL", "19x10x8", "24x17x19"
    color_identifier = Column(String(30), nullable=False)
    item_code = Column(String(50), nullable=False, unique=True)
    location_code = Column(String(20), nullable=False, default="MAIN")
    unit_of_measure = Column(String(10), nullable=False, default="BTL")
    case_quantity = Column(Integer, nullable=False, default=6)
    shelf_life_days = Column(Integer, nullable=False)
    current_stock_bottles = Column(Integer, nullable=False, default=0)
    min_stock = Column(Integer, nullable=False, default=0)
    reorder_qty = Column(Integer, nullable=False, default=0)
    expiry_date = Column(String(10), nullable=True)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    notes = Column(Text, default="")

    @property
    def current_stock_cases(self) -> int:
        return self.current_stock_bottles // self.case_quantity if self.case_quantity else 0

    def to_dict(self):
        return {
            "id": self.id,
            "brand": self.brand,
            "category": self.category,
            "label_name": self.label_name,
            "flavor": self.flavor,
            "size": self.size,
            "color_identifier": self.color_identifier,
            "item_code": self.item_code,
            "location_code": self.location_code,
            "unit_of_measure": self.unit_of_measure,
            "case_quantity": self.case_quantity,
            "shelf_life_days": self.shelf_life_days,
            "current_stock_bottles": self.current_stock_bottles,
            "current_stock_cases": self.current_stock_cases,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "min_stock": self.min_stock,
            "reorder_qty": self.reorder_qty,
            "expiry_date": self.expiry_date,
            "notes": self.notes or "",
        }
