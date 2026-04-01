import base64
import json
import io
import os
import httpx
from PIL import Image, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session
from backend.models.label import Label


# ═══════════════════════════════════════════════════════════
#  IMAGE PREPROCESSING — make text crystal clear for AI
# ═══════════════════════════════════════════════════════════

def preprocess_image(file_bytes: bytes) -> tuple[str, str]:
    """
    Clean up phone photos for maximum OCR accuracy.
    Returns (base64_string, mime_type).
    """
    img = Image.open(io.BytesIO(file_bytes))

    # Convert to RGB if needed
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize large images (phone photos are 4000x3000+)
    # Keep readable but reduce noise — 1600px wide is optimal for OCR
    max_width = 1600
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    # Sharpen — makes text edges crisp
    img = img.filter(ImageFilter.SHARPEN)

    # Boost contrast — makes text pop against background
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # Slight brightness boost for washed-out photos
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)

    # Save as high-quality JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    return b64, "image/jpeg"


# ═══════════════════════════════════════════════════════════
#  OCR PROMPT — simple, clear instructions
# ═══════════════════════════════════════════════════════════

OCR_PROMPT = """Read this invoice image. Extract every line item from the table.

For EACH row, give me exactly:
- "no": item number (e.g. "FG-1516")
- "desc": full description text INCLUDING the flavor name (Lime, Lemon, Orange, Grapefruit, etc.)
- "qty": the quantity number (just digits)
- "unit": unit type (Case, Bottle, etc.)
- "price": unit price number
- "total": line total number

From the header:
- "inv": invoice/order number
- "company": company name
- "date": date

CRITICAL:
- Each table row is a DIFFERENT product — read each row independently
- Always include the flavor name in the description
- Read numbers carefully — double check each row's quantity

Return ONLY this JSON:
{"header": {"inv": "", "company": "", "date": ""}, "rows": [{"no": "", "desc": "", "qty": 0, "unit": "", "price": 0, "total": 0}]}"""


# ═══════════════════════════════════════════════════════════
#  PRODUCT MATCHING — deterministic Python, zero AI mistakes
# ═══════════════════════════════════════════════════════════

FG_CODES = {
    "fg-1516": "ARTE-LME-1L-BTL",
    "fg-1515": "ARTE-LMN-1L-BTL",
    "fg-1514": "ARTE-GRF-1L-BTL",
    "fg-1513": "ARTE-ORG-1L-BTL",
}

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


def match_product(desc: str, item_no: str, labels: list[dict]) -> str | None:
    desc_lower = desc.lower()
    item_no_lower = (item_no or "").lower().strip()

    # Strategy 1: FG code (bulletproof)
    if item_no_lower in FG_CODES:
        return FG_CODES[item_no_lower]

    # Strategy 2: Multi-keyword match
    best_match = None
    best_score = 0
    for keywords, code in PRODUCT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score == len(keywords) and score > best_score:
            best_match = code
            best_score = score
    if best_match:
        return best_match

    # Strategy 3: Brand + single flavor
    if "arte" in desc_lower or "drink arte" in desc_lower:
        for flavor, code in [("lime", "ARTE-LME-1L-BTL"), ("lemon", "ARTE-LMN-1L-BTL"),
                              ("grapefruit", "ARTE-GRF-1L-BTL"), ("orange", "ARTE-ORG-1L-BTL")]:
            if flavor in desc_lower:
                return code

    # Strategy 4: DB fuzzy match
    for label in labels:
        if label["category"] != "juice":
            continue
        if label["flavor"].lower() in desc_lower and label["brand"].lower()[:4] in desc_lower:
            return label["item_code"]

    return None


def calc_bottles(qty: int, unit: str, case_size: int = 6) -> int:
    if "case" in unit.lower() or "cs" in unit.lower():
        return qty * case_size
    return qty


def get_case_size(item_code: str, labels: list[dict]) -> int:
    for label in labels:
        if label["item_code"] == item_code:
            return label.get("case_quantity", 6)
    return 6


def validate_qty(qty: int, price: float, total: float) -> int:
    if not price or price <= 0 or not total or total <= 0:
        return qty
    calculated = round(total / price)
    if abs(calculated - qty) <= 1:
        return qty
    return calculated


def process_ocr_result(raw: dict, labels: list[dict]) -> dict:
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

        qty = validate_qty(qty, price, total)
        matched_code = match_product(desc, item_no, labels)
        case_size = get_case_size(matched_code, labels) if matched_code else 6
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
        "supplier": header.get("company") or "",
        "invoice_date": header.get("date") or "",
    }


# ═══════════════════════════════════════════════════════════
#  DUAL-CALL CONSENSUS — call twice, pick the better result
# ═══════════════════════════════════════════════════════════

def pick_best_result(results: list[dict], labels: list[dict]) -> dict:
    """Pick the result with the most matched products and valid quantities."""
    best = None
    best_score = -1

    for raw in results:
        if not raw:
            continue
        processed = process_ocr_result(raw, labels)
        items = processed.get("items", [])
        # Score: matched items + items with valid qty
        score = sum(1 for i in items if i["matched_item_code"]) * 10
        score += sum(1 for i in items if i["quantity_bottles"] and i["quantity_bottles"] > 0) * 5
        score += len(items)  # More rows = read more carefully
        if score > best_score:
            best = processed
            best_score = score

    return best


# ═══════════════════════════════════════════════════════════
#  VISION API CALLS
# ═══════════════════════════════════════════════════════════

async def _call_gemini(b64: str, media_type: str) -> dict | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [
                    {"text": OCR_PROMPT},
                    {"inline_data": {"mime_type": media_type, "data": b64}},
                ]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2000},
            },
        )

    if resp.status_code != 200:
        return None

    try:
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
    except Exception:
        return None


async def _call_groq(b64: str, media_type: str) -> dict | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {"role": "system", "content": "OCR reader. Read each table row separately. Include flavor names. Output only JSON."},
                    {"role": "user", "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                    ]},
                ],
                "max_tokens": 2000,
                "temperature": 0.0,
            },
        )

    if resp.status_code != 200:
        return None

    try:
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
#  MAIN EXTRACTION — preprocess → dual call → consensus
# ═══════════════════════════════════════════════════════════

async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))

    if not has_gemini and not has_groq:
        raise ValueError("No vision API keys configured (need GEMINI_API_KEY or GROQ_API_KEY)")

    labels = [l.to_dict() for l in db.query(Label).all()]

    # Step 1: Preprocess image — sharpen, contrast, resize
    b64, media_type = preprocess_image(file_bytes)

    # Step 2: Call vision APIs (both if available, for consensus)
    results = []

    if has_gemini:
        # Call Gemini twice for consensus
        r1 = await _call_gemini(b64, media_type)
        results.append(r1)
        r2 = await _call_gemini(b64, media_type)
        results.append(r2)

    if has_groq and len([r for r in results if r]) < 2:
        r3 = await _call_groq(b64, media_type)
        results.append(r3)

    valid_results = [r for r in results if r and r.get("rows")]
    if not valid_results:
        raise ValueError("Could not read invoice. Try a clearer, well-lit photo with the invoice flat on a table.")

    # Step 3: Pick best result (most matches, valid quantities)
    return pick_best_result(valid_results, labels)
