import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import (
    User, UserRole, InternProfile, Submission, Evaluation, AuditLog, WorkflowStatus
)
from app.schemas.schemas import MentorFeedbackApproveRequest, CorrectionRequest
from app.core.security import get_current_user, require_roles
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/mentor", tags=["Mentor Workspace"])

@router.get("/workspace")
def get_mentor_workspace(
    current_user: User = Depends(require_roles([UserRole.MENTOR.value, UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    # If admin, can view all interns; if mentor, view assigned interns
    query = db.query(InternProfile)
    if current_user.role == UserRole.MENTOR.value:
        query = query.filter(InternProfile.mentor_id == current_user.id)
        
    interns = query.all()

    pending_submissions = []
    mentored_interns = []

    for ip in interns:
        mentored_interns.append({
            "id": ip.id,
            "intern_id": ip.intern_id,
            "full_name": ip.user.full_name,
            "email": ip.user.email,
            "department": ip.department,
            "status": ip.status,
            "task_title": ip.assigned_task.title if ip.assigned_task else "None",
            "task_deadline": ip.task_deadline.isoformat() if ip.task_deadline else None,
            "review_date": ip.review_date.isoformat() if ip.review_date else None,
            "google_meet_link": ip.google_meet_link
        })

        # Check latest submission
        if ip.submissions:
            latest = ip.submissions[0]
            ev = latest.evaluation
            if ev and (not ev.mentor_approved or ip.status in [WorkflowStatus.MENTOR_APPROVAL_PENDING.value, WorkflowStatus.RESUBMITTED.value]):
                pending_submissions.append({
                    "submission_id": latest.id,
                    "evaluation_id": ev.id,
                    "intern_profile_id": ip.id,
                    "intern_id": ip.intern_id,
                    "intern_name": ip.user.full_name,
                    "intern_email": ip.user.email,
                    "task_title": ip.assigned_task.title if ip.assigned_task else "",
                    "version": latest.version,
                    "file_name": latest.file_name,
                    "submitted_at": latest.submitted_at.isoformat(),
                    "completion_percentage": ev.completion_percentage,
                    "provisional_score": ev.overall_score,
                    "max_score": ev.max_score,
                    "is_provisional": ev.is_provisional,
                    "mentor_approved": ev.mentor_approved,
                    "mentor_notes": ev.mentor_notes,
                    "strengths": json.loads(ev.strengths) if ev.strengths else [],
                    "missing_items": json.loads(ev.missing_items) if ev.missing_items else [],
                    "suggested_corrections": json.loads(ev.suggested_corrections) if ev.suggested_corrections else [],
                    "requirement_evaluations": json.loads(ev.requirement_evaluations) if ev.requirement_evaluations else []
                })

    return {
        "pending_submissions": pending_submissions,
        "mentored_interns": mentored_interns
    }

@router.post("/evaluations/{evaluation_id}/approve")
def approve_evaluation(
    evaluation_id: int,
    req: MentorFeedbackApproveRequest,
    current_user: User = Depends(require_roles([UserRole.MENTOR.value, UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation record not found.")

    intern = ev.intern
    if current_user.role == UserRole.MENTOR.value and intern.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only approve evaluations for your assigned interns.")

    if req.overall_score is not None:
        ev.overall_score = req.overall_score
        ev.completion_percentage = round((ev.overall_score / max(ev.max_score, 1.0)) * 100, 1)

    ev.mentor_notes = req.mentor_notes
    ev.mentor_approved = req.approve_evaluation
    ev.is_provisional = not req.approve_evaluation
    ev.reviewed_by = current_user.id
    ev.reviewed_at = datetime.utcnow()

    # Update workflow status
    if req.update_status_to_approved:
        intern.status = WorkflowStatus.APPROVED.value
        email_template = "TASK_APPROVED"
    else:
        intern.status = WorkflowStatus.FEEDBACK_PUBLISHED.value
        email_template = "FEEDBACK_PUBLISHED"

    db.add(AuditLog(
        action="EVALUATION_APPROVED",
        actor_id=current_user.id,
        intern_id=intern.id,
        details=f"Mentor approved evaluation #{ev.id} with score {ev.overall_score}/{ev.max_score}. Status updated to {intern.status}."
    ))
    db.commit()

    # Dispatch feedback publication email
    queue_email(
        recipient=intern.user.email,
        template_key=email_template,
        context={
            "intern_name": intern.user.full_name,
            "task_title": intern.assigned_task.title if intern.assigned_task else "Internship Task",
            "score": ev.overall_score,
            "max_score": ev.max_score,
            "mentor_notes": ev.mentor_notes or "Well done!"
        },
        intern_id=intern.id,
        prevent_duplicate=False
    )

    return {
        "message": f"Evaluation successfully reviewed. Workflow status set to '{intern.status}'.",
        "evaluation_id": ev.id,
        "status": intern.status,
        "score": ev.overall_score
    }

@router.post("/interns/{intern_profile_id}/request-corrections")
def request_corrections(
    intern_profile_id: int,
    req: CorrectionRequest,
    current_user: User = Depends(require_roles([UserRole.MENTOR.value, UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    intern = db.query(InternProfile).filter(InternProfile.id == intern_profile_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found.")

    if current_user.role == UserRole.MENTOR.value and intern.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage your assigned interns.")

    intern.status = WorkflowStatus.CORRECTIONS_REQUIRED.value
    intern.correction_checklist = req.checklist
    intern.resubmission_deadline = req.resubmission_deadline

    next_review_info_html = ""
    if req.next_review_date:
        intern.review_date = req.next_review_date
        if req.google_meet_link:
            intern.google_meet_link = req.google_meet_link
        next_review_info_html = (
            f"<div style='background-color:#eff6ff; padding:12px; border-left:4px solid #3b82f6; margin:10px 0;'>"
            f"<p><strong>Follow-up Review Date:</strong> {req.next_review_date.strftime('%Y-%m-%d %H:%M')}</p>"
            f"<p><strong>Google Meet Link:</strong> <a href='{intern.google_meet_link}'>{intern.google_meet_link}</a></p>"
            f"</div>"
        )

    db.add(AuditLog(
        action="CORRECTIONS_REQUESTED",
        actor_id=current_user.id,
        intern_id=intern.id,
        details=f"Requested corrections. Resubmission deadline: {req.resubmission_deadline.strftime('%Y-%m-%d %H:%M')}"
    ))
    db.commit()

    # Dispatch email with correction instructions & next review link
    queue_email(
        recipient=intern.user.email,
        template_key="CORRECTIONS_REQUIRED",
        context={
            "intern_name": intern.user.full_name,
            "task_title": intern.assigned_task.title if intern.assigned_task else "Assigned Task",
            "checklist": req.checklist,
            "resubmission_deadline": req.resubmission_deadline.strftime("%Y-%m-%d %H:%M"),
            "next_review_info": next_review_info_html
        },
        intern_id=intern.id,
        prevent_duplicate=False
    )

    return {
        "message": "Corrections requested and intern notified successfully.",
        "status": intern.status,
        "resubmission_deadline": intern.resubmission_deadline.isoformat()
    }

@router.post("/interns/{intern_profile_id}/close-task")
def close_intern_task(
    intern_profile_id: int,
    current_user: User = Depends(require_roles([UserRole.MENTOR.value, UserRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    intern = db.query(InternProfile).filter(InternProfile.id == intern_profile_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern record not found.")

    intern.status = WorkflowStatus.CLOSED.value

    db.add(AuditLog(
        action="TASK_CLOSED",
        actor_id=current_user.id,
        intern_id=intern.id,
        details="Task cycle formally approved and closed."
    ))
    db.commit()

    return {"message": "Intern task cycle formally closed.", "status": intern.status}
