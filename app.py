"""
Flask app for automatic receipt processing.

GET  /        — Serves the upload form
POST /scan    — Receives receipt images, runs OCR, streams NDJSON results for review
POST /confirm — Receives reviewed data, sends to Google Sheets via Apps Script
"""

import base64
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path

import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

TMP_DIR = ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)


def load_config():
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def validate_ocr_result(receipt_data: dict) -> dict:
    """Flag missing or invalid OCR fields via confidence_note (never reject)."""
    warnings = []
    amount = receipt_data.get("amount")
    if amount is None:
        warnings.append("Beløb ikke genkendt")
    else:
        try:
            float(amount)
        except (ValueError, TypeError):
            warnings.append("Beløb ikke genkendt")

    date = receipt_data.get("date")
    if not date or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        warnings.append("Dato ikke genkendt")

    if not receipt_data.get("vendor"):
        warnings.append("Butik ikke genkendt")

    if warnings:
        existing = receipt_data.get("confidence_note", "")
        sep = "; " if existing else ""
        receipt_data["confidence_note"] = existing + sep + "; ".join(warnings)

    return receipt_data


def _cleanup_old_temp_files(max_age_seconds=3600):
    """Remove temp files older than max_age_seconds."""
    now = time.time()
    for f in TMP_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            try:
                if now - f.stat().st_mtime > max_age_seconds:
                    f.unlink()
            except OSError:
                pass


@app.route("/")
def index():
    config = load_config()
    return render_template(
        "form.html",
        forening_name=config.get("forening_name", "Forening"),
        categories_json=json.dumps(config.get("categories", ["Andet"])),
        udvalg_json=json.dumps(config.get("udvalg", [])),
    )


