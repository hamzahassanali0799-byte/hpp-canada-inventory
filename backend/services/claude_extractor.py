import base64
import json
import os
import re
import httpx
from sqlalchemy.orm import Session
from backend.models.label import Label


# ── Step 1: Simple OCR prompt — LLM only reads text, no math ──

OCR_PROMPT = """Read this invoice image. Extract EACH line item row exactly as written.

For each row, give me:
- "no": the item number (e.g. "FG-1516")
- "desc": the product description text exactly as written
- "qty_num": the NUMBER shown in the quantity column (just the number, e.g. 83)
- "qty_unit": the unit shown (e.g. "Case", "Bottle", "EA", "Case of 06")
- "unit_price": the unit price number
- "line_total": the line amount/total number

Also extract from the header:
- "invoice_no": order/invoice number
- "supplier": supplier/company name
- "date": the date

CRITICAL: Read each row's quantity INDEPENDENTLY. The quantity number belongs to the row it appears in.
Go row by row, top to bottom.

Return ONLY this JSON (no markdown, no explanation):
{
  "header": {"invoice_no": "...", "supplier": "...", "date": "..."},
  "rows": [
    {"no": "...", "desc": "...", "qty_num": 83, "qty_unit": "Case", "unit_price": 36.56, "line_total": 3034.48},
    ...
  ]
}"""


# ── Step 2: Python matching — deterministic, zero mistakes ──

# Keyword → item_code mapping
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


def match_product(desc: str, labels: list[dict]) -> str | None:
    """Match a description to an item_code using keywords."""
    desc_lower = desc.lower()

    # Try keyword matching first (most reliable)
    best_match = None
    best_score = 0
    for keywords, code in PRODUCT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score == len(keywords) and score > best_score:
            best_match = code
            best_score = score
        elif score > 0 and score == len(keywords):
            best_match = code

    if best_match:
        return best_match

    # Fallback: fuzzy match against label names
    for label in labels:
        name_lower = label["label_name"].lower()
        flavor_lower = label["flavor"].lower()
        if flavor_lower in desc_lower and label["category"] == "juice":
            # Check brand
            brand_lower = label["brand"].lower()
            if brand_lower in desc_lower or brand_lower[:4] in desc_lower:
                return label["item_code"]

    return None


def calc_bottles(qty_num: int, qty_unit: str, case_size: int = 6) -> int:
    """Convert quantity to bottles. Cases get multiplied, bottles stay as-is."""
    unit = qty_unit.lower().strip()
    if "case" in unit or "cs" in unit or "crate" in unit:
        return qty_num * case_size
    return qty_num


def get_case_size(item_code: str, labels: list[dict]) -> int:
    """Get case quantity for a matched product."""
    for label in labels:
        if label["item_code"] == item_code:
            return label.get("case_quantity", 6)
    return 6


def validate_with_line_total(qty_num: int, unit_price: float, line_total: float) -> int | None:
    """Cross-check quantity using line_total / unit_price."""
    if not unit_price or unit_price <= 0 or not line_total or line_total <= 0:
        return None
    calculated = round(line_total / unit_price)
    # If the calculated qty is close to qty_num, trust it
    if abs(calculated - qty_num) <= 1:
        return qty_num
    # If they disagree, trust the math (line_total / unit_price)
    return calculated


def process_ocr_result(raw: dict, labels: list[dict]) -> dict:
    """Step 2: Take raw OCR data and apply deterministic matching + math."""
    header = raw.get("header", {})
    rows = raw.get("rows", [])
    items = []

    for row in rows:
        desc = row.get("desc", "")
        qty_num = int(row.get("qty_num", 0) or 0)
        qty_unit = row.get("qty_unit", "")
        unit_price = float(row.get("unit_price", 0) or 0)
        line_total = float(row.get("line_total", 0) or 0)

        # Cross-validate quantity with line math
        validated_qty = validate_with_line_total(qty_num, unit_price, line_total)
        if validated_qty is not None:
            qty_num = validated_qty

        # Match to product
        matched_code = match_product(desc, labels)

        # Get case size for this product
        case_size = get_case_size(matched_code, labels) if matched_code else 6

        # Convert to bottles
        bottles = calc_bottles(qty_num, qty_unit, case_size)

        items.append({
            "description": desc,
            "quantity_bottles": bottles,
            "quantity_cases": qty_num if "case" in qty_unit.lower() else None,
            "unit_price": unit_price if unit_price > 0 else None,
            "matched_item_code": matched_code,
        })

    return {
        "items": items,
        "invoice_number": header.get("invoice_no"),
        "supplier": header.get("supplier"),
        "invoice_date": header.get("date"),
    }


# ── Main extraction function ──

async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not set — add it to your .env file")

    labels = [l.to_dict() for l in db.query(Label).all()]

    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    supported_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    media_type = content_type if content_type in supported_types else "image/jpeg"

    # Step 1: LLM does OCR only — reads raw text from each row
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
                        "content": "You are a precise OCR reader. Read invoice images and extract raw text data into JSON. Do NOT do any math or calculations. Just read what is written.",
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

    # Strip markdown fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )

    try:
        raw_ocr = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OCR response as JSON: {e}\nRaw: {response_text[:500]}")

    # Step 2: Python does all math + matching (deterministic, no mistakes)
    return process_ocr_result(raw_ocr, labels)
