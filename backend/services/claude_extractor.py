import base64
import json
import os
import httpx
from sqlalchemy.orm import Session
from backend.models.label import Label


# ── OCR Prompt ──

OCR_PROMPT = """Read this invoice image carefully. Extract each line item row separately.

For EACH row in the table, give me:
- "no": item/product number (e.g. "FG-1516")
- "desc": full description including flavor name (e.g. "Packed product - Drink Arte, Lime, case qty6 of 1L")
- "qty": quantity number (just the digits)
- "unit": unit type (e.g. "Case of 06", "Case", "Bottle")
- "price": unit price
- "total": line amount total

From the header:
- "inv": invoice/order number
- "company": company name (supplier)
- "date": invoice date

RULES:
- Each row is a DIFFERENT product with its own flavor (Lime, Lemon, Grapefruit, Orange, etc.)
- Do NOT merge rows together
- Read the flavor name for each row carefully

Return ONLY valid JSON:
{"header": {"inv": "", "company": "", "date": ""}, "rows": [{"no": "", "desc": "", "qty": 0, "unit": "", "price": 0, "total": 0}]}"""


# ── Product Matching (deterministic Python) ──

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

    if item_no_lower in FG_CODES:
        return FG_CODES[item_no_lower]

    best_match = None
    best_score = 0
    for keywords, code in PRODUCT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score == len(keywords) and score > best_score:
            best_match = code
            best_score = score
    if best_match:
        return best_match

    if "arte" in desc_lower or "drink arte" in desc_lower:
        for flavor, code in [("lime", "ARTE-LME-1L-BTL"), ("lemon", "ARTE-LMN-1L-BTL"),
                              ("grapefruit", "ARTE-GRF-1L-BTL"), ("orange", "ARTE-ORG-1L-BTL")]:
            if flavor in desc_lower:
                return code

    for label in labels:
        if label["category"] != "juice":
            continue
        if label["flavor"].lower() in desc_lower and label["brand"].lower()[:4] in desc_lower:
            return label["item_code"]

    return None


def calc_bottles(qty: int, unit: str, case_size: int = 6) -> int:
    unit_lower = unit.lower()
    if "case" in unit_lower or "cs" in unit_lower:
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


# ── Vision API call — tries Gemini first, falls back to Groq ──

async def _call_gemini(b64: str, media_type: str) -> str:
    """Google Gemini Flash 2.0 — free, excellent OCR."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [
                        {"text": OCR_PROMPT},
                        {"inline_data": {"mime_type": media_type, "data": b64}},
                    ]
                }],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2000},
            },
        )

    if resp.status_code != 200:
        return None

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return None


async def _call_groq(b64: str, media_type: str) -> str:
    """Groq Llama 4 Scout — free fallback."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("No vision API keys configured (need GEMINI_API_KEY or GROQ_API_KEY)")

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {"role": "system", "content": "You are an OCR reader. Read invoice images exactly. Each row is a separate product. Output only JSON."},
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
        raise ValueError(f"Groq API error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    labels = [l.to_dict() for l in db.query(Label).all()]
    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    supported_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    media_type = content_type if content_type in supported_types else "image/jpeg"

    # Try Gemini first (better OCR), fall back to Groq
    response_text = await _call_gemini(b64, media_type)
    if not response_text:
        response_text = await _call_groq(b64, media_type)

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
