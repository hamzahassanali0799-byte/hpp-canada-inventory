import base64
import json
import os
import httpx
from sqlalchemy.orm import Session
from backend.models.label import Label


def get_extraction_prompt(labels: list[dict]) -> str:
    label_list = "\n".join(
        f"- {l['item_code']}: {l['label_name']} ({l['flavor']}, {l['size']}, case qty {l.get('case_quantity', 6)})"
        for l in labels
    )
    return f"""You are a precise invoice data extractor. Read the invoice image VERY carefully.

CRITICAL RULES:
1. Read EACH line item row separately — do NOT mix up quantities between rows
2. For each row, read the description, then the quantity number right next to it
3. If the quantity says "Cases" or "Case of 06", multiply the number by 6 to get bottles
4. Double-check: the quantity you read belongs to THAT row's product, not another row
5. Return ONLY valid JSON — no markdown, no explanation, no code fences

Known products in our inventory:
{label_list}

For EACH line item in the invoice, extract in order from top to bottom:
{{
  "items": [
    {{
      "description": "exact text from the invoice line",
      "quantity_bottles": <number of cases * 6 if cases, or raw number if bottles>,
      "quantity_cases": <number of cases as shown on invoice, or null>,
      "unit_price": <price per unit from invoice, or null>,
      "matched_item_code": "<match to item_code from list above, or null>"
    }}
  ],
  "invoice_number": "<from invoice header>",
  "supplier": "<from invoice header>",
  "invoice_date": "<from invoice header>"
}}

MATCHING RULES:
- "Drink Arte, Lime" or "Arte Lime" → ARTE-LME-1L-BTL
- "Drink Arte, Lemon" or "Arte Lemon" → ARTE-LMN-1L-BTL
- "Drink Arte, Orange" or "Arte Orange" → ARTE-ORG-1L-BTL
- "Drink Arte, Grapefruit" or "Arte Grapefruit" → ARTE-GRF-1L-BTL
- "Quirkies" products → QRKS-xxx codes
- "Joosy" products → JOOS-xxx codes

OUTPUT ONLY THE JSON. Nothing else."""


async def extract_invoice(file_bytes: bytes, content_type: str, db: Session) -> dict:
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not set — add it to your .env file")

    labels = [l.to_dict() for l in db.query(Label).all()]
    prompt = get_extraction_prompt(labels)

    b64 = base64.standard_b64encode(file_bytes).decode("utf-8")

    # Map content type for Groq vision — only these are supported
    supported_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    media_type = content_type if content_type in supported_types else "image/jpeg"

    # Use Groq API with Llama 4 Scout vision
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
                        "content": "You are a precise OCR data extractor. Read invoice images carefully and return only valid JSON. Never mix up quantities between line items. Read each row independently.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64}",
                                },
                            },
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
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI response as JSON: {e}\nRaw: {response_text[:500]}")
