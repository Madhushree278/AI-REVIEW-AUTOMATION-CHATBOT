import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.entities import (
    User, UserRole, InternProfile, Task, Submission, Evaluation, AuditLog, WorkflowStatus
)
from app.schemas.schemas import SubmissionOut, EvaluationOut
from app.core.security import get_current_user, get_current_intern_profile
from app.core.document_parser import parse_and_verify_document
from app.core.ai_evaluator import evaluate_submission
from app.core.email_service import queue_email

router = APIRouter(prefix="/api/intern", tags=["Intern Portal"])

@router.get("/dashboard")
def get_intern_dashboard(
    profile: InternProfile = Depends(get_current_intern_profile),
    db: Session = Depends(get_db)
):
    task = profile.assigned_task
    task_rubric = []
    if task and task.rubric_criteria:
        try:
            task_rubric = json.loads(task.rubric_criteria)
        except Exception:
            pass

    # Submissions
    submissions_list = []
    for s in profile.submissions:
        ev = s.evaluation
        ev_data = None
        if ev:
            ev_data = {
                "id": ev.id,
                "overall_score": ev.overall_score,
                "max_score": ev.max_score,
                "completion_percentage": ev.completion_percentage,
                "ai_confidence": ev.ai_confidence,
                "is_provisional": ev.is_provisional,
                "mentor_approved": ev.mentor_approved,
                "mentor_notes": ev.mentor_notes,
                "strengths": json.loads(ev.strengths) if ev.strengths else [],
                "missing_items": json.loads(ev.missing_items) if ev.missing_items else [],
                "technical_errors": json.loads(ev.technical_errors) if ev.technical_errors else [],
                "suggested_corrections": json.loads(ev.suggested_corrections) if ev.suggested_corrections else [],
                "recommended_next_steps": json.loads(ev.recommended_next_steps) if ev.recommended_next_steps else [],
                "requirement_evaluations": json.loads(ev.requirement_evaluations) if ev.requirement_evaluations else []
            }
        submissions_list.append({
            "id": s.id,
            "version": s.version,
            "file_name": s.file_name,
            "file_type": s.file_type,
            "file_size": s.file_size,
            "description": s.description,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat(),
            "evaluation": ev_data
        })

    # Review Schedule
    reviews_list = []
    for r in profile.reviews:
        reviews_list.append({
            "id": r.id,
            "review_date": r.review_date.strftime("%Y-%m-%d"),
            "start_time": r.start_time,
            "end_time": r.end_time,
            "timezone": r.timezone,
            "google_meet_link": r.google_meet_link,
            "status": r.status,
            "notes": r.notes
        })

    return {
        "intern_info": {
            "name": profile.user.full_name,
            "email": profile.user.email,
            "intern_id": profile.intern_id,
            "department": profile.department,
            "status": profile.status,
            "mentor_name": profile.mentor.full_name if profile.mentor else "Not yet assigned",
            "mentor_email": profile.mentor.email if profile.mentor else None,
            "correction_checklist": profile.correction_checklist,
            "resubmission_deadline": profile.resubmission_deadline.isoformat() if profile.resubmission_deadline else None
        },
        "assigned_task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deliverables": task.deliverables,
            "submission_format": task.submission_format,
            "reference_links": task.reference_links,
            "deadline": profile.task_deadline.isoformat() if profile.task_deadline else (task.deadline.isoformat() if task.deadline else None),
            "max_marks": task.max_marks,
            "rubric": task_rubric
        } if task else None,
        "submissions": submissions_list,
        "reviews": reviews_list,
        "active_meet_link": profile.google_meet_link
    }

