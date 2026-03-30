from sqlalchemy.orm import Session
from backend.models.label import Label


def _btl(brand, flavor, size, color, code, case_qty, shelf, notes):
    return {"brand": brand, "category": "juice", "label_name": f"{brand} {flavor} {size}" if size != "1L" else f"{brand} {flavor}",
            "flavor": flavor, "size": size, "color_identifier": color, "item_code": code,
            "location_code": "MAIN", "unit_of_measure": "BTL", "case_quantity": case_qty,
            "shelf_life_days": shelf, "current_stock_bottles": 0, "notes": notes}


def _ebt(brand, flavor, size, color, code, case_qty, notes):
    return {"brand": brand, "category": "bottle", "label_name": f"{brand} {flavor} Empty {size}",
            "flavor": flavor, "size": size, "color_identifier": color, "item_code": code,
            "location_code": "MAIN", "unit_of_measure": "BTL", "case_quantity": case_qty,
            "shelf_life_days": 9999, "current_stock_bottles": 0, "notes": notes}


def _lbl(brand, flavor, size, color, code, notes):
    return {"brand": brand, "category": "label", "label_name": f"{brand} {flavor} Label" + (f" {size}" if size != "1L" else ""),
            "flavor": flavor, "size": size, "color_identifier": color, "item_code": code,
            "location_code": "MAIN", "unit_of_measure": "EA", "case_quantity": 100,
            "shelf_life_days": 9999, "current_stock_bottles": 0, "notes": notes}


def _box(name, size, code, notes):
    return {"brand": "General", "category": "box", "label_name": name,
            "flavor": name, "size": size, "color_identifier": "box",
            "item_code": code, "location_code": "MAIN", "unit_of_measure": "EA",
            "case_quantity": 1, "shelf_life_days": 9999, "current_stock_bottles": 0, "notes": notes}


ARTE_NOTE = "HPP Certified, 100% Natural, No Preservatives, Cold Pressed"
QUIRK_NOTE = "Cold-Pressed Juice, No Added Sugar, No Preservatives"
JOOSY_NOTE = "Cold Pressed, No Added Sugar"

