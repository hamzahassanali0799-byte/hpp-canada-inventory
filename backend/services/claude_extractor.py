import base64
import json
import io
import logging
import os
import re
import httpx
from PIL import Image
from sqlalchemy.orm import Session
from backend.models.label import Label

logger = logging.getLogger(__name__)


def compress_image(file_bytes: bytes) -> tuple[str, str]:
    """Resize phone photo to reduce upload size. No over-processing."""
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    # Resize to 1200px wide — fast upload, still readable
    if img.width > 1200:
        ratio = 1200 / img.width
        img = img.resize((1200, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
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


def process(raw: dict) -> dict:
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

        matched = match_product(desc, no)
        case_size = 6
        bottles = qty * case_size if "case" in unit.lower() else qty

        items.append({
            "description": f"{desc} [{no}]" if no else desc,
            "quantity_bottles": bottles,
            "quantity_cases": qty if "case" in unit.lower() else None,
            "unit_price": price if price > 0 else None,
            "matched_item_code": matched,
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

    prompt = (
        'Read this invoice table. For each row give: no (item number like FG-1516), '
        'desc (full text with flavor name like Lime/Lemon/Grapefruit/Orange), '
        'qty (quantity number), unit (Case/Bottle), price (unit price), total (line total). '
        'Return JSON: {"header":{"inv":"","company":"","date":""},"rows":[{"no":"","desc":"","qty":0,"unit":"","price":0,"total":0}]}'
    )

    raw = None
    errors = []

    # Try Claude Haiku first (primary)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        logger.info("Attempting extraction with Claude Haiku")
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
                logger.info("Claude Haiku extraction succeeded")
            else:
                msg = f"Claude HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(msg)
                errors.append(msg)
        except Exception as e:
            msg = f"Claude error: {e}"
            logger.warning(msg)
            errors.append(msg)
    else:
        logger.info("ANTHROPIC_API_KEY not set — skipping Claude, trying Gemini")

    # Fallback to Gemini Flash
    if not raw and gemini_key:
        logger.info("Attempting extraction with Gemini Flash")
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
                logger.info("Gemini Flash extraction succeeded")
            else:
                msg = f"Gemini HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(msg)
                errors.append(msg)
        except Exception as e:
            msg = f"Gemini error: {e}"
            logger.warning(msg)
            errors.append(msg)
    elif not raw and not gemini_key:
        logger.warning("GEMINI_API_KEY not set — no fallback available")

    if not raw or not raw.get("rows"):
        detail = "; ".join(errors) if errors else "no extractors succeeded"
        logger.error("Invoice extraction failed: %s", detail)
        raise ValueError("Could not read invoice. Lay it flat, good light, hold steady.")

    return process(raw)
