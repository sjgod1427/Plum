"""
Email utility — SendGrid backend.

Two sending modes:
  send_simple_email()  — plain coded template (used for appeal notifications)
  send_agentic_email() — LLM drafts the email content via tool call (used for MANUAL_REVIEW)

Both are no-ops if SENDGRID_API_KEY or SENDGRID_FROM_EMAIL is not configured,
or if admin_email is not set. Never raises — logs and returns False on failure.
"""

import json
import logging

from config import settings

logger = logging.getLogger(__name__)


def _can_send() -> bool:
    return bool(settings.SENDGRID_API_KEY and settings.SENDGRID_FROM_EMAIL)


def send_simple_email(to: str, subject: str, body: str) -> bool:
    """Send a plain text email via SendGrid. Returns True on success."""
    if not _can_send() or not to:
        logger.warning("[Email] Skipped — SendGrid not configured or no recipient.")
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"[Email] Sent to {to} — status {response.status_code}")
        return response.status_code in (200, 202)
    except Exception as e:
        logger.error(f"[Email] Failed to send: {e}")
        return False


def get_admin_email(session) -> str | None:
    """Read reviewer email from PolicyConfig table. Returns None if not set."""
    try:
        from sqlmodel import select
        from models import PolicyConfig
        config = session.exec(
            select(PolicyConfig).where(PolicyConfig.section == "admin_config")
        ).first()
        if config:
            data = json.loads(config.config_json)
            return data.get("reviewer_email") or None
    except Exception as e:
        logger.error(f"[Email] Failed to read admin email: {e}")
    return None
