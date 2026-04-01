import base64
import json
import os
import httpx
from sqlalchemy.orm import Session
from backend.models.label import Label


def get_extraction_prompt(labels: list[dict]) -> str:
    label_list = "\n".join(
        f"- {l['item_code']}: {l['label_name']} ({l['flavor']}, {l['size']})"
        for l in labels
    )
    return f"""You are an invoice data extractor for an HPP juice company.
Extract all line items from this delivery invoice image/document.

Known product labels in inventory:
{label_list}

Return ONLY valid JSON (no markdown, no code fences) with this structure:
{{
  "items": [
    {{
      "description": "product description from invoice",
      "quantity_bottles": <integer>,
      "quantity_cases": <integer or null>,
      "unit_price": <float or null>,
      "matched_item_code": "<best matching item_code from the list above, or null if no match>"
    }}
  ],
  "invoice_number": "<string or null>",
  "supplier": "<string or null>",
  "invoice_date": "<string or null>"
}}

Match products to known labels by fuzzy name matching (e.g. "Orange Juice 1L" → "ARTE-ORG-1L").
If quantity is in cases, multiply by 6 for quantity_bottles.
If you can't determine a field, use null."""


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
                "temperature": 0.1,
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