@app.route("/scan", methods=["POST"])
def scan():
    """OCR receipt images and stream NDJSON results. Temp files kept for /confirm."""
    name = request.form.get("name", "").strip()
    files = request.files.getlist("receipt")

    if not name:
        return jsonify({"error": "Vælg venligst dit navn."}), 400
    if not files:
        return jsonify({"error": "Vedhæft venligst mindst én kvittering."}), 400

    _cleanup_old_temp_files()

    saved = []
    for file in files:
        ext = Path(file.filename).suffix.lower() or ".jpg"
        temp_id = f"{uuid.uuid4().hex}{ext}"
        temp_path = TMP_DIR / temp_id
        file.save(str(temp_path))
        saved.append((temp_path, temp_id, file.filename, ext))

    def generate():
        from tools.ocr_receipt import extract_receipt_data

        for i, (temp_path, temp_id, original_name, ext) in enumerate(saved):
            try:
                yield json.dumps({"index": i, "step": "ocr", "message": f"Scanner kvittering {i + 1} af {len(saved)}..."}) + "\n"
                receipt_data = extract_receipt_data(str(temp_path))
                receipt_data = validate_ocr_result(receipt_data)
                yield json.dumps({"index": i, "status": "ok", "receipt": receipt_data, "temp_id": temp_id, "filename": original_name}) + "\n"
            except Exception as e:
                app.logger.error("Scan fejl for %s: %s", original_name, e)
                if temp_path.exists():
                    temp_path.unlink()
                yield json.dumps({"index": i, "status": "error", "error": str(e), "filename": original_name}) + "\n"

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/confirm", methods=["POST"])
def confirm():
    """Send reviewed receipt data + images to Google Sheets via Apps Script."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Ingen data modtaget."}), 400

    name = data.get("name", "").strip()
    comment = data.get("comment", "").strip()
    payment_type = data.get("payment_type", "").strip()
    phone = data.get("phone", "").strip()
    reg_nr = data.get("reg_nr", "").strip()
    konto_nr = data.get("konto_nr", "").strip()
    udvalg = data.get("udvalg", "").strip()
    receipts = data.get("receipts", [])

    if not name:
        return jsonify({"error": "Navn mangler."}), 400
    if not receipts:
        return jsonify({"error": "Ingen kvitteringer at sende."}), 400

    # Validate temp_ids — must be hex + extension, no path traversal
    for item in receipts:
        temp_id = item.get("temp_id", "")
        if not temp_id or "/" in temp_id or "\\" in temp_id or ".." in temp_id:
            return jsonify({"error": "Ugyldig fil-reference."}), 400

    def generate():
        from tools.send_to_sheets import send_receipt

        for i, item in enumerate(receipts):
            temp_id = item.get("temp_id", "")
            receipt_data = item.get("receipt", {})
            temp_path = TMP_DIR / temp_id

            yield json.dumps({"index": i, "step": "sheets", "message": f"Sender kvittering {i + 1} af {len(receipts)}..."}) + "\n"

            if not temp_path.exists():
                yield json.dumps({"index": i, "status": "error", "error": "Billedfil ikke fundet (udløbet)."}) + "\n"
                continue

            try:
                with open(temp_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

                ext = Path(temp_id).suffix
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                drive_filename = f"kvittering_{timestamp}_{name.lower().replace(' ', '_')}{ext}"

                send_receipt(
                    receipt_data=receipt_data,
                    submitter=name,
                    image_base64=image_b64,
                    image_filename=drive_filename,
                    comment=comment,
                    payment_type=payment_type,
                    phone=phone,
                    reg_nr=reg_nr,
                    konto_nr=konto_nr,
                    udvalg=udvalg,
                )
                yield json.dumps({"index": i, "status": "ok"}) + "\n"
            except Exception as e:
                app.logger.error("Confirm fejl for %s: %s", temp_id, e)
                yield json.dumps({"index": i, "status": "error", "error": str(e)}) + "\n"
            finally:
                if temp_path.exists():
                    temp_path.unlink()

    return Response(stream_with_context(generate()), mimetype="text/plain")


# ---------------------------------------------------------------------------
# Dashboard (password-protected)
# ---------------------------------------------------------------------------

def require_dashboard_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("dashboard_auth"):
            return redirect(url_for("dashboard_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/dashboard/login", methods=["GET", "POST"])
def dashboard_login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == os.environ.get("DASHBOARD_PASSWORD", ""):
            session["dashboard_auth"] = True
            return redirect(url_for("dashboard"))
        error = "Forkert adgangskode."
    return render_template("dashboard_login.html", error=error)


@app.route("/dashboard/logout")
def dashboard_logout():
    session.pop("dashboard_auth", None)
    return redirect(url_for("dashboard_login"))


@app.route("/dashboard")
@require_dashboard_auth
def dashboard():
    config = load_config()
    return render_template(
        "dashboard.html",
        forening_name=config.get("forening_name", "Forening"),
        categories_json=json.dumps(config.get("categories", ["Andet"])),
        udvalg_json=json.dumps(config.get("udvalg", [])),
    )


@app.route("/dashboard/api/data")
@require_dashboard_auth
def dashboard_data():
    """Fetch all sheet data via Apps Script doGet."""
    import requests as http_requests

    config = load_config()
    url = config.get("apps_script_url", "")
    if not url:
        return jsonify({"error": "Apps Script URL ikke konfigureret."}), 500

    try:
        resp = http_requests.get(url, timeout=30)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        app.logger.error("Dashboard data fetch fejl: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/api/update-status", methods=["POST"])
@require_dashboard_auth
def dashboard_update_status():
    """Update status for a specific row in Google Sheets."""
    import requests as http_requests

    data = request.get_json()
    if not data or "row" not in data:
        return jsonify({"error": "Mangler rækkenummer."}), 400

    config = load_config()
    url = config.get("apps_script_url", "")

    payload = {
        "action": "updateStatus",
        "row": data["row"],
        "status": data.get("status", ""),
        "udbetalt_dato": data.get("udbetalt_dato", ""),
    }

    try:
        resp = http_requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        app.logger.error("Status update fejl: %s", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
