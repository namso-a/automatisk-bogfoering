"""
Kvitly v2 — Multi-tenant SaaS for receipt automation.

Routes:
    GET  /                          Landing page
    GET  /signup                    Signup form (requires invite code)
    POST /signup                    Create admin + forening
    GET  /invite/<code>             Direct signup link with pre-filled code
    GET  /login                     Login form
    POST /login                     Authenticate, set JWT cookie
    GET  /logout                    Clear session
    GET  /privatlivspolitik         Privacy policy

    GET  /u/<token>                 Member upload form (anonymous)
    POST /u/<token>/scan            OCR receipts (rate-limited)
    POST /u/<token>/confirm         Submit confirmed receipts (rate-limited)

    GET  /dashboard                 Forening admin dashboard (auth required)
    GET  /dashboard/api/data        List kvitteringer for forening
    GET  /dashboard/api/categories  List categories
    POST /dashboard/api/categories  Add category
    DELETE /dashboard/api/categories/<id>
    GET  /dashboard/api/udvalg      List udvalg
    POST /dashboard/api/udvalg      Add udvalg
    DELETE /dashboard/api/udvalg/<id>
    POST /dashboard/api/update-status
    POST /dashboard/api/regenerate-token
    POST /dashboard/api/upload-disabled
    DELETE /dashboard/api/kvittering/<id>
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import qrcode
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    stream_with_context,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from tools import auth, db

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

TMP_DIR = ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)

CANONICAL_HOST = os.environ.get("CANONICAL_HOST", "").strip().lower()


@app.before_request
def force_canonical_host():
    """301-redirect any request hitting a non-canonical host (e.g. the legacy
    *.onrender.com URL) to the canonical domain. Idempotent — does nothing
    when CANONICAL_HOST is unset (development) or already matched."""
    if not CANONICAL_HOST:
        return None
    host = (request.host or "").lower()
    if host == CANONICAL_HOST:
        return None
    # Skip during local dev (localhost / 127.0.0.1 / private LAN ips)
    if host.startswith(("localhost", "127.", "192.168.", "10.")):
        return None
    target = f"https://{CANONICAL_HOST}{request.full_path}"
    if target.endswith("?"):
        target = target[:-1]
    return redirect(target, code=301)

# Rate limiter: anonymous /u/<token>/* routes are protected
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],  # most routes have no limit; we apply per-route
    storage_uri="memory://",
)


# =============================================================================
# Helpers
# =============================================================================


def cleanup_old_temp_files(max_age_seconds=3600):
    now = time.time()
    for f in TMP_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            try:
                if now - f.stat().st_mtime > max_age_seconds:
                    f.unlink()
            except OSError:
                pass


def validate_ocr_result(receipt_data: dict) -> dict:
    """Add confidence_note when OCR fields are missing/invalid (never reject)."""
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


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def is_valid_email(email: str) -> bool:
    if not email or len(email) > 200:
        return False
    return bool(_EMAIL_RE.match(email.strip().lower()))


def slugify(s: str) -> str:
    """Generate a URL-safe slug from a forening name."""
    s = (s or "").lower().strip()
    s = re.sub(r"[æà]", "a", s)
    s = re.sub(r"[øö]", "o", s)
    s = re.sub(r"å", "aa", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:40] or f"forening-{uuid.uuid4().hex[:6]}"


def ensure_unique_slug(base: str) -> str:
    sb = db.service_client()
    slug = base
    n = 1
    while True:
        res = sb.table("foreninger").select("id").eq("slug", slug).limit(1).execute()
        if not res.data:
            return slug
        n += 1
        slug = f"{base}-{n}"
        if n > 999:
            return f"{base}-{uuid.uuid4().hex[:6]}"


# =============================================================================
# Public routes
# =============================================================================


@app.route("/")
def index():
    return render_template("landing.html", loom_embed_url=os.environ.get("LOOM_EMBED_URL", ""))


@app.route("/privatlivspolitik")
def privatlivspolitik():
    return render_template("privatlivspolitik.html")


@app.route("/handelsbetingelser")
def handelsbetingelser():
    return render_template("handelsbetingelser.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}), 200


@app.route("/demo-request", methods=["POST"])
@limiter.limit("10 per minute")
def demo_request():
    """Receive a demo/invite request from the landing form.

    Auto-generates an invite-code, mails Osman with a one-click invite-link
    so he can forward to the forening (or grant directly).
    """
    import requests as http_requests

    data = request.get_json() or {}
    forening = (data.get("forening") or "").strip()[:200]
    navn = (data.get("navn") or "").strip()[:100]
    email = (data.get("email") or "").strip().lower()[:200]
    besked = (data.get("besked") or "").strip()[:2000]

    if not forening or not navn or not email:
        return jsonify({"error": "Udfyld forening, navn og email."}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Ugyldig email."}), 400

    try:
        invite = db.create_invite_code(note=f"Demo-anmodning fra {forening} ({email})")
    except Exception as e:
        app.logger.error("demo-request invite-code failed: %s", e)
        invite = None

    invite_url = (
        f"{request.url_root.rstrip('/')}/invite/{invite}"
        if invite else "(kunne ikke genereres — opret manuelt)"
    )
    submitter_ip = request.headers.get(
        "X-Forwarded-For", request.remote_addr or ""
    ).split(",")[0].strip()

    resend_key = os.environ.get("RESEND_API_KEY", "")
    if resend_key:
        try:
            sender = os.environ.get("NOTIFY_FROM", "Kvitly <onboarding@resend.dev>")
            body = (
                f"Ny demo-anmodning på Kvitly\n\n"
                f"Forening: {forening}\n"
                f"Navn: {navn}\n"
                f"Email: {email}\n"
                f"IP: {submitter_ip}\n\n"
                f"Besked:\n{besked or '(ingen besked)'}\n\n"
                f"--- INVITE-LINK (klar til at videresende) ---\n"
                f"{invite_url}\n"
            )
            http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": sender,
                    "to": ["othman@ajjalytics.dev"],
                    "subject": f"Kvitly demo-anmodning: {forening}",
                    "text": body,
                    "reply_to": email,
                },
                timeout=10,
            )
        except Exception as e:
            app.logger.warning("demo-request Resend email failed: %s", e)

    return jsonify({"status": "ok"})


@app.route("/login", methods=["GET"])
def login():
    if auth.decode_jwt(auth.get_jwt_from_request()):
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=None, email="")


@app.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        return render_template("login.html", error="Udfyld email og adgangskode.", email=email), 400
    token, err = auth.sign_in_with_password(email, password)
    if err or not token:
        return render_template("login.html", error="Forkert email eller adgangskode.", email=email), 401
    resp = make_response(redirect(url_for("dashboard")))
    auth.set_jwt_cookie(resp, token)
    return resp


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("index")))
    auth.clear_jwt_cookie(resp)
    return resp


@app.route("/forgot-password", methods=["GET"])
def forgot_password():
    return render_template("forgot_password.html", error=None, sent=False, email="")


@app.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per minute")
def forgot_password_post():
    email = (request.form.get("email") or "").strip().lower()
    if not email or not is_valid_email(email):
        return render_template(
            "forgot_password.html",
            error="Indtast en gyldig email-adresse.",
            sent=False,
            email=email,
        ), 400
    redirect_url = f"{request.url_root.rstrip('/')}/reset-password"
    # Always return success — never reveal whether email exists in our system
    auth.send_password_reset_email(email, redirect_url)
    return render_template("forgot_password.html", error=None, sent=True, email=email)


@app.route("/reset-password", methods=["GET"])
def reset_password():
    """Land users here from the email link. Supabase appends auth tokens to
    the URL hash (#access_token=…&refresh_token=…), which the template's JS
    must read and submit alongside the new password."""
    return render_template("reset_password.html", error=None, success=False)


@app.route("/reset-password", methods=["POST"])
@limiter.limit("10 per minute")
def reset_password_post():
    access_token = (request.form.get("access_token") or "").strip()
    password = request.form.get("password") or ""
    if not access_token:
        return render_template(
            "reset_password.html",
            error="Reset-link er udløbet eller mangler. Bed om et nyt på Glemt adgangskode-siden.",
            success=False,
        ), 400
    if len(password) < 8:
        return render_template(
            "reset_password.html",
            error="Adgangskoden skal være mindst 8 tegn.",
            success=False,
        ), 400
    ok, err = auth.update_user_password(access_token, password)
    if not ok:
        return render_template(
            "reset_password.html",
            error=f"Kunne ikke opdatere adgangskode: {err or 'ukendt fejl'}",
            success=False,
        ), 400
    return render_template("reset_password.html", error=None, success=True)


@app.route("/dev-login")
def dev_login():
    """One-click admin login for development/testing.

    Activated only when DEV_LOGIN_KEY is set in env. Visit
        /dev-login?key=<DEV_LOGIN_KEY>
    and Flask will sign you in as DEV_LOGIN_EMAIL using DEV_LOGIN_PASSWORD,
    then redirect to /dashboard. Bookmark the URL for one-click access.

    Remove DEV_LOGIN_KEY from env to disable the route entirely.
    """
    expected_key = os.environ.get("DEV_LOGIN_KEY", "").strip()
    email = os.environ.get("DEV_LOGIN_EMAIL", "").strip()
    password = os.environ.get("DEV_LOGIN_PASSWORD", "")

    if not expected_key or not email or not password:
        return "Dev login is not configured.", 404

    provided = (request.args.get("key") or "").strip()
    if provided != expected_key:
        # Constant-time-ish check; both are short strings, hidden behind 404
        return "Not found.", 404

    token, err = auth.sign_in_with_password(email, password)
    if err or not token:
        app.logger.error("dev-login failed for %s: %s", email, err)
        return f"Dev login failed: {err or 'unknown'}", 500

    resp = make_response(redirect(url_for("dashboard")))
    auth.set_jwt_cookie(resp, token)
    return resp


@app.route("/invite/<code>")
def invite_link(code):
    """Pre-fill invite code on signup form."""
    return render_template("signup.html", invite_code=code, error=None, prefill={})


@app.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html", invite_code="", error=None, prefill={})


@app.route("/signup", methods=["POST"])
def signup_post():
    invite_code = request.form.get("invite_code", "").strip().lower()
    forening_navn = request.form.get("forening_navn", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    prefill = {"forening_navn": forening_navn, "email": email}

    if not invite_code or not forening_navn or not email or not password:
        return render_template(
            "signup.html",
            invite_code=invite_code,
            error="Alle felter skal udfyldes.",
            prefill=prefill,
        ), 400
    if len(password) < 8:
        return render_template(
            "signup.html",
            invite_code=invite_code,
            error="Adgangskoden skal være mindst 8 tegn.",
            prefill=prefill,
        ), 400

    invite = db.find_invite_code(invite_code)
    if not invite or invite.get("used_at"):
        return render_template(
            "signup.html",
            invite_code=invite_code,
            error="Ugyldig eller allerede brugt invite-kode.",
            prefill=prefill,
        ), 400

    user_id, access_token, err = auth.sign_up_with_password(email, password)
    if err or not user_id:
        return render_template(
            "signup.html",
            invite_code=invite_code,
            error=f"Kunne ikke oprette bruger: {err or 'ukendt fejl'}",
            prefill=prefill,
        ), 400

    slug = ensure_unique_slug(slugify(forening_navn))
    try:
        forening = db.create_forening(slug=slug, navn=forening_navn, auth_user_id=user_id)
    except Exception as e:
        return render_template(
            "signup.html",
            invite_code=invite_code,
            error=f"Kunne ikke oprette forening: {e}",
            prefill=prefill,
        ), 500

    db.consume_invite_code(invite_code, forening["id"])

    if access_token:
        resp = make_response(redirect(url_for("dashboard")))
        auth.set_jwt_cookie(resp, access_token)
        return resp
    # Email confirmation required — send to login
    return render_template(
        "login.html",
        error="Tjek din indbakke for at bekræfte din email, derefter log ind.",
        email=email,
    )


# =============================================================================
# Anonymous member upload routes (rate-limited)
# =============================================================================


def _resolve_token_or_404(token: str):
    forening = db.forening_by_token(token)
    if not forening:
        return None, (jsonify({"error": "Ugyldigt link eller deaktiveret."}), 404)
    if forening.get("upload_disabled"):
        return None, (jsonify({"error": "Foreningen har sat upload på pause."}), 403)
    return forening, None


@app.route("/u/<token>")
@limiter.limit("60 per minute")
def upload_form(token):
    forening = db.forening_by_token(token)
    if not forening:
        return render_template("upload_invalid.html"), 404
    udvalg_list = [u["navn"] for u in db.list_udvalg(forening["id"])]
    return render_template(
        "form.html",
        forening_name=forening["navn"],
        upload_token=token,
        categories_json=json.dumps([c["navn"] for c in db.list_categories(forening["id"])] or ["Andet"]),
        udvalg_json=json.dumps(udvalg_list),
        member_email_required=bool(forening.get("member_email_required", False)),
    )


@app.route("/u/<token>/scan", methods=["POST"])
@limiter.limit("30 per minute")
def upload_scan(token):
    forening, err_resp = _resolve_token_or_404(token)
    if err_resp:
        return err_resp

    name = request.form.get("name", "").strip()
    files = request.files.getlist("receipt")

    if not name:
        return jsonify({"error": "Vælg venligst dit navn."}), 400
    if not files:
        return jsonify({"error": "Vedhæft venligst mindst én kvittering."}), 400

    cleanup_old_temp_files()

    saved = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower() or ".jpg"
        temp_id = f"{uuid.uuid4().hex}{ext}"
        temp_path = TMP_DIR / temp_id
        file.save(str(temp_path))
        saved.append((temp_path, temp_id, file.filename, ext))

    def generate():
        from tools.ocr_receipt import extract_receipt_data

        for i, (temp_path, temp_id, original_name, ext) in enumerate(saved):
            try:
                yield json.dumps({
                    "index": i,
                    "step": "ocr",
                    "message": f"Scanner kvittering {i + 1} af {len(saved)}...",
                }) + "\n"
                receipt_data = extract_receipt_data(str(temp_path))
                receipt_data = validate_ocr_result(receipt_data)
                yield json.dumps({
                    "index": i,
                    "status": "ok",
                    "receipt": receipt_data,
                    "temp_id": temp_id,
                    "filename": original_name,
                }) + "\n"
            except Exception as e:
                app.logger.error("Scan fejl for %s: %s", original_name, e)
                if temp_path.exists():
                    temp_path.unlink()
                yield json.dumps({
                    "index": i,
                    "status": "error",
                    "error": str(e),
                    "filename": original_name,
                }) + "\n"

    return Response(stream_with_context(generate()), mimetype="text/plain")


@app.route("/u/<token>/confirm", methods=["POST"])
@limiter.limit("30 per minute")
def upload_confirm(token):
    forening, err_resp = _resolve_token_or_404(token)
    if err_resp:
        return err_resp

    data = request.get_json()
    if not data:
        return jsonify({"error": "Ingen data modtaget."}), 400

    name = (data.get("name") or "").strip()
    submitter_email = (data.get("submitter_email") or "").strip().lower() or None
    if submitter_email and not is_valid_email(submitter_email):
        return jsonify({"error": "Ugyldig email-adresse."}), 400
    if forening.get("member_email_required") and not submitter_email:
        return jsonify({"error": "Email er påkrævet for denne forening."}), 400
    comment = (data.get("comment") or "").strip()
    payment_type = (data.get("payment_type") or "").strip()
    phone = (data.get("phone") or "").strip()
    reg_nr = (data.get("reg_nr") or "").strip()
    konto_nr = (data.get("konto_nr") or "").strip()
    udvalg = (data.get("udvalg") or "").strip()
    receipts = data.get("receipts") or []

    if not name:
        return jsonify({"error": "Navn mangler."}), 400
    if not receipts:
        return jsonify({"error": "Ingen kvitteringer at sende."}), 400

    for item in receipts:
        temp_id = item.get("temp_id", "")
        if not temp_id or "/" in temp_id or "\\" in temp_id or ".." in temp_id:
            return jsonify({"error": "Ugyldig fil-reference."}), 400

    submitter_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip() or None

    def generate():
        for i, item in enumerate(receipts):
            temp_id = item["temp_id"]
            receipt_data = item.get("receipt") or {}
            temp_path = TMP_DIR / temp_id

            yield json.dumps({
                "index": i,
                "step": "saving",
                "message": f"Gemmer kvittering {i + 1} af {len(receipts)}...",
            }) + "\n"

            if not temp_path.exists():
                yield json.dumps({"index": i, "status": "error", "error": "Billedfil ikke fundet (udløbet)."}) + "\n"
                continue

            try:
                ext = Path(temp_id).suffix
                with open(temp_path, "rb") as f:
                    image_bytes = f.read()
                billede_path = db.upload_image(forening["slug"], image_bytes, ext)

                amount = receipt_data.get("amount")
                try:
                    amount_num = float(amount) if amount is not None else None
                except (ValueError, TypeError):
                    amount_num = None

                row = {
                    "dato": receipt_data.get("date") or None,
                    "navn": name,
                    "submitter_email": submitter_email,
                    "type": payment_type or None,
                    "udvalg": udvalg or None,
                    "telefon": phone or None,
                    "reg_nr": reg_nr or None,
                    "konto_nr": konto_nr or None,
                    "butik": receipt_data.get("vendor") or None,
                    "beskrivelse": receipt_data.get("description") or None,
                    "beloeb": amount_num,
                    "valuta": receipt_data.get("currency") or "DKK",
                    "kategori": receipt_data.get("category") or "Andet",
                    "kommentar": comment or None,
                    "ocr_note": receipt_data.get("confidence_note") or None,
                    "billede_path": billede_path,
                    "submitter_ip": submitter_ip,
                }
                db.insert_kvittering(forening["id"], row)
                yield json.dumps({"index": i, "status": "ok"}) + "\n"
            except Exception as e:
                app.logger.error("Confirm fejl for %s: %s", temp_id, e)
                yield json.dumps({"index": i, "status": "error", "error": str(e)}) + "\n"
            finally:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass

    return Response(stream_with_context(generate()), mimetype="text/plain")


# =============================================================================
# Dashboard routes (auth required)
# =============================================================================


@app.route("/dashboard")
@auth.require_forening_admin
def dashboard():
    forening = g.forening
    cats = [c["navn"] for c in db.list_categories(forening["id"])]
    udvalg_list = [u["navn"] for u in db.list_udvalg(forening["id"])]
    if not cats:
        cats = ["Transport", "Forplejning", "Materialer", "Udstyr", "Aktiviteter", "Andet"]
    return render_template(
        "dashboard.html",
        forening_name=forening["navn"],
        forening_slug=forening["slug"],
        upload_token=forening["upload_token"],
        upload_disabled=forening.get("upload_disabled", False),
        member_email_required=bool(forening.get("member_email_required", False)),
        upload_link_base=request.url_root.rstrip("/"),
        categories_json=json.dumps(cats),
        udvalg_json=json.dumps(udvalg_list),
    )


@app.route("/dashboard/qr/<token>.png")
@auth.require_forening_admin
def dashboard_qr(token):
    """QR-code PNG of upload link for download/print."""
    if token != g.forening["upload_token"]:
        return "", 404
    upload_url = f"{request.url_root.rstrip('/')}/u/{token}"
    img = qrcode.make(upload_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"kvitly-upload-{token}.png")


def _map_row_to_dashboard(row: dict) -> dict:
    """Transform a Supabase kvittering row into the Sheet-style keys
    that the existing dashboard.html JavaScript expects."""
    image_url = db.public_image_url(row["billede_path"]) if row.get("billede_path") else ""
    indsendt_raw = row.get("indsendt_at") or ""
    # Convert "2026-05-06T14:30:00+00:00" → "2026-05-06 14:30"
    indsendt_display = ""
    if indsendt_raw:
        try:
            indsendt_display = indsendt_raw[:16].replace("T", " ")
        except Exception:
            indsendt_display = indsendt_raw
    # Capitalize status for display (frontend normalizes back to lowercase for class-name lookup)
    status = (row.get("status") or "").strip()
    status_display = status.capitalize() if status else ""
    return {
        "id": row["id"],
        "_row": row["id"],  # legacy alias used throughout dashboard.html
        "Dato": row.get("dato") or "",
        "Indsendt": indsendt_display,
        "Navn": row.get("navn") or "",
        "Type": row.get("type") or "",
        "Udvalg": row.get("udvalg") or "",
        "Telefon": row.get("telefon") or "",
        "Reg.nr.": row.get("reg_nr") or "",
        "Kontonr.": row.get("konto_nr") or "",
        "Butik": row.get("butik") or "",
        "Beskrivelse": row.get("beskrivelse") or "",
        "Beløb": row.get("beloeb"),
        "Valuta": row.get("valuta") or "DKK",
        "Kategori": row.get("kategori") or "",
        "Kommentar": row.get("kommentar") or "",
        "Kvittering": image_url,
        "Status": status_display,
        "Udbetalt dato": row.get("udbetalt_dato") or "",
        "submitter_email": row.get("submitter_email") or "",
        "admin_note": row.get("admin_note") or "",
        "ocr_note": row.get("ocr_note") or "",
    }


@app.route("/dashboard/api/data")
@auth.require_forening_admin
def api_data():
    rows = db.list_kvitteringer(g.forening["id"])
    mapped = [_map_row_to_dashboard(r) for r in rows]
    headers = [
        "Dato", "Indsendt", "Navn", "Type", "Udvalg", "Telefon", "Reg.nr.", "Kontonr.",
        "Butik", "Beskrivelse", "Beløb", "Valuta", "Kategori", "Kommentar", "Kvittering",
        "Status", "Udbetalt dato",
    ]
    return jsonify({"status": "ok", "headers": headers, "rows": mapped})


@app.route("/dashboard/api/categories", methods=["GET"])
@auth.require_forening_admin
def api_categories_list():
    return jsonify({"categories": db.list_categories(g.forening["id"])})


@app.route("/dashboard/api/categories", methods=["POST"])
@auth.require_forening_admin
def api_categories_add():
    data = request.get_json() or {}
    navn = (data.get("navn") or "").strip()
    if not navn:
        return jsonify({"error": "Navn mangler."}), 400
    try:
        cat = db.add_category(g.forening["id"], navn)
        return jsonify({"category": cat})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/dashboard/api/categories/<cat_id>", methods=["PATCH"])
@auth.require_forening_admin
def api_categories_rename(cat_id):
    data = request.get_json() or {}
    navn = (data.get("navn") or "").strip()
    if not navn:
        return jsonify({"error": "Navn mangler."}), 400
    if len(navn) > 60:
        return jsonify({"error": "Navn er for langt (max 60 tegn)."}), 400
    try:
        cat = db.rename_category(g.forening["id"], cat_id, navn)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if not cat:
        return jsonify({"error": "Kategori ikke fundet."}), 404
    return jsonify({"category": cat})


@app.route("/dashboard/api/categories/<cat_id>", methods=["DELETE"])
@auth.require_forening_admin
def api_categories_delete(cat_id):
    db.delete_category(g.forening["id"], cat_id)
    return jsonify({"status": "ok"})


@app.route("/dashboard/api/udvalg", methods=["GET"])
@auth.require_forening_admin
def api_udvalg_list():
    return jsonify({"udvalg": db.list_udvalg(g.forening["id"])})


@app.route("/dashboard/api/udvalg", methods=["POST"])
@auth.require_forening_admin
def api_udvalg_add():
    data = request.get_json() or {}
    navn = (data.get("navn") or "").strip()
    if not navn:
        return jsonify({"error": "Navn mangler."}), 400
    try:
        u = db.add_udvalg(g.forening["id"], navn)
        return jsonify({"udvalg": u})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/dashboard/api/udvalg/<udvalg_id>", methods=["PATCH"])
@auth.require_forening_admin
def api_udvalg_rename(udvalg_id):
    data = request.get_json() or {}
    navn = (data.get("navn") or "").strip()
    if not navn:
        return jsonify({"error": "Navn mangler."}), 400
    if len(navn) > 60:
        return jsonify({"error": "Navn er for langt (max 60 tegn)."}), 400
    try:
        u = db.rename_udvalg(g.forening["id"], udvalg_id, navn)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if not u:
        return jsonify({"error": "Udvalg ikke fundet."}), 404
    return jsonify({"udvalg": u})


@app.route("/dashboard/api/udvalg/<udvalg_id>", methods=["DELETE"])
@auth.require_forening_admin
def api_udvalg_delete(udvalg_id):
    db.delete_udvalg(g.forening["id"], udvalg_id)
    return jsonify({"status": "ok"})


@app.route("/dashboard/api/forening", methods=["PATCH"])
@auth.require_forening_admin
def api_forening_update():
    data = request.get_json() or {}
    updated = None

    if "navn" in data:
        navn = (data.get("navn") or "").strip()
        if not navn:
            return jsonify({"error": "Navn mangler."}), 400
        if len(navn) > 120:
            return jsonify({"error": "Navn er for langt (max 120 tegn)."}), 400
        try:
            updated = db.update_forening_name(g.forening["id"], navn)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    if "member_email_required" in data:
        try:
            updated = db.set_member_email_required(
                g.forening["id"], bool(data["member_email_required"])
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    if not updated:
        return jsonify({"error": "Ingen ændringer."}), 400
    return jsonify({"forening": updated})


@app.route("/dashboard/api/update-status", methods=["POST"])
@auth.require_forening_admin
def api_update_status():
    data = request.get_json() or {}
    # Accept both `id` (new) and `row` (legacy alias from dashboard.html)
    kvittering_id = data.get("id") or data.get("row")
    raw_status = (data.get("status") or "").strip().lower()  # normalize "Godkendt" → "godkendt"
    udbetalt_dato = data.get("udbetalt_dato") or None
    admin_note = data.get("admin_note")

    if not kvittering_id:
        return jsonify({"error": "Kvittering-id mangler."}), 400
    if raw_status and raw_status not in {"afventer", "godkendt", "udbetalt", "afvist"}:
        return jsonify({"error": "Ugyldig status."}), 400
    status = raw_status

    updates: dict = {}
    if status:
        updates["status"] = status
    if udbetalt_dato:
        updates["udbetalt_dato"] = udbetalt_dato
    if admin_note is not None:
        updates["admin_note"] = admin_note

    if not updates:
        return jsonify({"error": "Ingen ændringer."}), 400

    row = db.update_kvittering(
        kvittering_id, g.forening["id"], updates, actor_user_id=g.user_id
    )
    if not row:
        return jsonify({"error": "Kvittering ikke fundet."}), 404

    # Phase 3b will hook in notify_submitter here
    try:
        from tools.notify_submitter import notify_status_change
        notify_status_change(row, g.forening)
    except Exception as e:
        app.logger.warning("Notify failed: %s", e)

    return jsonify({"status": "ok", "row": row})


@app.route("/dashboard/api/regenerate-token", methods=["POST"])
@auth.require_forening_admin
def api_regenerate_token():
    new_token = db.regenerate_upload_token(g.forening["id"])
    return jsonify({"token": new_token})


@app.route("/dashboard/api/upload-disabled", methods=["POST"])
@auth.require_forening_admin
def api_upload_disabled():
    data = request.get_json() or {}
    disabled = bool(data.get("disabled", False))
    db.set_upload_disabled(g.forening["id"], disabled)
    return jsonify({"status": "ok", "disabled": disabled})


@app.route("/dashboard/api/kvittering/<kvittering_id>", methods=["DELETE"])
@auth.require_forening_admin
def api_delete_kvittering(kvittering_id):
    ok = db.delete_kvittering(kvittering_id, g.forening["id"])
    if not ok:
        return jsonify({"error": "Kvittering ikke fundet."}), 404
    return jsonify({"status": "ok"})


# =============================================================================
# Error handlers
# =============================================================================


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/dashboard/api/") or request.path.startswith("/u/"):
        return jsonify({"error": "Ikke fundet."}), 404
    return render_template("404.html"), 404


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
