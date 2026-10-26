from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import (
    User, UserRole, InternProfile, ReviewSchedule, AuditLog, WorkflowStatus
)
from app.schemas.schemas import ReviewCreate, ReviewUpdate, ReviewOut
from app.core.security import get_current_user, require_roles
from app.core.calendar_service import (
    validate_google_meet_link, check_mentor_schedule_conflict, create_google_calendar_event
)
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/reviews", tags=["Review Scheduling"])

@router.get("", response_model=List[ReviewOut])
def list_reviews(
    intern_id: Optional[int] = None,
    mentor_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ReviewSchedule)

    # If intern, isolate to their own reviews
    if current_user.role == UserRole.INTERN.value:
        profile = db.query(InternProfile).filter(InternProfile.user_id == current_user.id).first()
        if not profile:
            return []
        query = query.filter(ReviewSchedule.intern_id == profile.id)
    else:
        if intern_id:
            query = query.filter(ReviewSchedule.intern_id == intern_id)
        if mentor_id:
            query = query.filter(ReviewSchedule.mentor_id == mentor_id)
        elif current_user.role == UserRole.MENTOR.value:
            query = query.filter(ReviewSchedule.mentor_id == current_user.id)

    if status_filter:
        query = query.filter(ReviewSchedule.status == status_filter)

    return query.order_by(ReviewSchedule.review_date.desc()).all()

@router.post("", response_model=ReviewOut)
def schedule_review(
    req: ReviewCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    intern = db.query(InternProfile).filter(InternProfile.id == req.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found.")

    mentor = db.query(User).filter(User.id == req.mentor_id).first()
    if not mentor or mentor.role != UserRole.MENTOR.value:
        raise HTTPException(status_code=400, detail="Specified mentor is invalid or not registered as a mentor.")

    # 1. Overlap Conflict Check
    conflict = check_mentor_schedule_conflict(
        db=db,
        mentor_id=req.mentor_id,
        review_date=req.review_date,
        start_time=req.start_time,
        end_time=req.end_time
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scheduling Conflict: Mentor {mentor.full_name} is already booked for review #{conflict.id} on {conflict.review_date.strftime('%Y-%m-%d')} from {conflict.start_time} to {conflict.end_time}."
        )

    meet_link = req.google_meet_link
    calendar_event_id = None

    # 2. Automated Google Calendar OAuth scheduling if requested
    if req.use_google_calendar:
        start_dt = req.review_date
        end_dt = req.review_date + timedelta(minutes=45)
        cal_res = create_google_calendar_event(
            mentor_email=mentor.email,
            intern_email=intern.user.email,
            summary=f"Intern Review: {intern.user.full_name} ({intern.intern_id})",
            description=f"Performance review for {intern.assigned_task.title if intern.assigned_task else 'Internship Task'}.\nNotes: {req.notes or ''}",
            start_dt=start_dt,
            end_dt=end_dt,
            timezone=req.timezone
        )
        if cal_res["success"]:
            meet_link = cal_res["meet_link"]
            calendar_event_id = cal_res["event_id"]
        else:
            # Fall back to manual link requirement without pretending success
            if not meet_link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Google Calendar integration failed ({cal_res['error']}). Please enter an existing Google Meet link manually."
                )

    # 3. Validate Meet link
    if not meet_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A Google Meet link is required. Please provide a valid URL (e.g., https://meet.google.com/abc-defg-hij)."
        )

    if not validate_google_meet_link(meet_link):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided link is not a valid Google Meet link. Format should be: https://meet.google.com/xxx-xxxx-xxx."
        )

    # 4. Save review
    review = ReviewSchedule(
        intern_id=intern.id,
        mentor_id=mentor.id,
        review_date=req.review_date,
        start_time=req.start_time,
        end_time=req.end_time,
        timezone=req.timezone,
        google_meet_link=meet_link,
        calendar_event_id=calendar_event_id,
        status="Scheduled",
        notes=req.notes
    )
    db.add(review)

    # Update intern profile cache
    intern.review_date = req.review_date
    intern.google_meet_link = meet_link
    intern.status = WorkflowStatus.REVIEW_SCHEDULED.value

    db.add(AuditLog(
        action="REVIEW_SCHEDULED",
        actor_id=current_user.id,
        intern_id=intern.id,
        details=f"Scheduled review on {req.review_date.strftime('%Y-%m-%d')} {req.start_time}-{req.end_time} with mentor {mentor.full_name}. Meet: {meet_link}"
    ))
    db.commit()
    db.refresh(review)

    # 5. Send Review Invitation Email
    if req.send_invitation_email:
        queue_email(
            recipient=intern.user.email,
            template_key="REVIEW_SCHEDULED",
            context={
                "intern_name": intern.user.full_name,
                "task_title": intern.assigned_task.title if intern.assigned_task else "Internship Review",
                "mentor_name": mentor.full_name,
                "review_date": req.review_date.strftime("%Y-%m-%d"),
                "start_time": req.start_time,
                "end_time": req.end_time,
                "timezone": req.timezone,
                "meet_link": meet_link,
                "notes": req.notes or "Please be on time."
            },
            intern_id=intern.id,
            prevent_duplicate=False
        )

    return review

@router.post("/{review_id}/send-reminder")
def trigger_review_reminder(
    review_id: int,
    reminder_type: str = "24h",  # "24h" or "1h"
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    review = db.query(ReviewSchedule).filter(ReviewSchedule.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review schedule not found.")

    if reminder_type == "24h" and review.reminder_24h_sent:
        return {"message": "24-hour reminder was already sent. Duplicate prevented."}
    if reminder_type == "1h" and review.reminder_1h_sent:
        return {"message": "1-hour reminder was already sent. Duplicate prevented."}

    time_remaining_str = "24 hours" if reminder_type == "24h" else "1 hour"

    queue_email(
        recipient=review.intern.user.email,
        template_key="REVIEW_REMINDER",
        context={
            "intern_name": review.intern.user.full_name,
            "task_title": review.intern.assigned_task.title if review.intern.assigned_task else "Internship Task",
            "time_remaining": time_remaining_str,
            "review_date": review.review_date.strftime("%Y-%m-%d"),
            "start_time": review.start_time,
            "timezone": review.timezone,
            "meet_link": review.google_meet_link
        },
        intern_id=review.intern_id,
        prevent_duplicate=True
    )

    if reminder_type == "24h":
        review.reminder_24h_sent = True
    else:
        review.reminder_1h_sent = True
    db.commit()

    return {"message": f"{reminder_type} reminder sent successfully."}

@router.put("/{review_id}")
def update_review(
    review_id: int,
    req: ReviewUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MENTOR.value])),
    db: Session = Depends(get_db)
):
    review = db.query(ReviewSchedule).filter(ReviewSchedule.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(review, k, v)

    db.commit()
    return {"message": "Review schedule updated successfully."}