@router.post("/submit")
async def submit_task_deliverable(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    profile: InternProfile = Depends(get_current_intern_profile),
    db: Session = Depends(get_db)
):
    """
    Submits a task deliverable document (PDF, DOCX, ZIP, or code file).
    Automatically extracts text, evaluates against task rubric with AI,
    and saves provisional evaluation awaiting mentor review.
    """
    if not profile.assigned_task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have an assigned task to submit for."
        )

    task = profile.assigned_task
    rubric_list = []
    if task.rubric_criteria:
        try:
            rubric_list = json.loads(task.rubric_criteria)
        except Exception:
            pass

    # Determine submission version
    latest_sub = db.query(Submission).filter(
        Submission.intern_id == profile.id,
        Submission.task_id == task.id
    ).order_by(Submission.version.desc()).first()

    next_version = (latest_sub.version + 1) if latest_sub else 1

    # Check file size & extension
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    ext = Path(file.filename).suffix.lower().replace(".", "")
    allowed = set(settings.ALLOWED_EXTENSIONS.split(","))
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not permitted. Permitted extensions: {settings.ALLOWED_EXTENSIONS}"
        )

    # Save to uploads directory with unique safe filename
    safe_filename = f"{profile.intern_id}_v{next_version}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(save_path, "wb") as f:
        f.write(contents)

    # Step 1: Extract text and verify document
    doc_result = parse_and_verify_document(save_path, file.filename)
    if not doc_result["success"]:
        # Handle unreadable/empty files gracefully without crashing
        queue_email(
            recipient=profile.user.email,
            template_key="SUBMISSION_ERROR",
            context={
                "intern_name": profile.user.full_name,
                "task_title": task.title,
                "error_message": doc_result["error_message"]
            },
            intern_id=profile.id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document verification failed: {doc_result['error_message']}"
        )

    # Step 2: Save Submission record
    submission = Submission(
        intern_id=profile.id,
        task_id=task.id,
        version=next_version,
        file_path=save_path,
        file_name=file.filename,
        file_type=doc_result["file_type"],
        file_size=file_size,
        description=description,
        extracted_text=doc_result["extracted_text"][:50000],  # store up to 50k chars
        status="Submitted",
        submitted_at=datetime.utcnow()
    )
    db.add(submission)
    db.flush()

    # Step 3: Run AI Evaluation Engine against Task Rubric
    ai_report = evaluate_submission(
        intern_id_str=profile.intern_id,
        task_title=task.title,
        task_description=task.description,
        expected_deliverables=task.deliverables,
        rubric_criteria=rubric_list,
        extracted_text=doc_result["extracted_text"],
        file_name=file.filename,
        version=next_version,
        correction_checklist=profile.correction_checklist if next_version > 1 else None
    )

    evaluation = Evaluation(
        submission_id=submission.id,
        task_id=task.id,
        intern_id=profile.id,
        overall_score=ai_report.get("overall_score", 0.0),
        max_score=ai_report.get("max_score", float(task.max_marks)),
        completion_percentage=ai_report.get("completion_percentage", 0.0),
        requirement_evaluations=json.dumps(ai_report.get("requirement_evaluations", [])),
        completed_items=json.dumps(ai_report.get("completed_items", [])),
        missing_items=json.dumps(ai_report.get("missing_items", [])),
        technical_errors=json.dumps(ai_report.get("technical_errors", [])),
        strengths=json.dumps(ai_report.get("strengths", [])),
        areas_for_improvement=json.dumps(ai_report.get("areas_for_improvement", [])),
        suggested_corrections=json.dumps(ai_report.get("suggested_corrections", [])),
        recommended_next_steps=json.dumps(ai_report.get("recommended_next_steps", [])),
        ai_confidence=ai_report.get("ai_confidence", "High (92%)"),
        is_provisional=True,  # Always provisional until mentor approval
        mentor_approved=False
    )
    db.add(evaluation)

    # Step 4: Update intern status
    if next_version > 1:
        profile.status = WorkflowStatus.RESUBMITTED.value
    else:
        profile.status = WorkflowStatus.MENTOR_APPROVAL_PENDING.value

    db.add(AuditLog(
        action="TASK_SUBMITTED",
        actor_id=profile.user_id,
        intern_id=profile.id,
        details=f"Submitted {file.filename} (Version {next_version}). AI evaluation generated ({ai_report.get('completion_percentage')}% complete)."
    ))
    db.commit()

    # Step 5: Send confirmation email to intern
    queue_email(
        recipient=profile.user.email,
        template_key="SUBMISSION_CONFIRMATION" if next_version == 1 else "RESUBMISSION_CONFIRMATION",
        context={
            "intern_name": profile.user.full_name,
            "task_title": task.title,
            "version": next_version,
            "file_name": file.filename,
            "file_size_kb": round(file_size / 1024, 1)
        },
        intern_id=profile.id
    )

    # Notify mentor
    if profile.mentor:
        queue_email(
            recipient=profile.mentor.email,
            template_key="AI_EVAL_READY",
            context={
                "mentor_name": profile.mentor.full_name,
                "intern_name": profile.user.full_name,
                "intern_id": profile.intern_id,
                "task_title": task.title,
                "completion_percentage": ai_report.get("completion_percentage"),
                "score": ai_report.get("overall_score"),
                "max_score": task.max_marks
            },
            intern_id=profile.id
        )

    return {
        "message": f"Submission (Version {next_version}) uploaded and verified successfully.",
        "submission_id": submission.id,
        "version": next_version,
        "ai_provisional_report": ai_report
    }
