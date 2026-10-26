import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import threading
import queue
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.entities import EmailLog
from app.templates.email_templates import render_email

logger = logging.getLogger("email_service")
logger.setLevel(logging.INFO)

# Background email task queue
email_queue = queue.Queue()

def is_duplicate_email(db: Session, recipient: str, intern_id: Optional[int], email_type: str, cooldown_minutes: int = 15) -> bool:
    """
    Prevents accidental duplicate emails for the same intern and template type within the cooldown window.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
    recent = db.query(EmailLog).filter(
        EmailLog.recipient == recipient,
        EmailLog.email_type == email_type,
        EmailLog.status == "SENT",
        EmailLog.sent_at >= cutoff
    )
    if intern_id:
        recent = recent.filter(EmailLog.intern_id == intern_id)
    return recent.first() is not None

def send_smtp_email(recipient: str, subject: str, body_html: str, body_text: str) -> None:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise ValueError("SMTP credentials (SMTP_USER or SMTP_PASSWORD) are not configured.")
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = recipient

    part1 = MIMEText(body_text, "plain")
    part2 = MIMEText(body_html, "html")
    msg.attach(part1)
    msg.attach(part2)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(msg["From"], [recipient], msg.as_string())

def execute_email_dispatch(item: Dict[str, Any]) -> None:
    recipient = item["recipient"]
    intern_id = item.get("intern_id")
    template_key = item["template_key"]
    context = item["context"]
    prevent_duplicate = item.get("prevent_duplicate", True)

    db: Session = SessionLocal()
    try:
        if prevent_duplicate and is_duplicate_email(db, recipient, intern_id, template_key):
            logger.info(f"[Email Service] Skipped duplicate {template_key} to {recipient}")
            return

        rendered = render_email(template_key, context)
        subject = rendered["subject"]
        body_html = rendered["body_html"]
        body_text = rendered["body_text"]

        status = "SENT"
        error_msg = None

        if settings.EMAIL_PROVIDER == "mock":
            # Mock mode: Record success with preview, ideal for local tests & dev
            logger.info(f"[Email Service: MOCK] Sent '{subject}' to {recipient}")
        elif settings.EMAIL_PROVIDER == "smtp":
            try:
                send_smtp_email(recipient, subject, body_html, body_text)
                logger.info(f"[Email Service: SMTP] Successfully delivered '{subject}' to {recipient}")
            except Exception as e:
                status = "FAILED"
                error_msg = str(e)
                logger.error(f"[Email Service: SMTP ERROR] Failed sending to {recipient}: {e}")
        else:
            status = "FAILED"
            error_msg = f"Unknown email provider '{settings.EMAIL_PROVIDER}'."

        # Log into database
        log_entry = EmailLog(
            recipient=recipient,
            intern_id=intern_id,
            email_type=template_key,
            subject=subject,
            status=status,
            error_message=error_msg,
            content_preview=body_text[:400],
            sent_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()

    except Exception as e:
        logger.error(f"[Email Service] General processing failure: {e}")
        try:
            log_entry = EmailLog(
                recipient=recipient,
                intern_id=intern_id,
                email_type=template_key,
                subject=f"Failed Template: {template_key}",
                status="FAILED",
                error_message=str(e),
                content_preview=None,
                sent_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()

def _worker_loop():
    while True:
        try:
            item = email_queue.get()
            if item is None:
                break
            execute_email_dispatch(item)
            email_queue.task_done()
        except Exception as e:
            logger.error(f"[Email Worker Loop Error] {e}")

# Start background daemon worker thread
_worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="EmailBackgroundWorker")
_worker_thread.start()

def queue_email(
    recipient: str,
    template_key: str,
    context: Dict[str, Any],
    intern_id: Optional[int] = None,
    prevent_duplicate: bool = True
) -> None:
    """
    Enqueues an email to be sent asynchronously in the background.
    Safe for bulk operations (100+ interns).
    """
    email_queue.put({
        "recipient": recipient,
        "template_key": template_key,
        "context": context,
        "intern_id": intern_id,
        "prevent_duplicate": prevent_duplicate
    })
