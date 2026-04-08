import base64
import json
import io
import os
import re
import httpx
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy.orm import Session
from backend.models.label import Label


def compress_image(file_bytes: bytes) -> tuple[str, str]:
    """Resize and enhance phone photo for better AI text extraction.
    Handles low-res and blurry phone camera images."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    is_small = img.width < 900

    if is_small:
        # Upscale small/low-res images to improve OCR
        target_width = 1200
        ratio = target_width / img.width
        img = img.resize((target_width, int(img.height * ratio)), Image.LANCZOS)
        # Auto-contrast to improve text readability on low-quality cameras
        img = ImageOps.autocontrast(img, cutoff=1)
        # Sharpen text edges for blurry images
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.8)
        quality = 88
    elif img.width > 1400:
        # Resize large images down
        ratio = 1400 / img.width
        img = img.resize((1400, int(img.height * ratio)), Image.LANCZOS)
        quality = 82
    else:
        # Medium-size images: mild auto-contrast enhancement
        img = ImageOps.autocontrast(img, cutoff=1)
        quality = 85

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"


# ── Product matching — pure Python ──

FG_CODES = {
    "fg-1516": "ARTE-LME-1L-BTL",
    "fg-1515": "ARTE-LMN-1L-BTL",
    "fg-1514": "ARTE-GRF-1L-BTL",
    "fg-1513": "ARTE-ORG-1L-BTL",
}

KEYWORDS = {
    ("arte", "orange"): "ARTE-ORG-1L-BTL",
    ("arte", "lime"): "ARTE-LME-1L-BTL",
    ("arte", "lemon"): "ARTE-LMN-1L-BTL",
    ("arte", "grapefruit"): "ARTE-GRF-1L-BTL",
    ("quirk", "blueberry"): "QRKS-BLU-250-BTL",
    ("quirk", "sunshine"): "QRKS-SUN-250-BTL",
    ("quirk", "apple"): "QRKS-APL-250-BTL",
    ("quirk", "tropical"): "QRKS-TRP-250-BTL",
    ("joosy", "tropical", "1l"): "JOOS-TRP-1L-BTL",
    ("joosy", "mandarin", "1l"): "JOOS-MAN-1L-BTL",
    ("joosy", "blueberry", "1l"): "JOOS-BLU-1L-BTL",
    ("joosy", "apple", "1l"): "JOOS-APL-1L-BTL",
    ("joosy", "tropical", "300"): "JOOS-TRP-300-BTL",
    ("joosy", "mandarin", "300"): "JOOS-MAN-300-BTL",
    ("joosy", "blueberry", "300"): "JOOS-BLU-300-BTL",
    ("joosy", "apple", "300"): "JOOS-APL-300-BTL",
}


def match_product(desc: str, supplier_code: str, item_no: str = "") -> str | None:
    d = desc.lower()

    # Check FG codes in supplier code and item_no
    for candidate in [supplier_code, item_no]:
        n = (candidate or "").lower().replace(" ", "-")
        fg = re.search(r'fg[- ]?(\d+)', n)
        if fg:
            key = f"fg-{fg.group(1)}"
            if key in FG_CODES:
                return FG_CODES[key]

    best = None
    best_s = 0
    for kws, code in KEYWORDS.items():
        s = sum(1 for k in kws if k in d)
        if s == len(kws) and s > best_s:
            best = code
            best_s = s
    if best:
        return best

    if "arte" in d or "drink" in d:
        for f, c in [("lime", "ARTE-LME-1L-BTL"), ("lemon", "ARTE-LMN-1L-BTL"),
                      ("grapefruit", "ARTE-GRF-1L-BTL"), ("orange", "ARTE-ORG-1L-BTL")]:
            if f in d:
                return c
    return None


def match_product_db(desc: str, supplier_code: str, db_labels) -> str | None:
    """Try to match against actual DB items using supplier code first, then description."""
    d = desc.lower()
    sc = (supplier_code or "").strip().upper()

    # 1. Exact match: supplier code == item_code
    for label in db_labels:
        if sc and label.item_code.upper() == sc:
            return label.item_code

    # 2. Partial match — only if supplier code is >= 5 chars to avoid false positives
    #    (e.g., avoid "1" matching "ARTE-LME-1L-BTL")
    if len(sc) >= 5:
        for label in db_labels:
            if sc in label.item_code.upper() or label.item_code.upper() in sc:
                return label.item_code

    # 3. Keyword match against label_name — require >= 2 meaningful words (min 4 chars
    #    to filter out short tokens like "1l", "art", "the" causing false matches)
    best = None
    best_score = 0
    for label in db_labels:
        words = label.label_name.lower().split()
        score = sum(1 for w in words if len(w) >= 4 and w in d)
        if score > best_score and score >= 2:
            best = label.item_code
            best_score = score

    return best


def _make_safe_code(supplier_code: str, desc: str) -> str | None:
    """Generate a safe item_code from supplier code or description."""
    if supplier_code:
        safe = re.sub(r'[^A-Za-z0-9\-]', '-', supplier_code).upper()
        safe = re.sub(r'-+', '-', safe).strip('-')
        return safe[:50] if safe else None
    if desc:
        words = re.sub(r'[^A-Za-z0-9 ]', '', desc).split()[:4]
        safe = '-'.join(w[:5].upper() for w in words if w)
        return safe[:50] if safe else None
    return None


def process(raw: dict, db_labels=None, db=None, supplier_name: str = "") -> dict:
    header = raw.get("header", {})
    supplier = header.get("company") or supplier_name or ""
    items = []
    db_labels = list(db_labels or [])  # local mutable copy for auto-created items

    for row in raw.get("rows", []):
        desc = str(row.get("desc", ""))
        no = str(row.get("no", ""))
        supplier_code = str(row.get("code", ""))  # supplier item code, e.g. AS-32-36/IO
        qty = int(row.get("qty", 0) or 0)
        unit = str(row.get("unit", ""))
        price = float(row.get("price", 0) or 0)
        total = float(row.get("total", 0) or 0)

        # Math validation: if price×qty doesn't match total, recalculate
        if price > 0 and total > 0:
            calc = round(total / price)
            if abs(calc - qty) > 1:
                qty = calc

        # Try hardcoded match first (FG codes / brand keywords), then DB match
        matched = match_product(desc, supplier_code, no)
        if not matched and db_labels:
            matched = match_product_db(desc, supplier_code, db_labels)

        warnings = []

        # Auto-create product if no match found and we have identifying info
        if not matched and (supplier_code or desc) and db is not None:
            safe_code = _make_safe_code(supplier_code, desc)
            if safe_code:
                # Check if already exists in our local list (avoids duplicates within one scan)
                existing = next((l for l in db_labels if l.item_code.upper() == safe_code.upper()), None)
                if existing:
                    matched = existing.item_code
                else:
                    try:
                        new_label = Label(
                            brand=supplier or "Unknown",
                            category="bottle",
                            label_name=desc or supplier_code,
                            item_code=safe_code,
                            flavor="",
                            size="",
                            color_identifier="",
                            current_stock_bottles=0,
                            case_quantity=6,
                            shelf_life_days=9999,
                            min_stock=0,
                            reorder_qty=0,
                            location_code="MAIN",
                            unit_of_measure="BTL",
                        )
                        db.add(new_label)
                        db.commit()
                        db.refresh(new_label)
                        db_labels.append(new_label)
                        matched = new_label.item_code
                        warnings.append("auto_created")
                    except Exception:
                        db.rollback()
                        warnings.append("no_match")
            else:
                warnings.append("no_match")
        elif not matched:
            warnings.append("no_match")

        case_size = 6
        bottles = qty * case_size if "case" in unit.lower() else qty

        if qty == 0:
            warnings.append("no_qty")
        if not desc or desc.lower() in ("", "nan"):
            warnings.append("no_desc")

        # Build display description — show supplier code in brackets if present
        if supplier_code:
            display_desc = f"{desc} [{supplier_code}]" if desc else supplier_code
        elif no and no not in ("0", ""):
            display_desc = f"{desc} [{no}]" if desc else no
        else:
            display_desc = desc

        items.append({
            "description": display_desc,
            "quantity_bottles": bottles,
            "quantity_cases": qty if "case" in unit.lower() else None,
            "unit_price": price if price > 0 else None,
            "matched_item_code": matched,
            "warnings": warnings,
            "raw_item_no": no,
            "raw_supplier_code": supplier_code,
            "raw_unit": unit,
        })

    return {
        "items": items,
        "invoice_number": header.get("inv") or "",
        "supplier": header.get("company") or "",
        "invoice_date": header.get("date") or "",
    }


# ── Single Gemini call ──

async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not os.getenv("ANTHROPIC_API_KEY") and not gemini_key:
        raise ValueError("Set ANTHROPIC_API_KEY or GEMINI_API_KEY")

    b64, mime = compress_image(file_bytes)

    # Build list of known items for smarter matching
    known = db.query(Label).all()
    item_hints = ", ".join(f"{l.item_code}={l.label_name}" for l in known[:80])

    prompt = (
        'Read this invoice/packing slip/delivery note EXACTLY as printed. '
        'NOTE: The image may be low quality, blurry, or taken with a low-resolution phone camera — '
        'try your best to read text even if it is blurry or partially obscured.\n\n'
        'Do NOT paraphrase, interpret, or correct any text. Copy every word and number character-for-character.\n\n'
        'CRITICAL RULES:\n'
        '- The "code" field must contain the supplier/product code printed on the document '
        '(e.g. AS-32-36/IO, AS-36-C/old/White/Cap, FG-1516). These are alphanumeric codes '
        'with dashes or slashes — NOT row numbers.\n'
        '- The "no" field is for the row/line number only (1, 2, 3...).\n'
        '- Product descriptions must be copied verbatim from the document.\n'
        '- Quantities: read the EXACT number printed. Never default to 0 if a number is visible.\n'
        '- Each row in the document = one row in output. Do NOT merge or duplicate rows.\n\n'
        'For each line item extract:\n'
        '  no = row/line number as printed\n'
        '  code = supplier item/product code (alphanumeric with dashes/slashes, e.g. AS-32-36/IO)\n'
        '  desc = full product description as printed\n'
        '  qty = quantity number only\n'
        '  unit = Case/Bottle/Each/KG/L\n'
        '  price = unit price\n'
        '  total = line total\n\n'
        f'Known inventory items (for reference only): [{item_hints}]\n\n'
        'Return ONLY valid JSON:\n'
        '{"header":{"inv":"invoice number","company":"company name","date":"date"},'
        '"rows":[{"no":"","code":"","desc":"","qty":0,"unit":"","price":0,"total":0}]}'
    )

    raw = None

    # Try Claude Haiku first (primary)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 2048,
                        "temperature": 0,
                        "messages": [{"role": "user", "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                            {"type": "text", "text": prompt},
                        ]}],
                    },
                )
            if resp.status_code == 200:
                text = resp.json()["content"][0]["text"].strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                raw = json.loads(text)
        except Exception:
            pass

    # Fallback to Gemini Flash
    if not raw and gemini_key:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": b64}},
                    ]}], "generationConfig": {"temperature": 0.0}},
                )
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                raw = json.loads(text)
        except Exception:
            pass

    if not raw or not raw.get("rows"):
        raise ValueError("Could not read document. Make sure text is clear and readable.")

    return process(raw, db_labels=known, db=db, supplier_name="")
