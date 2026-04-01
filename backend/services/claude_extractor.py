import base64
import json
import os
import httpx
from sqlalchemy.orm import Session
from backend.models.label import Label


# ── Step 1: Simple OCR prompt — LLM only reads raw numbers ──

OCR_PROMPT = """Look at this invoice image. Read EACH line item row one by one, from top to bottom.

For EACH row in the table, tell me exactly:
- "no": item number column (e.g. "FG-1516")
- "desc": full description text (copy it exactly, include the flavor/product name)
- "qty": the quantity NUMBER (just the digits, e.g. 83)
- "unit": what unit (e.g. "Case of 06", "Case", "Bottle")
- "price": unit price number
- "total": line amount number

Also read the invoice header:
- "inv": invoice/order number
- "to": who is it addressed to / customer
- "from": supplier company
- "date": the date

IMPORTANT:
- Each row is a SEPARATE product. Read the flavor name for each (Lime, Lemon, Orange, Grapefruit, etc.)
- Do NOT combine or merge rows
- The quantity on each row belongs ONLY to that row's product

Return ONLY valid JSON:
{"header": {"inv": "", "to": "", "from": "", "date": ""}, "rows": [{"no": "", "desc": "", "qty": 0, "unit": "", "price": 0, "total": 0}]}"""


# ── Step 2: Deterministic Python matching ──

PRODUCT_KEYWORDS = {
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

# FG code → item_code (from your invoices)
FG_CODES = {
    "fg-1516": "ARTE-LME-1L-BTL",   # Lime
    "fg-1515": "ARTE-LMN-1L-BTL",   # Lemon
    "fg-1514": "ARTE-GRF-1L-BTL",   # Grapefruit
    "fg-1513": "ARTE-ORG-1L-BTL",   # Orange
}


def match_product(desc: str, item_no: str, labels: list[dict]) -> str | None:
    """Match using multiple strategies — most reliable first."""
    desc_lower = desc.lower()
    item_no_lower = (item_no or "").lower().strip()

    # Strategy 1: FG code mapping (most reliable — unique per product)
    if item_no_lower in FG_CODES:
        return FG_CODES[item_no_lower]

    # Strategy 2: Keyword matching on description
    best_match = None
    best_score = 0
    for keywords, code in PRODUCT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score == len(keywords) and score > best_score:
            best_match = code
            best_score = score

    if best_match:
        return best_match

    # Strategy 3: Single flavor keyword (if brand is in desc)
    flavors = {
        "lime": "ARTE-LME-1L-BTL",
        "lemon": "ARTE-LMN-1L-BTL",
        "grapefruit": "ARTE-GRF-1L-BTL",
        "orange": "ARTE-ORG-1L-BTL",
        "blueberry": None,
        "sunshine": None,
        "tropical": None,
        "mandarin": None,
        "apple": None,
    }
    if "arte" in desc_lower or "drink arte" in desc_lower:
        for flavor, code in flavors.items():
            if code and flavor in desc_lower:
                return code

    # Strategy 4: Fuzzy match against DB labels
    for label in labels:
        if label["category"] != "juice":
            continue
        flavor_lower = label["flavor"].lower()
        brand_lower = label["brand"].lower()
        if flavor_lower in desc_lower and (brand_lower in desc_lower or brand_lower[:4] in desc_lower):
            return label["item_code"]

    return None


def calc_bottles(qty: int, unit: str, case_size: int = 6) -> int:
    """Convert to bottles."""
    unit_lower = unit.lower()
    if "case" in unit_lower or "cs" in unit_lower or "crate" in unit_lower:
        return qty * case_size
    return qty


def get_case_size(item_code: str, labels: list[dict]) -> int:
    """Get case quantity for a matched product."""
    for label in labels:
        if label["item_code"] == item_code:
            return label.get("case_quantity", 6)
    return 6


def validate_qty(qty: int, price: float, total: float) -> int:
    """Cross-check quantity using total / price."""
    if not price or price <= 0 or not total or total <= 0:
        return qty
    calculated = round(total / price)
    if abs(calculated - qty) <= 1:
        return qty
    # Math disagrees — trust math
    return calculated


def process_ocr_result(raw: dict, labels: list[dict]) -> dict:
    """Deterministic processing — no AI, pure code."""
    header = raw.get("header", {})
    rows = raw.get("rows", [])
    items = []

    for row in rows:
        desc = str(row.get("desc", ""))
        item_no = str(row.get("no", ""))
        qty = int(row.get("qty", 0) or 0)
        unit = str(row.get("unit", ""))
        price = float(row.get("price", 0) or 0)
        total = float(row.get("total", 0) or 0)

        # Validate quantity with math
        qty = validate_qty(qty, price, total)

        # Match product
        matched_code = match_product(desc, item_no, labels)

        # Get case size
        case_size = get_case_size(matched_code, labels) if matched_code else 6

        # Convert to bottles
        bottles = calc_bottles(qty, unit, case_size)

        items.append({
            "description": f"{desc} [{item_no}]" if item_no else desc,
            "quantity_bottles": bottles,
            "quantity_cases": qty if "case" in unit.lower() else None,
            "unit_price": price if price > 0 else None,
            "matched_item_code": matched_code,
        })

    return {
        "items": items,
        "invoice_number": header.get("inv") or "",
        "supplier": header.get("from") or header.get("to") or "",
        "invoice_date": header.get("date") or "",
    }


# ── Main ──

async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not set — add it to your .env file")

    labels = [l.to_dict() for l in db.query(Label).all()]
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    supported_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    media_type = content_type if content_type in supported_types else "image/jpeg"

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an OCR reader. Read text from invoice images exactly as written. Each table row is a separate product — never combine rows. Output only JSON.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": OCR_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                        ],
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.0,
            },
        )

    if resp.status_code != 200:
        error_detail = resp.text
        try:
            err_json = resp.json()
            error_detail = err_json.get("error", {}).get("message", error_detail)
        except Exception:
            pass
        raise ValueError(f"Vision API error ({resp.status_code}): {error_detail}")

    data = resp.json()
    response_text = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )

    try:
        raw_ocr = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse response: {e}\nRaw: {response_text[:500]}")

    return process_ocr_result(raw_ocr, labels)
