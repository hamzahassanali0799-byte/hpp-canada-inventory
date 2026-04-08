import base64
import json
import io
import os
import re
import httpx
from PIL import Image
from sqlalchemy.orm import Session
from backend.models.label import Label


def compress_image(file_bytes: bytes) -> tuple[str, str]:
    """Resize phone photo to reduce upload size. No over-processing."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    # Resize to 1400px wide — readable for AI text extraction
    if img.width > 1400:
        ratio = 1400 / img.width
        img = img.resize((1400, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
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


def match_product(desc: str, item_no: str) -> str | None:
    d = desc.lower()
    n = (item_no or "").lower().replace(" ", "-")

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


def match_product_db(desc: str, item_no: str, db_labels) -> str | None:
    """Try to match against actual DB items. Only use item_no if it looks like a code (not a bare number)."""
    d = desc.lower()
    n = (item_no or "").strip().upper()

    # Only use n for code matching if it has non-digit characters (it's a real code, not just "1" or "12")
    n_is_code = bool(n) and not n.isdigit() and len(n) >= 4

    if n_is_code:
        # Exact item code match
        for label in db_labels:
            if label.item_code.upper() == n:
                return label.item_code

        # Partial item code match — only safe when n is long enough to be unambiguous
        if len(n) >= 5:
            for label in db_labels:
                if n in label.item_code.upper() or label.item_code.upper() in n:
                    return label.item_code

    # Keyword match against label_name — require >= 2 meaningful words (min 4 chars)
    best = None
    best_score = 0
    for label in db_labels:
        words = label.label_name.lower().split()
        score = sum(1 for w in words if len(w) >= 4 and w in d)
        if score > best_score and score >= 2:
            best = label.item_code
            best_score = score

    return best


def _make_safe_code(no: str, desc: str) -> str | None:
    """Generate a safe item_code from item no or description."""
    if no and not no.strip().isdigit():
        safe = re.sub(r'[^A-Za-z0-9\-]', '-', no).upper()
        safe = re.sub(r'-+', '-', safe).strip('-')
        return safe[:50] if safe else None
    if desc:
        words = re.sub(r'[^A-Za-z0-9 ]', '', desc).split()[:4]
        safe = '-'.join(w[:5].upper() for w in words if w)
        return safe[:50] if safe else None
    return None


def process(raw: dict, db_labels=None, db=None) -> dict:
    header = raw.get("header", {})
    items = []

    for row in raw.get("rows", []):
        desc = str(row.get("desc", ""))
        no = str(row.get("no", ""))
        qty = int(row.get("qty", 0) or 0)
        unit = str(row.get("unit", ""))
        price = float(row.get("price", 0) or 0)
        total = float(row.get("total", 0) or 0)

        # Math validation
        if price > 0 and total > 0:
            calc = round(total / price)
            if abs(calc - qty) > 1:
                qty = calc

        # Only use `no` for matching if it looks like an item code, not a plain number
        no_for_match = no if (no and not no.strip().isdigit()) else ""

        # Try hardcoded match first, then DB match
        matched = match_product(desc, no_for_match)
        if not matched and db_labels:
            matched = match_product_db(desc, no_for_match, db_labels)

        # Auto-create product if still no match
        if not matched and db is not None and (desc or no):
            new_code = _make_safe_code(no_for_match, desc)
            if new_code:
                existing = db.query(Label).filter(Label.item_code == new_code).first()
                if not existing:
                    new_label = Label(
                        label_name=desc[:100] or no,
                        flavor="Unknown",
                        item_code=new_code,
                        color_identifier="",
                        shelf_life_days=9999,
                        notes="Auto-created by invoice scanner",
                    )
                    db.add(new_label)
                    db.commit()
                    db.refresh(new_label)
                    if db_labels is not None:
                        db_labels.append(new_label)
                matched = new_code

        case_size = 6
        bottles = qty * case_size if "case" in unit.lower() else qty

        warnings = []
        if not matched:
            warnings.append("no_match")
        if qty == 0:
            warnings.append("no_qty")
        if not desc or desc.lower() in ("", "nan"):
            warnings.append("no_desc")

        items.append({
            "description": f"{desc} [{no}]" if no else desc,
            "quantity_bottles": bottles,
            "quantity_cases": qty if "case" in unit.lower() else None,
            "unit_price": price if price > 0 else None,
            "matched_item_code": matched,
            "warnings": warnings,
            "raw_item_no": no,
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
        'Do NOT paraphrase, interpret, or correct any text. Copy every word and number character-for-character.\n\n'
        'CRITICAL RULES:\n'
        '- Item codes (e.g. FG-1516, FG-1515, FG-1514) must be copied EXACTLY. Never substitute digits.\n'
        '- Product descriptions must be copied verbatim from the document.\n'
        '- Quantities: read the EXACT number printed. Never default to 0 if a number is visible.\n'
        '- Each row in the document = one row in output. Do NOT merge or duplicate rows.\n\n'
        'For each line item extract: no=item code, desc=full product description as printed, '
        'qty=quantity number, unit=Case/Bottle/Each/KG/L, price=unit price, total=line total.\n\n'
        f'Known inventory items for reference (use for matching only, always prefer document text): [{item_hints}]\n\n'
        'Return ONLY valid JSON:\n'
        '{"header":{"inv":"invoice number","company":"company name","date":"date"},'
        '"rows":[{"no":"","desc":"","qty":0,"unit":"","price":0,"total":0}]}'
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

    return process(raw, db_labels=known, db=db)
