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