SEED_LABELS = [
    # ── ARTE Bottles ──
    _btl("Arte", "Orange",     "1L", "arte-orange",     "ARTE-ORG-1L-BTL",  6, 250, ARTE_NOTE),
    _btl("Arte", "Lime",       "1L", "arte-lime",       "ARTE-LME-1L-BTL",  6, 395, ARTE_NOTE),
    _btl("Arte", "Lemon",      "1L", "arte-lemon",      "ARTE-LMN-1L-BTL",  6, 395, ARTE_NOTE),
    _btl("Arte", "Grapefruit", "1L", "arte-grapefruit", "ARTE-GRF-1L-BTL",  6, 240, ARTE_NOTE),
    # ── ARTE Labels ──
    _lbl("Arte", "Orange",     "1L", "arte-orange",     "ARTE-ORG-1L-LBL",  "Label roll for Arte Orange 1L"),
    _lbl("Arte", "Lime",       "1L", "arte-lime",       "ARTE-LME-1L-LBL",  "Label roll for Arte Lime 1L"),
    _lbl("Arte", "Lemon",      "1L", "arte-lemon",      "ARTE-LMN-1L-LBL",  "Label roll for Arte Lemon 1L"),
    _lbl("Arte", "Grapefruit", "1L", "arte-grapefruit", "ARTE-GRF-1L-LBL",  "Label roll for Arte Grapefruit 1L"),
    # ── QUIRKIES Bottles ──
    _btl("Quirkies", "Blueberry Blend", "250mL", "quirk-blueberry", "QRKS-BLU-250-BTL", 12, 120, QUIRK_NOTE),
    _btl("Quirkies", "Sunshine",         "250mL", "quirk-sunshine",  "QRKS-SUN-250-BTL", 12, 120, QUIRK_NOTE),
    _btl("Quirkies", "100% Apple",       "250mL", "quirk-apple",     "QRKS-APL-250-BTL", 12, 120, QUIRK_NOTE),
    _btl("Quirkies", "Tropical Twist",   "250mL", "quirk-tropical",  "QRKS-TRP-250-BTL", 12, 120, QUIRK_NOTE),
    # ── QUIRKIES Labels ──
    _lbl("Quirkies", "Blueberry Blend", "250mL", "quirk-blueberry", "QRKS-BLU-250-LBL", "Label for Quirkies Blueberry Blend"),
    _lbl("Quirkies", "Sunshine",         "250mL", "quirk-sunshine",  "QRKS-SUN-250-LBL", "Label for Quirkies Sunshine"),
    _lbl("Quirkies", "100% Apple",       "250mL", "quirk-apple",     "QRKS-APL-250-LBL", "Label for Quirkies 100% Apple"),
    _lbl("Quirkies", "Tropical Twist",   "250mL", "quirk-tropical",  "QRKS-TRP-250-LBL", "Label for Quirkies Tropical Twist"),
    # ── JOOSY Bottles 1L ──
    _btl("Joosy", "Tropical Pulse",  "1L", "joosy-tropical",  "JOOS-TRP-1L-BTL",  6, 120, "Pineapple/Mango/Orange — Refresh"),
    _btl("Joosy", "Mandarin Juice",  "1L", "joosy-mandarin",  "JOOS-MAN-1L-BTL",  6, 120, "Mandarin/Orange/Apple — Energizing"),
    _btl("Joosy", "Blueberry Bliss", "1L", "joosy-blueberry", "JOOS-BLU-1L-BTL",  6, 120, "Blueberry/Coconut Water/Cranberry — Glow"),
    _btl("Joosy", "100% Apple",       "1L", "joosy-apple",     "JOOS-APL-1L-BTL",  6, 120, "Unpasteurized Apple"),
    # ── JOOSY Bottles 300mL ──
    _btl("Joosy", "Tropical Pulse",  "300mL", "joosy-tropical",  "JOOS-TRP-300-BTL", 12, 120, "Pineapple/Mango/Orange — Refresh"),
    _btl("Joosy", "Mandarin Juice",  "300mL", "joosy-mandarin",  "JOOS-MAN-300-BTL", 12, 120, "Mandarin/Orange/Apple — Energizing"),
    _btl("Joosy", "Blueberry Bliss", "300mL", "joosy-blueberry", "JOOS-BLU-300-BTL", 12, 120, "Blueberry/Coconut Water/Cranberry — Glow"),
    _btl("Joosy", "100% Apple",       "300mL", "joosy-apple",     "JOOS-APL-300-BTL", 12, 120, "Unpasteurized Apple"),
    # ── JOOSY Labels 1L ──
    _lbl("Joosy", "Tropical Pulse",  "1L", "joosy-tropical",  "JOOS-TRP-1L-LBL",  "Label for Joosy Tropical Pulse 1L"),
    _lbl("Joosy", "Mandarin Juice",  "1L", "joosy-mandarin",  "JOOS-MAN-1L-LBL",  "Label for Joosy Mandarin Juice 1L"),
    _lbl("Joosy", "Blueberry Bliss", "1L", "joosy-blueberry", "JOOS-BLU-1L-LBL",  "Label for Joosy Blueberry Bliss 1L"),
    _lbl("Joosy", "100% Apple",       "1L", "joosy-apple",     "JOOS-APL-1L-LBL",  "Label for Joosy 100% Apple 1L"),
    # ── JOOSY Labels 300mL ──
    _lbl("Joosy", "Tropical Pulse",  "300mL", "joosy-tropical",  "JOOS-TRP-300-LBL", "Label for Joosy Tropical Pulse 300mL"),
    _lbl("Joosy", "Mandarin Juice",  "300mL", "joosy-mandarin",  "JOOS-MAN-300-LBL", "Label for Joosy Mandarin Juice 300mL"),
    _lbl("Joosy", "Blueberry Bliss", "300mL", "joosy-blueberry", "JOOS-BLU-300-LBL", "Label for Joosy Blueberry Bliss 300mL"),
    _lbl("Joosy", "100% Apple",       "300mL", "joosy-apple",     "JOOS-APL-300-LBL", "Label for Joosy 100% Apple 300mL"),
    # ── BOXES ──
    _box("Small Box",  "19x10x8",  "BOX-19x10x8",  "Small shipping box 19\" x 10\" x 8\""),
    _box("Large Box",  "24x17x19", "BOX-24x17x19", "Large shipping box 24\" x 17\" x 19\""),
    # ── EMPTY BOTTLES ──
    _ebt("Arte", "Clear Glass",   "1L",    "arte-orange",     "EBTL-CLR-1L",     6,  "Empty 1L glass bottle for Arte"),
    _ebt("Quirkies", "PET Clear", "250mL", "quirk-apple",     "EBTL-PET-250",    12, "Empty 250mL PET bottle for Quirkies"),
    _ebt("Joosy", "PET Clear",    "1L",    "joosy-apple",     "EBTL-PET-1L",     6,  "Empty 1L PET bottle for Joosy"),
    _ebt("Joosy", "PET Clear",    "300mL", "joosy-apple",     "EBTL-PET-300",    12, "Empty 300mL PET bottle for Joosy"),
]


def seed_labels(db: Session):
    existing = db.query(Label).count()
    if existing > 0:
        return
    for data in SEED_LABELS:
        db.add(Label(**data))
    db.commit()
