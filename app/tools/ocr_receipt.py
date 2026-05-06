"""
OCR a receipt image using Google Gemini Flash (free tier).

Extracts: amount, date, vendor, category, currency.
Returns structured dict ready for Google Sheets.

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

# --- Gemini rate-limit throttle (free tier ≈ 15 RPM) ---
_gemini_lock = threading.Lock()
_last_call_time = 0.0
_MIN_INTERVAL = 6.0  # seconds between Gemini API calls


def _throttle():
    """Ensure minimum interval between Gemini API calls."""
    global _last_call_time
    with _gemini_lock:
        now = time.time()
        wait = _MIN_INTERVAL - (now - _last_call_time)
        if wait > 0:
            time.sleep(wait)
        _last_call_time = time.time()
from dotenv import load_dotenv
from PIL import Image

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # HEIC support optional

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _resize_image(image_path: str, max_dim: int = 1568) -> tuple[str, str]:
    """Resize image to max dimension and return (base64_data, mime_type)."""
    img = Image.open(image_path)

    fmt = img.format or "JPEG"
    media_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}
    mime_type = media_map.get(fmt.upper(), "image/jpeg")

    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    if img.mode == "RGBA" and fmt.upper() == "JPEG":
        img = img.convert("RGB")

    buf = BytesIO()
    save_fmt = fmt.upper() if fmt.upper() in ("JPEG", "PNG", "WEBP", "GIF") else "JPEG"
    img.save(buf, format=save_fmt, quality=85)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64, mime_type


def _read_pdf(file_path: str) -> tuple[str, str]:
    """Read a PDF file and return (base64_data, mime_type)."""
    with open(file_path, "rb") as f:
        b64 = base64.standard_b64encode(f.read()).decode("utf-8")
    return b64, "application/pdf"


def extract_receipt_data(image_path: str, categories: list[str] | None = None) -> dict:
    """
    Send receipt image or PDF to Gemini Flash and extract structured data.

    Returns:
        dict with keys: amount, date, vendor, category, currency, confidence_note
    """
    if categories is None:
        config_path = ROOT / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        categories = config.get("categories", ["Andet"])

    category_list = ", ".join(categories)

    # PDF files go directly to Gemini; images get resized first
    if Path(image_path).suffix.lower() == ".pdf":
        b64_data, mime_type = _read_pdf(image_path)
    else:
        b64_data, mime_type = _resize_image(image_path)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY mangler i .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data,
                        }
                    },
                    {
                        "text": (
                            "Du er en kvitteringsscanner for en dansk forening. "
                            "Udtræk følgende fra kvitteringsbilledet:\n\n"
                            "1. **amount**: Totalbeløb som tal (kun tallet, fx 149.95)\n"
                            "2. **date**: Dato i YYYY-MM-DD format\n"
                            "3. **vendor**: Butik eller leverandør\n"
                            "4. **category**: Vælg den bedst passende fra denne liste: "
                            f"{category_list}\n"
                            "5. **currency**: Valuta (DKK hvis ikke angivet)\n"
                            "6. **confidence_note**: Hvis noget er utydeligt eller usikkert, "
                            "beskriv det kort på dansk. Ellers tom streng.\n"
                            "7. **description**: Kort beskrivelse af hvad der er købt (2-5 ord, fx "
                            "'2x kaffe og croissant', 'togbillet Aarhus-Kbh')\n\n"
                            "Svar KUN med valid JSON. Ingen anden tekst."
                        ),
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    resp = None
    max_attempts = 5
    for attempt in range(max_attempts):
        _throttle()
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except requests.exceptions.RequestException as e:
            # Network error / connection reset — retry with backoff
            if attempt < max_attempts - 1:
                wait = 2 ** attempt  # 1, 2, 4, 8 s
                print(f"[OCR] network error, attempt {attempt+1}/{max_attempts}: {e}; retry in {wait}s")
                time.sleep(wait)
                continue
            raise

        if resp.status_code == 429:
            # Free tier per-minute rate-limit — wait full minute
            if attempt < max_attempts - 1:
                wait = 60
                print(f"[OCR] 429 rate limit, attempt {attempt+1}/{max_attempts}, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        elif 500 <= resp.status_code < 600:
            # Transient server-side outage (503 Service Unavailable, 502, etc.)
            # Gemini hiccups during peak — back off and retry
            if attempt < max_attempts - 1:
                wait = 2 ** attempt + 1  # 2, 3, 5, 9 s
                print(f"[OCR] {resp.status_code} from Gemini, attempt {attempt+1}/{max_attempts}, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        elif resp.status_code >= 400:
            resp.raise_for_status()
        else:
            break

    result = resp.json()

    # Safe extraction — Gemini may return empty candidates (safety filter, overload)
    try:
        raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        block_reason = result.get("promptFeedback", {}).get("blockReason", "unknown")
        return {
            "amount": None,
            "date": None,
            "vendor": None,
            "category": "Andet",
            "currency": "DKK",
            "confidence_note": f"Gemini returnerede intet svar (årsag: {block_reason})",
            "description": "",
        }

    # Strip markdown code fences if present
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
