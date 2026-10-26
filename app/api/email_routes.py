from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User, UserRole, EmailLog
from app.schemas.schemas import EmailLogOut
from app.core.security import require_roles
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/emails", tags=["Email Logs & Delivery"])

@router.get("/logs", response_model=List[EmailLogOut])
def get_email_logs(
    recipient: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    email_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    query = db.query(EmailLog)
    if recipient:
        query = query.filter(EmailLog.recipient.ilike(f"%{recipient.strip()}%"))
    if status_filter:
        query = query.filter(EmailLog.status == status_filter)
    if email_type:
        query = query.filter(EmailLog.email_type == email_type)

    return query.order_by(EmailLog.sent_at.desc()).limit(limit).all()

@router.post("/retry/{log_id}")
def retry_failed_email(
    log_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Email log record not found.")

    # Re-queue
    queue_email(
        recipient=log.recipient,
        template_key=log.email_type,
        context={"portal_url": "http://localhost:8000"},
        intern_id=log.intern_id,
        prevent_duplicate=False
    )

    return {"message": f"Retried sending {log.email_type} to {log.recipient}."}
