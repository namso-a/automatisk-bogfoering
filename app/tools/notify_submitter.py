"""Email notifications to submitters when their receipt status changes.

Triggered after an admin updates a kvittering's status. Uses Resend (RESEND_API_KEY).
Silently no-ops if the submitter didn't provide an email or if Resend is not configured.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
NOTIFY_FROM = os.environ.get("NOTIFY_FROM", "Kvitly <onboarding@resend.dev>")


SUBJECTS = {
    "godkendt": "Din kvittering er godkendt",
    "udbetalt": "Din kvittering er udbetalt",
    "afvist": "Din kvittering er afvist",
}


def _format_dkk(value) -> str:
    try:
        n = float(value)
    except (ValueError, TypeError):
        return str(value)
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kr."


def _body_for(status: str, kvittering: dict, forening: dict) -> str:
    forening_navn = forening.get("navn", "Foreningen")
    butik = kvittering.get("butik", "din kvittering")
    beloeb = _format_dkk(kvittering.get("beloeb")) if kvittering.get("beloeb") else "kvitteringen"
    admin_note = (kvittering.get("admin_note") or "").strip()
    udbetalt_dato = kvittering.get("udbetalt_dato")

    if status == "godkendt":
        return (
            f"Hej,\n\n"
            f"{forening_navn} har godkendt din kvittering fra {butik} på {beloeb}.\n"
            f"Den udbetales snart — du får besked når det sker.\n"
            + (f"\nKommentar fra foreningen:\n{admin_note}\n" if admin_note else "")
            + f"\nVenlig hilsen,\nKvitly"
        )
    if status == "udbetalt":
        return (
            f"Hej,\n\n"
            f"{forening_navn} har udbetalt din kvittering fra {butik} på {beloeb}"
            + (f" ({udbetalt_dato})" if udbetalt_dato else "")
            + ".\n\nTak for at sende den ind via Kvitly!\n\nVenlig hilsen,\nKvitly"
        )
    if status == "afvist":
        return (
            f"Hej,\n\n"
            f"{forening_navn} har desværre afvist din kvittering fra {butik} på {beloeb}.\n"
            + (f"\nBegrundelse:\n{admin_note}\n" if admin_note else "")
            + f"\nKontakt foreningen direkte hvis du har spørgsmål.\n\nVenlig hilsen,\nKvitly"
        )
    return ""


def notify_welcome(email: str, forening: dict, upload_link: str) -> bool:
    """Send a welcome email to a newly-signed-up forening admin.

    Returns True if email sent. No-ops if Resend isn't configured or email missing.
    """
    if not RESEND_API_KEY or not email:
        return False

    forening_navn = forening.get("navn", "din forening")
    dashboard_url = "https://kvitly.dk/dashboard"

    subject = f"Velkommen til Kvitly, {forening_navn}"

    text_body = (
        f"Hej,\n\n"
        f"Tak fordi I valgte Kvitly til {forening_navn}.\n\n"
        f"Sådan kommer I i gang:\n\n"
        f"1) Del jeres upload-link med alle frivillige:\n   {upload_link}\n\n"
        f"   Du finder også en QR-kode i dashboardet — print den og hæng den op i klubhuset.\n\n"
        f"2) Bekræft jeres udvalg + kategorier i Indstillinger\n   {dashboard_url}\n\n"
        f"3) Frivillige uploader kvitteringer fra deres mobil — uden at installere en app.\n"
        f"   AI læser beløb, dato og butik automatisk. I godkender og udbetaler med ét klik.\n\n"
        f"Spørgsmål? Skriv tilbage på denne mail, eller direkte til Othman@ajjalytics.dev.\n\n"
        f"Venlig hilsen,\n"
        f"Othman — Kvitly"
    )

    html_body = f"""<!doctype html>
<html lang="da">
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#fafaf7; color:#1a1612; padding:32px 16px; margin:0;">
  <div style="max-width:540px; margin:0 auto; background:#fff; border:1px solid #e8e4d8; border-radius:10px; padding:32px;">
    <h1 style="font-family:Georgia,serif; font-weight:400; font-size:24px; margin:0 0 16px; letter-spacing:-0.02em;">Velkommen til Kvitly, {forening_navn} 👋</h1>
    <p style="line-height:1.55; color:#3d352e; margin:0 0 20px;">Tak fordi I valgte Kvitly. Her er hvad I skal gøre for at komme i gang.</p>

    <h2 style="font-size:14px; text-transform:uppercase; letter-spacing:0.06em; color:#9a6f28; margin:24px 0 8px;">1. Del upload-linket</h2>
    <p style="line-height:1.55; margin:0 0 8px;">Send dette link til alle frivillige i foreningen:</p>
    <p style="background:#f1eee5; padding:12px 14px; border-radius:6px; font-family:monospace; word-break:break-all; margin:0 0 16px;"><a href="{upload_link}" style="color:#9a6f28; text-decoration:none;">{upload_link}</a></p>
    <p style="line-height:1.55; color:#8a817a; font-size:14px; margin:0 0 24px;">Du finder også en QR-kode i dashboardet — print den og hæng op i klubhuset.</p>

    <h2 style="font-size:14px; text-transform:uppercase; letter-spacing:0.06em; color:#9a6f28; margin:24px 0 8px;">2. Tjek dine indstillinger</h2>
    <p style="line-height:1.55; margin:0 0 24px;">Bekræft jeres udvalg + kategorier under <a href="{dashboard_url}" style="color:#9a6f28;">Indstillinger i dashboardet</a>.</p>

    <h2 style="font-size:14px; text-transform:uppercase; letter-spacing:0.06em; color:#9a6f28; margin:24px 0 8px;">3. Lad de frivillige uploade</h2>
    <p style="line-height:1.55; margin:0 0 24px;">AI læser beløb, dato og butik automatisk. I godkender og markerer som udbetalt med ét klik fra dashboardet.</p>

    <hr style="border:0; border-top:1px solid #e8e4d8; margin:32px 0;">
    <p style="line-height:1.55; color:#8a817a; font-size:14px; margin:0;">Spørgsmål? Bare svar på denne mail, eller skriv direkte til <a href="mailto:Othman@ajjalytics.dev" style="color:#9a6f28;">Othman@ajjalytics.dev</a>.</p>
    <p style="line-height:1.55; color:#8a817a; font-size:14px; margin:8px 0 0;">Venlig hilsen,<br>Othman — Kvitly</p>
  </div>
</body>
</html>"""

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": NOTIFY_FROM,
                "to": [email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            },
            timeout=10,
        )
        return r.status_code < 400
    except Exception:
        return False


def notify_status_change(kvittering: dict, forening: dict) -> bool:
    """Send a status notification email if conditions are met. Returns True if sent."""
    if not RESEND_API_KEY:
        return False

    email = (kvittering.get("submitter_email") or "").strip()
    status = (kvittering.get("status") or "").strip()
    if not email or status not in SUBJECTS:
        return False

    subject = SUBJECTS[status]
    body = _body_for(status, kvittering, forening)
    if not body:
        return False

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": NOTIFY_FROM,
                "to": [email],
                "subject": f"{subject} — {forening.get('navn', 'Kvitly')}",
                "text": body,
            },
            timeout=10,
        )
        return r.status_code < 400
    except Exception:
        return False
