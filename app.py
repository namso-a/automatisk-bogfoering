"""
Flask app for automatic receipt processing.

GET  /        — Serves the upload form
POST /upload  — Receives receipt image, runs OCR, sends to Google Sheets via Apps Script
"""

import base64
import json
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

TMP_DIR = ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)


def load_config():
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    config = load_config()
    return render_template(
        "form.html",
        forening_name=config.get("forening_name", "Forening"),
    )


@app.route("/upload", methods=["POST"])
def upload():
    # Validate inputs
    name = request.form.get("name", "").strip()
    comment = request.form.get("comment", "").strip()
    payment_type = request.form.get("payment_type", "").strip()
    phone = request.form.get("phone", "").strip()
    reg_nr = request.form.get("reg_nr", "").strip()
    konto_nr = request.form.get("konto_nr", "").strip()
    file = request.files.get("receipt")

    if not name:
        return jsonify({"error": "Vælg venligst dit navn."}), 400
    if not file or file.filename == "":
        return jsonify({"error": "Vedhæft venligst et billede af kvitteringen."}), 400

    # Save temp file
    ext = Path(file.filename).suffix.lower() or ".jpg"
    temp_filename = f"{uuid.uuid4().hex}{ext}"
    temp_path = TMP_DIR / temp_filename

    try:
        file.save(str(temp_path))

        # Step 1: OCR with Gemini Vision
        from tools.ocr_receipt import extract_receipt_data

        try:
            receipt_data = extract_receipt_data(str(temp_path))
        except Exception as e:
            app.logger.error("OCR fejl for %s: %s", file.filename, e)
            return jsonify({"error": f"OCR fejlede: {e}"}), 500

        # Step 2: Read image as base64 and send to Apps Script (Drive + Sheets)
        from tools.send_to_sheets import send_receipt

        with open(temp_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"kvittering_{timestamp}_{name.lower().replace(' ', '_')}{ext}"

        try:
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
            )
        except Exception as e:
            app.logger.error("Sheets fejl for %s: %s", file.filename, e)
            return jsonify({"error": f"Kunne ikke sende til Google Sheets: {e}"}), 500

        return jsonify({"status": "ok", "message": "Kvittering modtaget!", "receipt": receipt_data})

    except Exception as e:
        app.logger.error("Uventet fejl for %s: %s", file.filename, e)
        return jsonify({"error": f"Der opstod en fejl: {str(e)}"}), 500

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@app.route("/upload-batch", methods=["POST"])
def upload_batch():
    """Accept multiple receipt files, process sequentially, stream NDJSON results."""
    name = request.form.get("name", "").strip()
    comment = request.form.get("comment", "").strip()
    payment_type = request.form.get("payment_type", "").strip()
    phone = request.form.get("phone", "").strip()
    reg_nr = request.form.get("reg_nr", "").strip()
    konto_nr = request.form.get("konto_nr", "").strip()
    files = request.files.getlist("receipt")

    if not name:
        return jsonify({"error": "Vælg venligst dit navn."}), 400
    if not files:
        return jsonify({"error": "Vedhæft venligst mindst én kvittering."}), 400

    # Save all files to disk first (request context needed)
    saved = []
    for file in files:
        ext = Path(file.filename).suffix.lower() or ".jpg"
        temp_filename = f"{uuid.uuid4().hex}{ext}"
        temp_path = TMP_DIR / temp_filename
        file.save(str(temp_path))
        saved.append((temp_path, file.filename, ext))

    def generate():
        from tools.ocr_receipt import extract_receipt_data
        from tools.send_to_sheets import send_receipt

        for i, (temp_path, original_name, ext) in enumerate(saved):
            try:
                receipt_data = extract_receipt_data(str(temp_path))

                with open(temp_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode("utf-8")

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
                )

                yield json.dumps({"index": i, "status": "ok", "receipt": receipt_data}) + "\n"

            except Exception as e:
                app.logger.error("Batch fejl for %s: %s", original_name, e)
                yield json.dumps({"index": i, "status": "error", "error": str(e)}) + "\n"

            finally:
                if temp_path.exists():
                    temp_path.unlink()

    return Response(stream_with_context(generate()), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
