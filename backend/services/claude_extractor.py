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
    # Resize to 900px wide — smaller payload, still readable for AI
    if img.width > 900:
        ratio = 900 / img.width
        img = img.resize((900, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72)
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
    """Try to match against actual DB items."""
    d = desc.lower()
    n = (item_no or "").strip().upper()

    # Exact item code match
    for label in db_labels:
        if n and label.item_code.upper() == n:
            return label.item_code

    # Partial item code match (e.g. "FG-1516" in item_no)
    for label in db_labels:
        if n and n in label.item_code.upper():
            return label.item_code

    # Keyword match against label_name / flavor
    best = None
    best_score = 0
    for label in db_labels:
        words = label.label_name.lower().split()
        score = sum(1 for w in words if len(w) > 2 and w in d)
        if score > best_score and score >= 2:
            best = label.item_code
            best_score = score

    return best


def process(raw: dict, db_labels=None) -> dict:
    header = raw.get("header", {})
    items = []
    missing_info = []

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

        # Try hardcoded match first, then DB match
        matched = match_product(desc, no)
        if not matched and db_labels:
            matched = match_product_db(desc, no, db_labels)

        case_size = 6
        bottles = qty * case_size if "case" in unit.lower() else qty

        # Track what's missing
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
        'Extract all items from this invoice/packing slip/delivery note. '
        'For each line: no=item code (e.g. FG-1516), desc=product name with flavor/size/brand, '
        'qty=quantity (0 if unclear), unit=Case/Bottle/Each/KG/L, price=unit price, total=line total. '
        f'Known items: [{item_hints}]. Use exact codes when matched. '
        'Return ONLY JSON: {"header":{"inv":"","company":"","date":""},"rows":[{"no":"","desc":"","qty":0,"unit":"","price":0,"total":0}]}'
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
                        "max_tokens": 1024,
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

    return process(raw, db_labels=known)
