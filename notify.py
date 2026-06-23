"""Email notifications for the A2A approval workflow.

Mirrors the Catering/Room Booking integration: the LSTM internal SMTP relay
(`smtprelay.lstmed.ac.uk:25`, no auth) with a per-app sender address. Approvers
are notified by email-with-a-link (an unguessable per-approver token), the same
pattern Catering uses.

Dev-safe by default: unless A2A_EMAIL_ENABLED is truthy the message is *logged*,
not sent (so local runs never email anyone). Set A2A_EMAIL_ENABLED=1 on the VM.

Config (.env):
    A2A_EMAIL_ENABLED     "1" to actually send; otherwise log-only (default)
    A2A_SMTP_HOST         default smtprelay.lstmed.ac.uk
    A2A_SMTP_PORT         default 25
    A2A_FROM_EMAIL        default a2a-smtp@lstmed.ac.uk
    A2A_BASE_URL          default https://trackon.lstmed.ac.uk/A2A (for links in
                          emails sent outside a request context)
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger("a2a.notify")

SMTP_HOST = os.environ.get("A2A_SMTP_HOST", "smtprelay.lstmed.ac.uk")
SMTP_PORT = int(os.environ.get("A2A_SMTP_PORT", "25"))
FROM_EMAIL = os.environ.get("A2A_FROM_EMAIL", "a2a-smtp@lstmed.ac.uk")
BASE_URL = os.environ.get("A2A_BASE_URL", "https://trackon.lstmed.ac.uk/A2A")
EMAIL_ENABLED = os.environ.get("A2A_EMAIL_ENABLED", "").strip().lower() in (
    "1", "true", "yes", "on")


def send_email(to_email: str, subject: str, html: str) -> bool:
    """Send (or, in dev, log) an HTML email. Returns True if handled without
    error. Never raises — a notification failure must not break the workflow."""
    if not EMAIL_ENABLED:
        log.info("[email-disabled] would send to %s | %s", to_email, subject)
        return True
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.sendmail(FROM_EMAIL, [to_email], msg.as_string())
        log.info("Sent A2A email to %s | %s", to_email, subject)
        return True
    except Exception as exc:  # noqa: BLE001 — notifications are best-effort
        log.error("SMTP send to %s failed: %s", to_email, exc)
        return False


# --- HTML builders ---------------------------------------------------------
def _shell(title: str, body: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
      <div style="background:#dc002e;padding:16px 24px">
        <h2 style="color:#fff;margin:0">{title}</h2>
      </div>
      <div style="padding:24px">{body}</div>
      <div style="background:#f5f5f5;padding:12px 24px;font-size:12px;color:#666">
        Issued by OnTrack Workflow Hub &mdash; Internal Use Only
      </div>
    </body></html>"""


def _button(url: str, label: str) -> str:
    return (
        f'<div style="margin-top:24px"><a href="{url}" '
        'style="background:#dc002e;color:#fff;padding:12px 28px;text-decoration:none;'
        'border-radius:4px;display:inline-block;font-weight:bold">'
        f'{label}</a>'
        f'<p style="margin:12px 0 0;font-size:12px;color:#666">Or copy this link: {url}</p></div>')


def approval_request_html(ref: str, purpose: str, role: str, requester: str,
                          approve_url: str) -> str:
    body = (
        f"<p>An A2A request needs your approval as <strong>{role}</strong>.</p>"
        '<table cellpadding="6" cellspacing="0" width="100%" style="border-collapse:collapse">'
        f'<tr style="background:#f5f5f5"><td><strong>Reference</strong></td><td>{ref}</td></tr>'
        f'<tr><td><strong>Type</strong></td><td>{purpose}</td></tr>'
        f'<tr style="background:#f5f5f5"><td><strong>Raised by</strong></td><td>{requester or "—"}</td></tr>'
        "</table>"
        + _button(approve_url, "Review & Approve"))
    return _shell(f"A2A {ref} — approval needed", body)


def rejection_html(ref: str, role: str, decision: str, comments: str,
                   returned_to: str) -> str:
    body = (
        f"<p>A2A <strong>{ref}</strong> was <strong>{decision}</strong> by the "
        f"{role}.</p>"
        f"<p><strong>Returned to:</strong> {returned_to}</p>"
        f'<p><strong>Comments:</strong><br>{comments or "—"}</p>')
    return _shell(f"A2A {ref} — {decision}", body)
