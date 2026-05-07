"""
OCR a receipt image using Groq's vision model (free tier).

Extracts: amount, date, vendor, category, currency, description, confidence_note.
Returns a structured dict ready for inserting into the kvitteringer table.

Usage:
    from tools.ocr_receipt import extract_receipt_data
    data = extract_receipt_data("path/to/receipt.jpg", categories=["Transport", ...])
"""

import base64
import json
import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC support optional

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Groq free tier: 30 RPM = one every 2 seconds. Be slightly more conservative
# to absorb retry traffic and leave headroom for concurrent uploads.
_groq_lock = threading.Lock()
_last_call_time = 0.0
_MIN_INTERVAL = 2.5

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _throttle():
    """Ensure minimum interval between Groq API calls."""
    global _last_call_time
    with _groq_lock:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _last_call_time)
        if wait > 0:
            time.sleep(wait)
        _last_call_time = time.time()


def _resize_image(image_path: str, max_dim: int = 1568) -> tuple[str, str]:
    """Resize image to max dimension and return (base64_data, mime_type)."""
    img = Image.open(image_path)

    fmt = img.format or "JPEG"
    media_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }
    mime_type = media_map.get(fmt.upper(), "image/jpeg")

    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    if img.mode == "RGBA" and fmt.upper() == "JPEG":
        img = img.convert("RGB")

    # Always save as JPEG for compatibility — Llama Vision is most reliable
    # with widely-supported formats and gives smaller payloads.
    save_fmt = "JPEG" if fmt.upper() not in ("PNG", "WEBP", "GIF") else fmt.upper()
    if save_fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = BytesIO()
    if save_fmt == "JPEG":
        img.save(buf, format="JPEG", quality=85, optimize=True)
        mime_type = "image/jpeg"
    else:
        img.save(buf, format=save_fmt)

    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64, mime_type


def extract_receipt_data(image_path: str, categories: list[str] | None = None) -> dict:
    """
    Send a receipt image to Groq's vision model and extract structured data.

    Returns a dict with: amount, date, vendor, category, currency, description, confidence_note.
    """
    if categories is None:
        config_path = ROOT / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        categories = config.get("default_categories") or config.get("categories") or ["Andet"]

    category_list = ", ".join(categories)

    if Path(image_path).suffix.lower() == ".pdf":
        # Llama 4 Scout takes images, not PDFs. Reject with a clear signal —
        # /u/<token>/scan translates this into a friendly Danish message.
        raise ValueError(
            "PDF understøttes ikke endnu. Tag et foto af kvitteringen i stedet."
        )

    b64_data, mime_type = _resize_image(image_path)
    data_url = f"data:{mime_type};base64,{b64_data}"

    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY mangler i .env")

    prompt = (
        "Du er en kvitteringsscanner for en dansk forening. "
        "Udtræk følgende felter fra kvitteringsbilledet og returnér KUN gyldig JSON:\n\n"
        "{\n"
        '  "amount": <totalbeløb som tal, fx 149.95>,\n'
        '  "date": "<YYYY-MM-DD>",\n'
        '  "vendor": "<butik eller leverandør>",\n'
        f'  "category": "<vælg den bedst passende fra: {category_list}>",\n'
        '  "currency": "<DKK hvis ikke angivet>",\n'
        '  "description": "<2-5 ord, fx \'2x kaffe og croissant\', \'togbillet Aarhus-Kbh\'>",\n'
        '  "confidence_note": "<kort note på dansk hvis noget er utydeligt; ellers tom streng>"\n'
        "}\n\n"
        "Retunér KUN JSON-objektet. Ingen forklaring, ingen markdown."
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = None
    max_attempts = 5
    for attempt in range(max_attempts):
        _throttle()
        try:
            resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=60)
        except requests.exceptions.RequestException as e:
            if attempt < max_attempts - 1:
                wait = 2 ** attempt
                print(f"[OCR] network error, attempt {attempt+1}/{max_attempts}: {e}; retry in {wait}s")
                time.sleep(wait)
                continue
            raise

        if resp.status_code == 429:
            # Per-minute rate-limit — Groq's headers usually have retry-after
            retry_after = resp.headers.get("retry-after")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 30
            if attempt < max_attempts - 1:
                print(f"[OCR] 429 rate limit, attempt {attempt+1}/{max_attempts}, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        elif 500 <= resp.status_code < 600:
            if attempt < max_attempts - 1:
                wait = 2 ** attempt + 1
                print(f"[OCR] {resp.status_code} from Groq, attempt {attempt+1}/{max_attempts}, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        elif resp.status_code >= 400:
            resp.raise_for_status()
        else:
            break

    result = resp.json()

    # OpenAI-compatible response shape: choices[0].message.content
    try:
        raw = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        finish_reason = ""
        try:
            finish_reason = result["choices"][0].get("finish_reason", "")
        except (KeyError, IndexError):
            pass
        return {
            "amount": None,
            "date": None,
            "vendor": None,
            "category": "Andet",
            "currency": "DKK",
            "confidence_note": f"OCR returnerede intet svar (årsag: {finish_reason or 'ukendt'})",
            "description": "",
        }

    # Strip markdown code fences if the model accidentally wrapped the JSON
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "amount": None,
            "date": None,
            "vendor": None,
            "category": "Andet",
            "currency": "DKK",
            "confidence_note": f"Kunne ikke parse OCR-svar: {raw[:200]}",
            "description": "",
        }

    defaults = {
        "amount": None,
        "date": None,
        "vendor": None,
        "category": "Andet",
        "currency": "DKK",
        "confidence_note": "",
        "description": "",
    }
    for key, default in defaults.items():
        data.setdefault(key, default)

    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_receipt.py <image_path>")
        sys.exit(1)
    result = extract_receipt_data(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
