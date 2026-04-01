"""
Send receipt data + image to Google Sheets via Apps Script Web App.

Replaces both upload_to_drive.py and push_to_sheets.py with a single call.
The Apps Script handles Drive upload and Sheet append server-side.

Usage:
    from tools.send_to_sheets import send_receipt
    image_link = send_receipt(receipt_data, "Anders", image_b64, "kvittering.jpg", "Til lejr")
"""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

_FORMULA_CHARS = frozenset("=+−-@\t\r\n")


def _sanitize(value):
    """Prefix dangerous characters to prevent spreadsheet formula injection."""
    if isinstance(value, str) and value and value[0] in _FORMULA_CHARS:
        return "'" + value
    return value


def send_receipt(
    receipt_data: dict,
    submitter: str,
    image_base64: str,
    image_filename: str,
    comment: str = "",
    payment_type: str = "",
    phone: str = "",
    reg_nr: str = "",
    konto_nr: str = "",
    udvalg: str = "",
    apps_script_url: str | None = None,
) -> str:
    """
    POST receipt data and base64 image to the Apps Script Web App.

    Args:
        receipt_data: Dict from ocr_receipt.py with keys: amount, date, vendor, category, currency, confidence_note
        submitter: Name of the person who submitted.
        image_base64: Base64-encoded image data.
        image_filename: Filename for the Drive file (e.g., "kvittering_2026-03-24_anders.jpg").
        comment: Optional comment from the submitter.
        apps_script_url: Override URL (defaults to config.json).

    Returns:
        Shareable Google Drive link to the uploaded image.
    """
    if apps_script_url is None:
        with open(ROOT / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        apps_script_url = config.get("apps_script_url", "")

    if not apps_script_url:
        raise ValueError(
            "Apps Script URL mangler. Sæt 'apps_script_url' i config.json.\n"
            "Se workflows/process_receipt.md for opsætningsguide."
        )

    payload = {
        "name": _sanitize(submitter),
        "payment_type": payment_type,
        "udvalg": _sanitize(udvalg),
        "phone": _sanitize(phone),
        "reg_nr": _sanitize(reg_nr),
        "konto_nr": _sanitize(konto_nr),
        "amount": receipt_data.get("amount"),
        "date": receipt_data.get("date"),
        "vendor": _sanitize(receipt_data.get("vendor", "")),
        "category": receipt_data.get("category", "Andet"),
        "currency": receipt_data.get("currency", "DKK"),
        "comment": _sanitize(comment),
        "description": _sanitize(receipt_data.get("description", "")),
        "confidence_note": _sanitize(receipt_data.get("confidence_note", "")),
        "image_base64": image_base64,
        "image_filename": image_filename,
    }

    import time

    response = None
    for attempt in range(3):
        try:
            response = requests.post(
                apps_script_url,
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            break
        except (requests.RequestException, requests.HTTPError):
            if attempt < 2:
                time.sleep(2 * (attempt + 1))  # 2s, 4s
            else:
                raise

    result = response.json()

    if result.get("status") != "ok":
        error_msg = result.get("message", "Ukendt fejl fra Apps Script")
        raise RuntimeError(f"Apps Script fejl: {error_msg}")

    return result.get("image_link", "")


if __name__ == "__main__":
    import base64
    import sys

    if len(sys.argv) < 2:
        print("Usage: python send_to_sheets.py <image_path> [submitter] [comment]")
        sys.exit(1)

    image_path = sys.argv[1]
    submitter = sys.argv[2] if len(sys.argv) > 2 else "Test"
    comment = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    dummy_data = {
        "amount": 0,
        "date": "2026-01-01",
        "vendor": "Test",
        "category": "Andet",
        "currency": "DKK",
        "confidence_note": "",
    }

    link = send_receipt(dummy_data, submitter, b64, Path(image_path).name, comment)
    print(f"Uploaded: {link}")
