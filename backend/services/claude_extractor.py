import base64
import json
import io
import os
import re
import httpx
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session
from backend.models.label import Label


# ═══════════════════════════════════════════════════════════
#  IMAGE PREPROCESSING
# ═══════════════════════════════════════════════════════════

def preprocess_image(file_bytes: bytes) -> Image.Image:
    """Clean up phone photo for OCR."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize to optimal OCR size
    max_width = 2000
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    # Sharpen + contrast for crisp text
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)  # double sharpen
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Brightness(img).enhance(1.1)

    return img


def image_to_b64(img: Image.Image) -> tuple[str, str]:
    """Convert PIL image to base64 JPEG."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8"), "image/jpeg"


# ═══════════════════════════════════════════════════════════
#  TESSERACT OCR — reads text perfectly, no hallucinations
# ═══════════════════════════════════════════════════════════

def tesseract_extract(img: Image.Image) -> str:
    """Run Tesseract OCR on preprocessed image."""
    try:
        text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
        return text
    except Exception:
        return ""


def parse_invoice_text(text: str) -> dict:
    """Parse raw OCR text into structured invoice data using regex."""
    lines = text.split("\n")
    header = {"inv": "", "company": "", "date": ""}
    rows = []

    # Find invoice/order number
    for line in lines:
        # Match "S-ORD101007" or "ORD-12345" patterns
        m = re.search(r'(S-ORD\d+|ORD[- ]?\d+|INV[- ]?\d+|PO[- ]?\d+[/\w]*)', line, re.IGNORECASE)
        if m and not header["inv"]:
            header["inv"] = m.group(1)

        # Match date patterns
        m = re.search(r'(\w+ \d{1,2},?\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line)
        if m and not header["date"]:
            header["date"] = m.group(1)

        # Company name
        if "hpp" in line.lower() and "canada" in line.lower():
            header["company"] = "HPP Canada"
        elif "drink arte" in line.lower():
            header["company"] = header["company"] or "Drink Arte"

    # Parse table rows — look for FG-xxxx patterns or lines with numbers
    # Pattern: FG-1516  Packed product - Drink Arte, Lime, case qty6 of 1L  83  Case of 06  36.56  0  3,034.48
    fg_pattern = re.compile(
        r'(FG[- ]?\d{3,5})\s+'           # Item number
        r'(.+?)\s+'                        # Description
        r'(\d{1,4})\s+'                    # Quantity
        r'(Case[^0-9]*\d*|Bottle|EA)\s+'   # Unit
        r'(\d+[.,]\d{2})\s+'              # Unit price
        r'\d+\s+'                          # Tax %
        r'([\d,]+[.,]\d{2})',             # Line total
        re.IGNORECASE
    )

    for line in lines:
        m = fg_pattern.search(line)
        if m:
            rows.append({
                "no": m.group(1).strip(),
                "desc": m.group(2).strip(),
                "qty": int(m.group(3)),
                "unit": m.group(4).strip(),
                "price": float(m.group(5).replace(",", "")),
                "total": float(m.group(6).replace(",", "")),
            })

    # If regex didn't find rows, try a simpler pattern
    if not rows:
        # Look for lines with FG codes
        for line in lines:
            fg_match = re.search(r'(FG[- ]?\d{3,5})', line, re.IGNORECASE)
            if not fg_match:
                continue

            # Extract numbers from the line
            numbers = re.findall(r'(\d+[.,]?\d*)', line)
            desc_parts = re.split(r'\d', line, 1)
            desc = desc_parts[0].strip() if desc_parts else line

            # Try to identify flavor
            flavor = ""
            for f in ["Lime", "Lemon", "Grapefruit", "Orange", "Blueberry", "Sunshine", "Apple", "Tropical", "Mandarin"]:
                if f.lower() in line.lower():
                    flavor = f
                    break

            if numbers and len(numbers) >= 2:
                qty = int(float(numbers[0].replace(",", "")))
                # Find the price (number with decimals)
                price = 0
                total = 0
                for n in numbers[1:]:
                    val = float(n.replace(",", ""))
                    if 10 < val < 200:
                        price = val
                    elif val > 200:
                        total = val

                rows.append({
                    "no": fg_match.group(1),
                    "desc": f"{desc} {flavor}".strip(),
                    "qty": qty,
                    "unit": "Case" if "case" in line.lower() else "Bottle",
                    "price": price,
                    "total": total,
                })

    return {"header": header, "rows": rows}


# ═══════════════════════════════════════════════════════════
#  PRODUCT MATCHING — deterministic, zero mistakes
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
    item_no_lower = (item_no or "").lower().strip().replace(" ", "-")

    # Normalize FG code format
    fg_match = re.search(r'fg[- ]?(\d+)', item_no_lower)
    if fg_match:
        normalized = f"fg-{fg_match.group(1)}"
        if normalized in FG_CODES:
            return FG_CODES[normalized]

    # Keyword match
    best_match = None
    best_score = 0
    for keywords, code in PRODUCT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score == len(keywords) and score > best_score:
            best_match = code
            best_score = score
    if best_match:
        return best_match

    # Brand + flavor
    if "arte" in desc_lower or "drink" in desc_lower:
        for flavor, code in [("lime", "ARTE-LME-1L-BTL"), ("lemon", "ARTE-LMN-1L-BTL"),
                              ("grapefruit", "ARTE-GRF-1L-BTL"), ("orange", "ARTE-ORG-1L-BTL")]:
            if flavor in desc_lower:
                return code

    # DB fuzzy
    for label in labels:
        if label["category"] != "juice":
            continue
        if label["flavor"].lower() in desc_lower:
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
#  AI FALLBACK (only if Tesseract can't parse the table)
# ═══════════════════════════════════════════════════════════

AI_PROMPT = """Read this invoice. For each table row give me:
{"header":{"inv":"","company":"","date":""},"rows":[{"no":"FG-xxxx","desc":"full description with flavor","qty":83,"unit":"Case","price":36.56,"total":3034.48}]}
Return ONLY JSON."""


async def _call_gemini(b64: str, media_type: str) -> dict | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                json={"contents": [{"parts": [
                    {"text": AI_PROMPT},
                    {"inline_data": {"mime_type": media_type, "data": b64}},
                ]}], "generationConfig": {"temperature": 0.0, "maxOutputTokens": 2000}},
            )
        if resp.status_code != 200:
            return None
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
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [
                        {"role": "system", "content": "OCR. Read each row. Include flavor. JSON only."},
                        {"role": "user", "content": [
                            {"type": "text", "text": AI_PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
                        ]},
                    ],
                    "max_tokens": 2000, "temperature": 0.0,
                },
            )
        if resp.status_code != 200:
            return None
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
#  MAIN — Tesseract first, AI fallback
# ═══════════════════════════════════════════════════════════

async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    labels = [l.to_dict() for l in db.query(Label).all()]

    # Step 1: Preprocess image
    img = preprocess_image(file_bytes)

    # Step 2: Try Tesseract OCR + regex parsing (most reliable)
    raw_text = tesseract_extract(img)
    if raw_text and len(raw_text.strip()) > 50:
        parsed = parse_invoice_text(raw_text)
        if parsed["rows"]:
            result = process_ocr_result(parsed, labels)
            if result["items"]:
                return result

    # Step 3: Tesseract failed to parse table — try AI
    b64, media_type = image_to_b64(img)

    # Try Gemini
    ai_result = await _call_gemini(b64, media_type)
    if ai_result and ai_result.get("rows"):
        return process_ocr_result(ai_result, labels)

    # Try Groq
    ai_result = await _call_groq(b64, media_type)
    if ai_result and ai_result.get("rows"):
        return process_ocr_result(ai_result, labels)

    raise ValueError("Could not read invoice. Tips: lay invoice flat, good lighting, hold camera steady.")
